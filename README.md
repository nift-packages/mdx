# mdx

`mdx` preserves MDX source and UTF-8 byte positions, discovers local document
imports, and registers them with Nift. Pure `parse`/`input` remain dependency-free
and work with `--no-process`. Optional trusted rendering compiles MDX to ordinary
static HTML through a build-time helper; no browser React/JSX runtime is required.

Implementation is experimental while release gates remain open. Linux/macOS
with Node 22/24 pass CI. Windows Nift file input is currently excluded, and the
Capgo corpus/performance/adapter certification gate has not passed. Neither
Capgo website is started. See [checkpoint evidence](investigation/GAMEPLAN.md).

The sole export is `mdx`, with these public methods:

| Method | Result / purpose |
| --- | --- |
| `parse(source)` | Pure bounded preservation document |
| `input(path)` | Preservation document plus local graph and Nift dependencies |
| `with_profile("bounded" or "trusted")` | Independent configured facade |
| `prepare(documents)` | One helper invocation for a document batch |
| `html(document)` | HTML string; file input requires the current prepared batch |

```f
@import("mdx")
document := mdx.parse("# hello\n\n<Card>{name}</Card>\n")
file_document := mdx.input("content/page.mdx")
```

## Optional rendering quick start

Install the package through Nift's normal Git installation and provision the
optional, locked Node dependencies once:

```sh
nift add mdx
npm ci --ignore-scripts --prefix .nift/packages/mdx/renderer
```

Set `.nift/mdx-render.json` to `{"policy":"trusted"}` only for reviewed authored
project sources. Rendering executes expressions, exports, adapters and plugins
with ordinary build-host privileges. The deadline is not an OS sandbox; untrusted
rendering is unsupported. Rendering never installs packages or accesses a package
registry. See [runtime installation/offline instructions](renderer/README.md).

Add a `prepare.f` project pre-build hook:

```f
@import("mdx")
prepared := mdx.prepare([
    mdx.input("content/one.mdx"),
    mdx.input("content/two.mdx")
])
```

In `.nift/config.json`, set `"pre build":"prepare.f"` inside the `config` object.
A template under `templates/` can then use the convenient composition:

```html
@import("../.nift/packages/mdx/src/mdx.f")
$[mdx.html(mdx.input("content/one.mdx"))]
```

File-backed `html` refuses missing/stale root/config preparation and never starts
a process per target. Every build must run the batch after input changes; prepared
records are not an independently validated cache for arbitrary external changes.
Inline `mdx.html(mdx.parse(...))` is an explicit one-off render and starts a helper.
Project local-path installations create symlinks which build templates may reject;
use Git installation for normal sites. The [copyable installed example](examples/basic)
is tested by automation, including unchanged builds and dependency metadata.

React static rendering is replaceable build-time machinery behind the public
MDX document-to-HTML abstraction. Project component factories receive a semantic
`element` constructor. General mappings/imports/plugins, static component rules,
all dependency classes, structured diagnostics, trusted profiles and the optional
content cache are documented in [renderer/README.md](renderer/README.md).

Normal builds batch all documents. Measured installed synthetic sites take
6.94/36.22/80.12 seconds cold at 100/500/1,000 pages and 3.65/18.77/44.82 seconds
unchanged. Parsing dominates; these are full-pipeline timings, not Capgo claims.
The actual pinned Capgo parser scan accepts 518/519 canonical docs and takes
204.84 seconds cumulatively. These unresolved gates prevent Capgo implementation.

## Preservation-parser scope

The research references are MDX 3.1.1 and CommonMark 0.31.2:

- <https://mdxjs.com/packages/mdx/>
- <https://spec.commonmark.org/0.31.2/>

The preservation scanner is not an MDX compiler, JavaScript parser, JSX
transformer, YAML parser, or CommonMark parser. It never executes code or renders
HTML; the optional helper performs compilation/rendering separately. It recognizes
only enough
structure to preserve and locate these node types:

- `markdown`
- `code_fence`
- `inline_code`
- `import`
- `export`
- `expression`
- `jsx_element`
- `jsx_fragment`

