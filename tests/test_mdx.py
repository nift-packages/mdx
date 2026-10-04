#!/usr/bin/env python3
"""Contract, adversarial, filesystem, and build certification for mdx 0.1."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time


NIFT = Path(sys.argv[1] if len(sys.argv) > 1 else "nift").resolve()
PACKAGE = Path(__file__).resolve().parent.parent
TESTS = PACKAGE / "tests"
SOURCE = PACKAGE / "src" / "mdx.f"


def require(condition, message, result=None):
    if condition:
        return
    detail = ""
    if result is not None:
        detail = f"\nrc={result.returncode}\nstdout={result.stdout!r}\nstderr={result.stderr!r}"
    raise AssertionError(message + detail)


def run(command, cwd, timeout=90):
    env = os.environ.copy()
    env["HOME"] = str(cwd / "home")
    env["XDG_CACHE_HOME"] = str(cwd / "cache")
    (cwd / "home").mkdir(exist_ok=True)
    (cwd / "cache").mkdir(exist_ok=True)
    return subprocess.run([str(NIFT), *command], cwd=cwd, env=env,
                          stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, timeout=timeout, check=False)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def install(cwd, package=PACKAGE, revision=None):
    (cwd / ".nift").mkdir(parents=True, exist_ok=True)
    if os.name == "nt" and isinstance(package, Path):
        package = package.as_uri()
        if revision is None:
            revision = "HEAD"
    arguments = ["add", str(package)]
    if revision is not None:
        arguments.append(f"--ref={revision}")
    result = run(arguments, cwd)
    require(result.returncode == 0, "fresh nift add failed", result)


def nift_literal(value):
    return json.dumps(value, ensure_ascii=False)


def run_external(command, cwd, timeout=60):
    return subprocess.run(command, cwd=cwd, stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, timeout=timeout,
                          check=False)


def parse_output(result, label):
    require(result.returncode == 0, label, result)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError(f"{label}: non-JSON output {result.stdout!r}") from error


manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="ascii"))
require(manifest == {
    "name": "mdx",
    "version": "0.1.0",
    "entry": "src/mdx.f",
    "description": "Bounded preservation parser and dependency discovery for MDX-like documents",
}, "manifest contract differs")
require("dependencies" not in manifest and "resources" not in manifest,
        "manifest must have no dependencies/resources")

package_source = SOURCE.read_text(encoding="ascii")
public = re.findall(r"^    fn\(([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)\)\)", package_source, re.MULTILINE)
private = re.findall(r"^    private fn\(([A-Za-z_][A-Za-z0-9_]*)\(", package_source, re.MULTILINE)
exports = re.findall(r"^export\(([^)]+)\)$", package_source, re.MULTILINE)
require(public == [("with_profile", "name"), ("prepare", "documents"), ("html", "document"), ("parse", "source"), ("input", "path")], f"exact public API differs: {public!r}")
require(exports == ["mdx"], f"sole export differs: {exports!r}")
require(private and len(private) == len(set(private)), "private helper list invalid")
for forbidden in ("process(", "shell(", "eval(", "exec(", "ffi_", "@input("):
    require(forbidden not in package_source, f"forbidden capability in package source: {forbidden}")
require(package_source.count("@dep('$[path]')") == 1, "dependency registration must be isolated")
require(package_source.count("open(path)") == 1 and "exists(path)" in package_source,
        "filesystem surface differs")
require(not re.search(r"^mdx_graph_", package_source, re.MULTILINE),
        "graph state must not be module-global")

expected_files = {"LICENSE", "README.md", "manifest.json", "src/mdx.f",
                  "tests/.gitignore", "tests/contract.f", "tests/test_mdx.py"}

work_context = tempfile.TemporaryDirectory(prefix=".mdx-test-", dir=TESTS)
work = Path(work_context.name)
timings = {}
try:
    suite_start = time.perf_counter()

    direct = work / "direct"
    direct.mkdir()
    contract = (TESTS / "contract.f").read_text(encoding="ascii")
    direct_contract = contract.replace('@import("mdx")', '@import("../../../src/mdx.f")', 1)
    write(direct / "contract.f", direct_contract)
    result = run(["contract.f", "--no-process"], direct)
    require(result.returncode == 0 and result.stdout.strip() == "PASS mdx contract",
            "direct source contract failed", result)

    consumer = work / "consumer"
    consumer.mkdir()
    install(consumer)
    installed_entry = consumer / ".nift" / "packages" / "mdx" / "src" / "mdx.f"
    require(installed_entry.is_file() and not installed_entry.is_symlink(),
            "installed entry must be a staged regular file")
    require(installed_entry.read_bytes() == SOURCE.read_bytes(), "installed entry differs from source")
    write(consumer / "contract.f", contract)
    installed_start = time.perf_counter()
    installed = run(["contract.f", "--no-process"], consumer)
    timings["contract"] = time.perf_counter() - installed_start
    require(installed.returncode == 0 and installed.stdout.strip() == "PASS mdx contract",
            "installed contract failed", installed)
    repeated = run(["contract.f", "--no-process"], consumer)
    require((installed.returncode, installed.stdout, installed.stderr) ==
            (repeated.returncode, repeated.stdout, repeated.stderr), "contract is nondeterministic")

    for helper in private:
        write(consumer / "private.f", f'@import("mdx")\nmdx.{helper}()\n')
        hidden = run(["private.f", "--no-process"], consumer)
        require(hidden.returncode != 0 and f"private struct method: {helper}" in hidden.stderr,
                f"private helper exposed: {helper}", hidden)
    for expression in ("mdx.parse()", 'mdx.parse("a", "b")', "mdx.input()", 'mdx.input("a", "b")'):
        write(consumer / "arity.f", f'@import("mdx")\n{expression}\n')
        require(run(["arity.f", "--no-process"], consumer).returncode != 0,
                f"wrong arity accepted: {expression}")
    for hidden_name in ("parse_core", "graph_state", "walk"):
        write(consumer / "global.f", f'@import("mdx")\nprint({hidden_name})\n')
        require(run(["global.f", "--no-process"], consumer).returncode != 0,
                f"private global binding leaked: {hidden_name}")

    origin = work / "origin"
    origin.mkdir()
    for relative in expected_files:
        destination = origin / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PACKAGE / relative, destination)
    initialized = run_external(["git", "init", "-q"], origin)
    require(initialized.returncode == 0, "temporary Git origin init failed", initialized)
    require(run_external(["git", "add", "."], origin).returncode == 0,
            "temporary Git origin add failed")
    committed = run_external(["git", "-c", "user.name=mdx-test", "-c",
                              "user.email=mdx@example.invalid", "commit", "-qm",
                              "package fixture"], origin)
    require(committed.returncode == 0, "temporary Git origin commit failed", committed)
    revision = run_external(["git", "rev-parse", "HEAD"], origin).stdout.strip()
    independent = work / "independent"
    independent.mkdir()
    install(independent, origin.as_uri(), revision)
    independent_entry = independent / ".nift" / "packages" / "mdx" / "src" / "mdx.f"
    require(independent_entry.is_file() and not independent_entry.is_symlink(),
            "Git-installed entry must be a staged regular file")
    write(independent / "contract.f", contract)

    website = work / "website"
    website.mkdir()
    install(website, origin.as_uri(), revision)
    shutil.rmtree(origin)
    independent_result = run(["contract.f", "--no-process"], independent)
    require(independent_result.returncode == 0 and
            independent_result.stdout.strip() == "PASS mdx contract",
            "source-independent installed contract failed", independent_result)

    corpus = [
        "", "plain", "a\nb\r\nc\rd", "\\<X /> \\{x}",
        "~~~js\nimport './no.mdx'\n~~~\n", "````\n```\n````",
        "`a { <X> b`", "``a ` b``", "{ /* only */ }", "{// x\n}",
        "{({a: `x ${value ? /[}]/g : /x\\//}`})}",
        "<A><><B x y='>' z={/}/.test(x)} {...props} /></></A>",
        "<ns:item data-id=\"{>}\">left{/* note */}right</ns:item>",
        "import {\n x,\n y\n} from './many.mdx'\nexport function f() { return `{x}` }\n",
        "caf\u00e9 \U0001f600 <X>\u03bb</X>", "\u00e9lead", "\u20aclead", "\U0001f600lead",
        "\u00e9\u20ac\U0001f600" * 40 + "{x}",
        "{typeof /}/.source}", "{a++ / b + ({c:1}).c}",
        "paragraph\nimport './not-esm.mdx'\n", "paragraph\rimport './not-esm.mdx'\r",
        "paragraph\r\nimport './not-esm.mdx'\r\n", "> quote\nimport './lazy.mdx'\n",
        "<A>\n```mdx\n<B>{inert}</B>\n```\n</A>",
        "import /* before */ x from /* after */ './commented.mdx'\n",
        "import /* before */ './side.mdx'\n",
        "import // before\n './line-side.mdx'\n",
        "import x from // before\n './line-from.mdx'\n",
        "export // before\n const x = 1\n",
        "export default // before\n 1\n",
        "export const x = 1 // done\nparagraph\n",
        "export default 1 // done\nimport './after-number.mdx'\n",
        "export default 'x' // done\nimport './after-string.mdx'\n",
        "export default `x` // done\nimport './after-template.mdx'\n",
        "export default [1] // done\nimport './after-array.mdx'\n",
        "{(() => { if (x) /}/.test(y) })()}",
        "{(() => { for (;x;) /[a}]+/g.test(y) })()}",
        "{(() => { switch (x) { case 1: break } /q}/.test(y) })()}",
        "{(() => { try {} catch (e) {} /r}/.test(y) })()}",
    ]
    generated = []
    for index in range(80):
        generated.append(("m" * (index % 7)) + "{a" + (" + {b: 1}" * (index % 5)) + "}" +
                         ("<X a=\"}>\">y</X>" if index % 3 == 0 else "`<Z />`") + "\n")
    corpus.extend(generated)
    corpus_lines = [
        '@import("mdx")',
        'fn(expect(condition, label)) { if(!condition) { print(label); missing.value } }',
    ]
    for index, sample in enumerate(corpus):
        literal = nift_literal(sample)
        corpus_lines.extend([
            f"r{index} := mdx.parse({literal})",
            f'expect(r{index}.ok, "corpus ok {index}")',
            f'expect(r{index}.source == {literal}, "corpus source {index}")',
            f'joined{index} := ""',
            f'for(n{index} : r{index}.nodes) {{ joined{index} += n{index}.source; expect(n{index}.source == r{index}.source.encode("utf-8").slice(n{index}.position.start.offset, n{index}.position.end.offset).decode("utf-8"), "slice {index}") }}',
            f'expect(joined{index} == r{index}.source.substr(r{index}.frontmatter.present ? r{index}.frontmatter.end.offset : 0), "reconstruct {index}")',
        ])
    corpus_lines.append('print("PASS mdx corpus")')
    write(consumer / "corpus.f", "\n".join(corpus_lines) + "\n")
    corpus_start = time.perf_counter()
    result = run(["corpus.f", "--no-process"], consumer, timeout=120)
    timings["corpus"] = time.perf_counter() - corpus_start
    require(result.returncode == 0 and result.stdout.strip() == "PASS mdx corpus",
            "generated parser corpus failed", result)

    malformed = {
        "unclosed_frontmatter": "---\na: b\n",
        "unclosed_expression": "before {x",
        "mismatched_jsx": "<A><B /></a>",
        "unclosed_jsx": "<A>text",
        "html_comment_unsupported": "<!-- no -->",
        "invalid_jsx_attribute": "<A x=no />",
        "malformed_import": "import thing\n",
        "unsupported_specifier_escape": "import './bad\\n.mdx'\n",
        "invalid_jsx_name": "<A:B:C />",
        "invalid_jsx_name_mixed": "<A.B:C />",
        "invalid_jsx_attribute_dot": "<A a.b />",
        "invalid_jsx_attribute_repeat": "<A a:b:c />",
        "jsx_backslash_quote": '<A q="a\\" b" />',
    }
    malformed_lines = ['@import("mdx")', 'fn(expect(c,l)) { if(!c) { print(l); missing.value } }']
    for index, (label, sample) in enumerate(malformed.items()):
        code = label
        if label == "invalid_jsx_name_mixed":
            code = "invalid_jsx_name"
        elif label in ("invalid_jsx_attribute_dot", "invalid_jsx_attribute_repeat", "jsx_backslash_quote"):
            code = "invalid_jsx_attribute"
        malformed_lines.append(f'r{index} := mdx.parse({nift_literal(sample)}); expect(!r{index}.ok && r{index}.nodes.length() == 0 && r{index}.imports.length() == 0 && r{index}.exports.length() == 0 && r{index}.diagnostics[0].code == "{code}", "{label}")')
    malformed_lines.append('expect(mdx.parse("```\nunclosed").ok, "unclosed fence is Markdown behavior")')
    malformed_lines.append('print("PASS mdx malformed")')
    write(consumer / "malformed.f", "\n".join(malformed_lines) + "\n")
    result = run(["malformed.f", "--no-process"], consumer)
    require(result.returncode == 0 and result.stdout.strip() == "PASS mdx malformed",
            "malformed contract failed", result)

    boundary_contract = r'''@import("mdx")
fn(expect(c,l)) { if(!c) { print(l); missing.value } }
fn(repeat(piece, count)) { result := ""; i := 0; while(i < count) { result += piece; i += 1 }; return result }
byte_at := repeat("a", 4096)
byte_at_result := mdx.parse(byte_at)
expect(byte_at.encode("utf-8").length() == 4096 && byte_at_result.ok, "byte exact")
byte_over := byte_at + "a"
expect(mdx.parse(byte_over).diagnostics[0].code == "source_too_large", "byte +1")
line_at := repeat("x\n", 1023) + "x"
expect(mdx.parse(line_at).ok, "line exact")
expect(mdx.parse(line_at + "\nx").diagnostics[0].code == "too_many_lines", "line +1")
objects_at := repeat("{x}", 1024)
objects_result := mdx.parse(objects_at)
expect(objects_result.ok && objects_result.nodes.length() == 1024, "syntax exact")
expect(mdx.parse(objects_at + "{x}").diagnostics[0].code == "too_many_syntax_objects", "syntax +1")
imports_at := repeat("import 'pkg'\n", 256)
imports_result := mdx.parse(imports_at)
expect(imports_result.ok && imports_result.imports.length() == 256, "imports exact")
expect(mdx.parse(imports_at + "import 'pkg'\n").diagnostics[0].code == "too_many_imports", "imports +1")
expression_at := "{" + repeat("{", 63) + "x" + repeat("}", 63) + "}"
expect(mdx.parse(expression_at).ok, "expression nesting exact")
expect(mdx.parse("{" + repeat("{", 64) + "x" + repeat("}", 64) + "}").diagnostics[0].code == "nesting_limit", "expression nesting +1")
jsx_at := repeat("<A>", 48) + "x" + repeat("</A>", 48)
expect(mdx.parse(jsx_at).ok, "JSX nesting exact")
expect(mdx.parse(repeat("<A>", 49) + "x" + repeat("</A>", 49)).diagnostics[0].code == "nesting_limit", "JSX nesting +1")
run_at := repeat("`", 256)
expect(mdx.parse(run_at).ok, "delimiter run exact")
expect(mdx.parse(run_at + "`").diagnostics[0].code == "delimiter_run_too_long", "delimiter run +1")
specifier_at := repeat("a", 4000)
expect(mdx.parse("import '" + specifier_at + "'\n").ok, "specifier exact")
expect(mdx.parse("import '" + specifier_at + "a'\n").diagnostics[0].code == "specifier_too_long", "specifier +1")
wide_at := "<A" + repeat(" a", 1023) + " />"
expect(mdx.parse(wide_at).ok, "wide attributes exact")
expect(mdx.parse("<A" + repeat(" a", 1024) + " />").diagnostics[0].code == "too_many_syntax_objects", "wide attributes +1")
children_at := "<A>" + repeat("{x}", 1023) + "</A>"
expect(mdx.parse(children_at).ok, "wide children exact")
expect(mdx.parse("<A>" + repeat("{x}", 1024) + "</A>").diagnostics[0].code == "too_many_syntax_objects", "wide children +1")
mixed_at := "prefix" + "<A" + repeat(" a", 1022) + " />"
expect(mdx.parse(mixed_at).ok, "aggregate syntax exact")
expect(mdx.parse("prefix" + "<A" + repeat(" a", 1023) + " />").diagnostics[0].code == "too_many_syntax_objects", "aggregate syntax +1")
print("PASS mdx boundaries")
'''
    boundary_checks = 22
    write(consumer / "boundaries.f", boundary_contract)
    boundary_start = time.perf_counter()
    result = run(["boundaries.f", "--no-process"], consumer, timeout=180)
    timings["boundaries"] = time.perf_counter() - boundary_start
    require(result.returncode == 0 and result.stdout.strip() == "PASS mdx boundaries",
            "exact boundary suite failed", result)

    fixtures = consumer / "fixtures"
    write(fixtures / "root.mdx", "import './a.mdx'\nimport './dir/../a.mdx'\nimport './note.md'\nimport './code.js'\nimport 'bare'\nroot\n")
    write(fixtures / "a.mdx", "import './nested/b.mdx'\nimport './note.md'\nA\n")
    write(fixtures / "nested" / "b.mdx", "B\n")
    write(fixtures / "note.md", "import './never.mdx'\n")
    write(fixtures / "code.js", "export default 1\n")
    write(fixtures / "cycle-a.mdx", "import './cycle-b.mdx'\n")
    write(fixtures / "cycle-b.mdx", "import './cycle-a.mdx'\n")
    write(fixtures / "inert.mdx", "```\nimport './no.mdx'\n```\n`import './no2.mdx'`\n")
    write(fixtures / "space \u03bb.mdx", "Unicode path\n")
    write(fixtures / "path-root.mdx", "import './space \u03bb.mdx'\n")
    (fixtures / "directory.mdx").mkdir()
    write(fixtures / "missing-import.mdx", "import './absent.mdx'\nimport './x/../absent.mdx'\nimport './directory.mdx'\nimport './directory.mdx'\n")
    unicode_directory = "\u591a\u5b57\u8282\u30c7\u30a3\u30ec\u30af\u30c8\u30ea\U0001f600"
    unicode_child = "\u5b50\u30c7\u30a3\u30ec\u30af\u30c8\u30ea\u03bb"
    write(fixtures / unicode_directory / unicode_child / "root.mdx", "import '../\u5bfe\u8c61.mdx'\n")
    write(fixtures / unicode_directory / "\u5bfe\u8c61.mdx", "unicode target\n")

    input_script = '''@import("mdx")
print(mdx.input("fixtures/root.mdx").stringify())
print(mdx.input("fixtures/cycle-a.mdx").stringify())
print(mdx.input("fixtures/inert.mdx").stringify())
print(mdx.input("fixtures/path-root.mdx").stringify())
print(mdx.input("fixtures/missing-import.mdx").stringify())
print(mdx.input("fixtures/''' + unicode_directory + "/" + unicode_child + '''/root.mdx").stringify())
print(mdx.input("fixtures/missing.mdx").stringify())
print(mdx.input("fixtures/directory.mdx").stringify())
'''
    write(consumer / "input.f", input_script)
    graph_start = time.perf_counter()
    graph_result = run(["input.f", "--no-process"], consumer, timeout=90)
    timings["graph"] = time.perf_counter() - graph_start
    require(graph_result.returncode == 0, "filesystem graph script failed", graph_result)
    graph_values = [json.loads(line) for line in graph_result.stdout.splitlines()]
    root, cycle, inert, unicode_path, missing_import, unicode_importer, missing, directory = graph_values
    require(root["ok"] and [item["path"] for item in root["dependencies"]] ==
            ["fixtures/a.mdx", "fixtures/nested/b.mdx", "fixtures/note.md"],
            f"DFS dependency order/dedup differs: {root['dependencies']!r}")
    require([item["depth"] for item in root["dependencies"]] == [1, 2, 2],
            "dependency depths differ")
    require(cycle["ok"] is False and any(d["code"] == "dependency_cycle" for d in cycle["diagnostics"]),
            "cycle was not structured")
    require(all(item["path"] != "fixtures/cycle-a.mdx" for item in cycle["dependencies"]),
            "cycle root leaked into dependencies")
    require(inert["ok"] and inert["dependencies"] == [], "code spans produced dependencies")
    require(unicode_path["ok"] and unicode_path["dependencies"][0]["path"] == "fixtures/space \u03bb.mdx",
            "space/Unicode path resolution failed")
    require([d["code"] for d in missing_import["diagnostics"]].count("missing_dependency") == 1 and
            [d["code"] for d in missing_import["diagnostics"]].count("dependency_is_directory") == 1,
            "duplicate missing/directory diagnostics were not deduplicated")
    expected_unicode_dependency = f"fixtures/{unicode_directory}/\u5bfe\u8c61.mdx"
    require(unicode_importer["ok"] and unicode_importer["dependencies"][0]["path"] == expected_unicode_dependency,
            f"Unicode importer resolution failed: {unicode_importer!r}")
    require(missing["diagnostics"][0]["code"] == "missing_file" and
            directory["diagnostics"][0]["code"] == "input_is_directory",
            "missing/directory input diagnostics differ")

    consistency_source = "---\nx: raw\n---\n<A>{x}</A>\n"
    write(fixtures / "consistent.mdx", consistency_source)
    write(consumer / "consistent.f", '''@import("mdx")
p := mdx.parse(open("fixtures/consistent.mdx"))
i := mdx.input("fixtures/consistent.mdx")
print(p.omit(["path","dependencies"]).stringify())
print(i.omit(["path","dependencies"]).stringify())
''')
    consistent = run(["consistent.f", "--no-process"], consumer)
    require(consistent.returncode == 0 and len(consistent.stdout.splitlines()) == 2 and
            consistent.stdout.splitlines()[0] == consistent.stdout.splitlines()[1],
            "parse/input consistency failed", consistent)

    # Recursive file, depth, and aggregate limits.
    write(fixtures / "many-63-root.mdx", "".join(f'import "./many/{i}.mdx"\n' for i in range(63)))
    write(fixtures / "many-64-root.mdx", "".join(f'import "./many/{i}.mdx"\n' for i in range(64)))
    for index in range(64):
        write(fixtures / "many" / f"{index}.mdx", "x\n")
    write(fixtures / "deep-0.mdx", 'import "./deep-1.mdx"\n')
    for index in range(1, 18):
        write(fixtures / f"deep-{index}.mdx", (f'import "./deep-{index + 1}.mdx"\n' if index < 17 else "end\n"))
    write(fixtures / "aggregate-root.mdx", "".join(f'import "./aggregate/{i}.mdx"\n' for i in range(17)))
    for index in range(17):
        write(fixtures / "aggregate" / f"{index}.mdx", "x" * 1000)
    write(consumer / "graph-limits.f", '''@import("mdx")
print(mdx.input("fixtures/many-63-root.mdx").stringify())
print(mdx.input("fixtures/many-64-root.mdx").stringify())
print(mdx.input("fixtures/deep-0.mdx").stringify())
print(mdx.input("fixtures/aggregate-root.mdx").stringify())
''')
    graph_limit_start = time.perf_counter()
    limit_graph = run(["graph-limits.f", "--no-process"], consumer, timeout=60)
    timings["graph_limits"] = time.perf_counter() - graph_limit_start
    require(limit_graph.returncode == 0, "graph limit script failed", limit_graph)
    many_at, many_over, deep, aggregate = [json.loads(line) for line in limit_graph.stdout.splitlines()]
    require(many_at["ok"] and len(many_at["dependencies"]) == 63, "64 recursive files exact failed")
    require(any(d["code"] == "dependency_file_limit" for d in many_over["diagnostics"]), "recursive file +1 limit missing")
    require(any(d["code"] == "dependency_depth_limit" for d in deep["diagnostics"]), "depth limit missing")
    require(any(d["code"] == "aggregate_source_limit" for d in aggregate["diagnostics"]), "aggregate limit missing")

    scaling_common = r'''@import("mdx")
fn(expect(c,l)) { if(!c) { print(l); missing.value } }
fn(repeat(piece, count)) { result := ""; i := 0; while(i < count) { result += piece; i += 1 }; return result }
fn(plain(size)) { line := repeat("p", 1023); result := ""; left := size; while(left >= 1024) { result += line + "\n"; left -= 1024 }; result += repeat("p", left); return result }
'''
    scaling_scripts = {
        "plain_scaling": scaling_common + '''for(size : [512,1024,2048,4096]) { expect(mdx.parse(plain(size)).ok, "plain") }
expect(mdx.parse(plain(4097)).diagnostics[0].code == "source_too_large", "plain over")
print("PASS")
''',
        "backtick_scaling": scaling_common + '''for(size : [512,1024,2048]) { r := mdx.parse(repeat("`", size)); expect(!r.ok && r.diagnostics[0].code == "delimiter_run_too_long", "backticks") }
staircase := ''' + nift_literal("x".join("`" * size for size in range(1, 90))) + '''
staircase_result := mdx.parse(staircase)
expect(staircase.encode("utf-8").length() == 4093 && staircase_result.ok && staircase_result.nodes.length() == 1, "distinct unmatched backticks")
print("PASS")
''',
        "malformed_scaling": scaling_common + '''for(size : [512,1024,2048,4000]) { r := mdx.parse("{/*" + plain(size)); expect(!r.ok && r.diagnostics[0].code == "unclosed_expression", "malformed") }
large_fence := mdx.parse("```\n" + plain(4000)); expect(large_fence.ok, "fence")
print("PASS")
''',
        "object_scaling": scaling_common + '''objects := repeat("{x}", 1024); expect(mdx.parse(objects).ok, "objects")
expect(mdx.parse(objects + "{x}").diagnostics[0].code == "too_many_syntax_objects", "objects over")
expect(mdx.parse("<A" + repeat(" a", 1024) + " />").diagnostics[0].code == "too_many_syntax_objects", "wide")
print("PASS")
''',
    }
    for scaling_name, scaling_source in scaling_scripts.items():
        write(consumer / f"{scaling_name}.f", scaling_source)
        started = time.perf_counter()
        scaled = run([f"{scaling_name}.f", "--no-process"], consumer, timeout=45)
        timings[scaling_name] = time.perf_counter() - started
        require(scaled.returncode == 0 and scaled.stdout.strip() == "PASS",
                f"{scaling_name} failed", scaled)
        require(timings[scaling_name] < 30, f"{scaling_name} exceeded 30 seconds")

    for count in (16, 32, 63):
        write(fixtures / f"scale-{count}.mdx", "".join(f'import "./many/{index}.mdx"\n' for index in range(count)))
    write(consumer / "graph-scaling.f", '''@import("mdx")
fn(expect(c,l)) { if(!c) { print(l); missing.value } }
expect(mdx.input("fixtures/scale-16.mdx").ok, "16")
expect(mdx.input("fixtures/scale-32.mdx").ok, "32")
expect(mdx.input("fixtures/scale-63.mdx").ok, "63")
print("PASS")
''')
    graph_scaling_start = time.perf_counter()
    graph_scaling = run(["graph-scaling.f", "--no-process"], consumer, timeout=30)
    timings["graph_scaling"] = time.perf_counter() - graph_scaling_start
    require(graph_scaling.returncode == 0 and graph_scaling.stdout.strip() == "PASS",
            "graph scaling failed", graph_scaling)
    require(timings["graph_scaling"] < 15, "graph scaling exceeded 15 seconds")

    # Real tracked build from the pinned, now-removed origin.
    write(website / ".nift" / "config.json", json.dumps({"config": {
        "content-dir": "content/", "content-ext": ".html", "output-dir": "public/",
        "output-ext": ".html", "default-template": "templates/template.html",
        "build-threads": 4, "incremental-mode": "hash"}}))
    write(website / ".nift" / "tracked.json", json.dumps({"tracked": [
        {"name": "/", "title": "Home", "template": "templates/template.html"},
        {"name": "other", "title": "Other", "template": "templates/other.html"}]}))
    staged_entry = website / ".nift" / "packages" / "mdx" / "src" / "mdx.f"
    require(staged_entry.is_file() and not staged_entry.is_symlink(), "website installed entry is not staged")
    write(website / "templates" / "template.html", '''@import("../.nift/packages/mdx/src/mdx.f")
$[mdx.input("content/page.mdx").source]
@content
''')
    write(website / "templates" / "other.html", "unrelated\n@content\n")
    write(website / "content" / "index.html", "home\n")
    write(website / "content" / "other.html", "other\n")
    write(website / "content" / "page.mdx", "import './intro.mdx'\npage\n")
    write(website / "content" / "intro.mdx", "import './nested.mdx'\nintro\n")
    write(website / "content" / "nested.mdx", "nested one\n")
    built = run(["build", "--all"], website, timeout=120)
    require(built.returncode == 0, "tracked website initial build failed", built)
    built_restricted = run(["build", "--all", "--no-process"], website, timeout=120)
    require(built_restricted.returncode == 0, "tracked website --no-process build failed", built_restricted)
    metadata = json.loads((website / ".nift" / "public" / "index.info.json").read_text())
    metadata_text = json.dumps(metadata, sort_keys=True)
    for dependency in ("content/page.mdx", "content/intro.mdx", "content/nested.mdx"):
        require(metadata_text.count(dependency) == 1, f"dependency metadata count differs for {dependency}: {metadata_text}")
    write(website / "content" / "nested.mdx", "nested two\n")
    status = run(["status"], website)
    require(status.returncode == 0 and "1 of 2 tracked files" in status.stdout and "content/nested.mdx" in status.stdout and "other" not in status.stdout,
            "nested edit did not isolate stale target", status)
    rebuilt = run(["build", "--no-process"], website, timeout=120)
    require(rebuilt.returncode == 0 and "1 file rebuilt successfully" in rebuilt.stdout and "other" not in rebuilt.stdout,
            "incremental rebuild did not isolate consuming target", rebuilt)
    metadata_after = (website / ".nift" / "public" / "index.info.json").read_text()
    for dependency in ("content/page.mdx", "content/intro.mdx", "content/nested.mdx"):
        require(metadata_after.count(dependency) == 1, f"rebuild duplicated metadata for {dependency}")

    # @dep confinement remains a Nift hard failure. A missing path is structured first.
    outside = work / "outside.mdx"
    write(outside, "outside\n")
    write(consumer / "escape.f", '@import("mdx")\nprint(mdx.input("../outside.mdx").stringify())\n')
    escaped = run(["escape.f", "--no-process"], consumer)
    require(escaped.returncode == 0 and json.loads(escaped.stdout)["diagnostics"][0]["code"] == "path_escape",
            "lexical root escape was not structured", escaped)
    symlink = consumer / "fixtures" / "link.mdx"
    try:
        symlink.symlink_to(outside)
        write(consumer / "symlink.f", '@import("mdx")\nprint(mdx.input("fixtures/link.mdx").stringify())\n')
        linked = run(["symlink.f", "--no-process"], consumer)
        require(linked.returncode != 0 and "stay inside" in linked.stderr,
                "@dep symlink confinement did not hard fail", linked)
    except (OSError, NotImplementedError):
        pass

    # This assertion protects the original parser surface, not Git metadata or
    # explicitly separate investigation/optional-renderer artifacts.
    all_paths = {str(path.relative_to(PACKAGE)) for path in PACKAGE.rglob("*")
                 if path.is_file() and work not in path.parents
                 and path.relative_to(PACKAGE).parts[0] not in {".git", "investigation", "renderer", "node_modules", ".github"}}
    all_paths -= {"tests/baseline.json", "tests/test_render.py", "tests/profile_parser.py", "tests/test_profiles.py", "tests/test_parser_parity.py"}
    require(all_paths == expected_files, f"package residue/unexpected files: {sorted(all_paths ^ expected_files)!r}")
    require(all(all(byte < 128 for byte in (PACKAGE / path).read_bytes()) for path in expected_files),
            "package source files must be ASCII")
    timings["full"] = time.perf_counter() - suite_start
    require(timings["full"] < 300, f"suite exceeded 300 seconds: {timings['full']:.3f}s")

    print(f"PASS public=5 private={len(private)} exports=1 files={len(expected_files)}")
    print(f"PASS corpus={len(corpus)} malformed={len(malformed)} boundaries={boundary_checks}")
    print("PASS filesystem DFS, cycles, limits, parse/input consistency, and --no-process")
    print("PASS real @dep root/transitive metadata and isolated incremental rebuild")
    print("TIMING " + " ".join(f"{name}={seconds:.3f}s" for name, seconds in timings.items()))
finally:
    work_context.cleanup()