Everything else remains exact `markdown` source. Backtick and tilde fences
follow the relevant CommonMark protection behavior: up to three leading
spaces, at least three matching markers, and a closing run at least as long as
the opening run. An unclosed fence extends through EOF and is valid. Backtick
inline code, fenced code, backslash-escaped `<`, and backslash-escaped `{`
shield MDX-looking text.

Root-line lowercase `import ` and `export ` declarations are recognized only
at byte zero, immediately after frontmatter, after a blank physical line, or
consecutively after another declaration. A declaration line inside an open
Markdown paragraph remains Markdown. Declarations are structurally scanned
across quotes, comments, templates, and bracket nesting. Static
side-effect and `from` import specifiers are extracted. Re-export specifiers
are retained but do not create automatic dependencies in version 0.1. The
scanner does not validate JavaScript semantics.

Expression containers preserve their interior as `value` and never execute
it. The scanner shields single/double strings, escapes, line/block comments,
template literals and `${...}`, nested delimiters, and practical regular
expression literals including character classes. Empty and comment-only
expressions are accepted.

JSX supports nested elements, fragments, self-closing elements, boolean and
quoted attributes, expression attributes, spreads, and expression children.
Names are intentionally ASCII-conservative: a letter first, followed by
letters, digits, `_`, or `-`. An element name may have either one namespace
suffix or one or more member suffixes, never both; an attribute may have one
namespace suffix and no member suffix. Closing names match case-sensitively. Unquoted attribute
values, fragment attributes, mismatches, unclosed tags, and HTML comments are
diagnostics. Raw HTML is handled by these same JSX rules.

## Result Contract

Both calls return an object with exactly these keys, in this order:

```text
ok, source, path, frontmatter, imports, exports, nodes, dependencies, diagnostics
```

`parse` is pure: `path` is `null`, `dependencies` is empty, and no filesystem
or dependency primitive is called. A valid in-limit source string is preserved
exactly, including Unicode and line endings. Invalid input type and oversized
source results use `source: null`. Structural failures preserve an in-limit
string but clear `imports`, `exports`, `nodes`, and `dependencies`, preventing
a partial tree from appearing authoritative.

Frontmatter has exactly:

```text
present, source, body, start, end
```

Raw frontmatter is a Nift extension. It is recognized only when byte zero is an
exact `---` line and closes at a later exact `---` line. `source` includes both
delimiter lines and the closing line ending when present; `body` is the exact
text between them. No YAML parsing occurs. `start` and `end` are points, and an
absent frontmatter value is `{present:false,source:"",body:"",start:null,end:null}`.
An unclosed opening delimiter is a structural error.

Every node has exactly:

```text
type, source, name, value, attributes, children, position
```

Every attribute has exactly:

```text
name, kind, value, source, position
```

Attribute `kind` is one of `boolean`, `string`, `expression`, or `spread`.
Every position has `start` and `end`; every point has `offset`, `line`, and
`column`. Offsets are zero-based UTF-8 bytes with an exclusive end. Lines and
columns are one-based and columns count UTF-8 bytes. CRLF is one line break;
bare CR and LF are also line breaks.

An import record has exactly:

```text
kind, specifier, source, local, extension, dependency, position
```

`kind` is `import` or `side_effect`. An export record has exactly `source`,
`specifier`, and `position`. A diagnostic has exactly `code`, `message`,
`severity`, `path`, `line`, `column`, and `offset`; severity is `error` or
`warning`. Diagnostic wording is noncontractual. Codes and shape are intended
for automation.

## File Input And Dependencies

`mdx.input(path)` resolves against Nift's current `pwd()`. It accepts a
project-root-relative path or an absolute path inside that directory,
normalizes POSIX `/`, `.`, `..`, and repeated
slashes, verifies existence, rejects a confirmed directory using the safe
`path + '/.'` heuristic, registers the root with `@dep('$[path]')`, reads it,
parses it, and performs depth-first dependency discovery.

An import is local only when its specifier starts with `./` or `../`. Automatic
dependency candidates are exact, case-sensitive `.mdx` and `.md` suffixes with
no query or hash. `.mdx` files are recursively parsed; `.md` files are
registered but not parsed. Local `.js`, `.jsx`, `.ts`, and `.tsx`, and bare or
scoped imports, remain records but are not dependencies. Re-exports are not
dependencies in version 0.1.

Dependencies have exactly `path`, `from`, `specifier`, and `depth`. The root is
not included. Normalized paths are deduplicated in DFS discovery order, and
each is registered once. Cycles produce `dependency_cycle`; nested parse
diagnostics carry the nested path. Missing paths are structured before
`@dep` is called.

Nift's `@dep` supplies the authoritative project and symlink confinement. A
lexically determinable escape is structured as `path_escape`; a symlink escape
may remain a Nift hard failure. There is no generic package-level stat or
recoverable filesystem exception mechanism, so permission changes, races after
`exists`, and some unusual filesystem errors can also remain hard failures.
No additional symlink policy is implemented. In a standalone script, parsing
and reading work in the current Nift project context, but dependency metadata
is useful only while rendering a tracked target. Package-name imports are a
Nift concern: a standalone consumer must install `mdx` in its own `.nift`
project, while a template may import the installed entry file by its actual
relative path when package-name lookup is unavailable in that template scope.

## Limits

These original bounded defaults remain unchanged. `trusted := mdx.with_profile("trusted")`
selects 65,536 bytes/file, 8,192 physical lines, 65,536 bytes/line and 2,097,152
aggregate graph bytes; other safeguards remain below. Selecting capacity does not
opt into execution. See [profile decisions](investigation/checkpoints/CP13.md).

Limits are deterministic and measured before unbounded parser growth:

- 4,096 UTF-8 bytes per file
- 1,024 logical lines per file (a terminal line ending does not add an empty line)
- 16,384 UTF-8 bytes per physical line (a defensive scanner bound currently
  shadowed by the smaller file bound)
- 1,024 aggregate syntax objects per file, including all nodes and JSX
  attributes
- 256 imports per file
- 64 expression nesting levels and 48 JSX element/fragment levels
- 256 bytes in a backtick or fence delimiter run
- 64 recursively opened files, including the root
- dependency depth 16, with the root at depth zero
- 16,384 aggregate UTF-8 source bytes across recursively opened files
- 4,096 UTF-8 bytes per input path and 4,000 per import/re-export specifier

These are deterministic resource boundaries for controlled offline builds, not
a latency guarantee for untrusted or high-concurrency request handling. Exact
admitted syntax and recursive graph limits can take seconds in Nift's
interpreter. Callers accepting external content should enforce their own
smaller ingress and concurrency limits before calling this package.

Representative codes are `source_too_large`, `too_many_lines`,
`physical_line_too_long`, `too_many_syntax_objects`, `too_many_imports`,
`nesting_limit`,
`dependency_file_limit`, `dependency_depth_limit`, `aggregate_source_limit`,
`path_too_long`, and `specifier_too_long`. Whole-file reading is unavoidable
with Nift's current `open` API; the per-file byte limit is checked immediately
after the read.

## Testing

```sh
python3 tests/test_mdx.py /path/to/nift
NIFT=/path/to/nift python3 tests/test_parser_parity.py
NIFT=/path/to/nift python3 tests/test_profiles.py
NIFT=/path/to/nift python3 tests/test_render.py
```

The suite certifies direct and installed imports, exact exports and hidden
helpers, arity, deterministic `--no-process` operation, ASCII package files,
source reconstruction and byte slices, generated adversarial syntax, all
structural forms above, exact and over-limit cases, malformed worst cases,
filesystem graphs and cycles, Unicode/space paths, DFS order and deduplication,
parse/input consistency, recursive limits, confinement behavior, and a real
tracked two-target website. The website test changes only a transitive `.mdx`
file and verifies that metadata contains the root and transitive dependencies
once and only the consuming target rebuilds.
