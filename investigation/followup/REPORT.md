# Follow-up: Windows input, Capgo parser cost, and rendering feasibility

Investigated 4 October 2026. This report supersedes the interpretation that CP22's failed gate ends the approach. The gate remains incomplete; there is a credible compiler-based route to full-corpus certification. No larger API change, production parser optimization, capacity-policy change, Nift core change, or Capgo website implementation is included.

## Answers to the ten requested questions

1. **Windows package-side fix:** neither `os()=="windows"` with `\\.` nor the other inspected existing filesystem operations provides a safe general predicate. Retain the documented Windows Nift-input exclusion. Independent Node rendering remains supported.
2. **Parser cost:** dense preservation objects, position bookkeeping, and interpreter/string dispatch dominate the evidence. It is broad cost with a dense tail, rather than package startup or transitive document traversal. The original 204.836 seconds reproduces as 166.779 seconds on this workstation with unchanged production source; this difference is run/environment variability, not an optimization.
3. **Reduction without core changes:** no tested parity-preserving candidate demonstrates a reliable full-corpus improvement. A position-removal ablation cuts the slow-page sample by about 38%, but breaks the API and cannot ship. An explicit rendering-only compiler path offers the substantial measured opportunity: 2.664 seconds of AST discovery and 3.768 seconds of compilation across all 526 authored files.
4. **Full preservation tree for HTML:** no. The renderer consumes source, frontmatter, and dependency/configuration information; it does not use the preservation node tree. Existing `html(input(...))` still promises full input parsing. Keep it compatible and propose a distinct render-preparation entry point.
5. **Fast scanner and incrementality:** use the authoritative MDX compiler AST rather than a regex or second incomplete grammar. It matches all 518 accepted corpus import records. Exact incremental correctness still needs explicit graph/manifests and certification described below. A fixture semantic disagreement prevents silently substituting it for the preservation parser.
6. **Projected clean MDX stage:** approximately **8–15 seconds** for compiler discovery, compile/render, graph validation and transport, assuming adapters and one helper process. This is a planning estimate, not a measured Capgo build; merge discovery into the existing compile traversal rather than paying for both prototype passes.
7. **Projected one-page incremental MDX stage:** approximately **1–2 seconds**, conditional on a correctly validated persisted graph/cache and unchanged global dependencies. Today `prepare()` does not already know the dirty set. Rescanning/recompiling all roots each time would remain nearer the clean-stage estimate. Global configuration changes may rebuild the whole corpus.
8. **149 failures:** 128 Starlight imports, 3 PackageManagers imports, 11 custom Astro imports, 7 HTML-style-string/React-style-object mismatches. These are first failures per page; later failures may be masked.
9. **Ownership:** the 142 component-import failures belong to Capgo adapters; the 7 style failures need a Capgo AST transform or native-element adapter. No primary failure establishes an MDX syntax/compiler defect. The generic package needs the proposed rendering orchestration and dependency contract, not Capgo-specific components.
10. **Full corpus route:** yes: explicit semantic render preparation, certified exact dependency manifests, project adapters/assets/aliases/style normalization, and a full 519+7 render/interaction/incremental gate. **All 526 files already compile in isolation**, but that is not full rendering or visual parity certification. Neither website begins here.

## Windows investigation

Core inspected: upstream main `1370a97b66a48af3a66d47d822800cdeb436c295`. `os()` reports lowercase host values; `platform()` is the selected target. Current checked-path handling applies absolute lexical normalization before filesystem operations.

[CI run 37191996078](https://github.com/nift-packages/mdx/actions/runs/37191996078) at `f3c3b614652d920571ca1f3e892eee1b4db4893b` tests Linux/macOS/Windows with Node 22 and 24. Linux/macOS full jobs pass. Windows probes, byte-exact 165-case preservation parity, and independent 30-case helper tests pass; existing Nift-input-dependent checks remain red. Saved six-platform records are `ci-filesystem-*.json`; [matrix metadata](filesystem-matrix.json) identifies job results.

Both Windows spellings normalize identically, including a trailing slash:

| Input | Nift normalized path (Node 22 runner) | exists |
|---|---|---|
| `normal.mdx/.` | `C:/Users/RUNNER~1/AppData/Local/Temp/mdx type spaces 0hlkk8xy/normal.mdx/` | true |
| `normal.mdx\.` | `C:/Users/RUNNER~1/AppData/Local/Temp/mdx type spaces 0hlkk8xy/normal.mdx/` | true |

The same false directory classification occurs for ordinary/nested files, relative and absolute drive paths, spaces, actual UTF-8 café names, and backslash-relative paths on both Windows jobs. Directories also return true. `/`, `\`, `/./` and `\.\` do not distinguish types. Extended `\\?\C:\…` spelling is normalized into `C:/?/C:/…`; it reports missing for both files and directories. Unix `/.` retains its expected distinction; backslashes remain literal filename characters there.

Inspected `ParserExpression.cpp`: checked-path resolver around 1331; `exists` around 1530; `ls/open/open_bytes` around 1537–1539; managed file opening around 1890. Internal C++ file-type primitives are not exposed as a suitable F predicate. `ls(file)`, `open(directory)`, `open_bytes(directory)` and managed opening of a directory exit with an error even inside `try/catch`; they do not produce a recoverable result. `ls(file+"/*")` and `ls(emptyDirectory+"/*")` both return empty. Recursive glob results do not distinguish the starting file/directory, skip hidden entries or symlinks inconsistently, and are potentially unbounded. File metadata/path methods expose existence/normalization, not a reliable type. Native FFI would introduce native execution/ABI dependencies into the no-process preservation contract. No safe general package-side fix was found.

The committed fixes improve investigation and test accuracy: raw UTF-8 fixture files replace JSON-string source transport in the parity test; probes assert byte-exact Unicode paths; CI removes stale evidence before uploading. They do not claim Windows input is fixed.

## Actual corpus distribution

Upstream Capgo pinned at `7d5b69d6ba8a6630384dffc7d012431ee3ed22ec`. Production scanner SHA-256 `febc5e0a8e83fb7628ad637247de67de8e353fc64ebfa5f7b3a183049c984d80`. One Nift 4.6 invocation, one trusted facade, 519 canonical documents; reads and result serialization excluded from per-page timers. Wall time 167.621 seconds; accumulated parse time 166.779 seconds; 518 accepted. Node is not involved in this pure parsing benchmark.

[All 519 rows, sorted slowest first](corpus-baseline.csv) contain paths, bytes, lines, syntax objects, JSX elements, expressions, imports and milliseconds. [JSON](corpus-baseline.json) includes detailed counts, source hashes, diagnostics and methodology. Syntax objects count nodes plus attributes; expression counts also include expression/spread attributes. Quantiles use nearest rank. Tail page counts round upward.

| Median | p90 | p95 | p99 |
|---:|---:|---:|---:|
| 198 ms | 703 ms | 994 ms | 1,843 ms |

| Slowest fraction | Pages | Cumulative ms | Share |
|---|---:|---:|---:|
| 1% | 6 | 13,961 | 8.37% |
| 5% | 26 | 39,043 | 23.41% |
| 10% | 52 | 59,888 | 35.91% |
| 20% | 104 | 90,042 | 53.99% |

Worst 20 (paths relative to canonical docs directory):

| Path | Bytes | Lines | Objects | JSX | Expressions | Imports | ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| plugins/intent-launcher/index.mdx | 35991 | 364 | 1221 | 0 | 0 | 0 | 3805 |
| cli/reference/build.mdx | 29555 | 479 | 589 | 170 | 0 | 0 | 2556 |
| cli/commands.mdx | 22549 | 488 | 504 | 10 | 0 | 1 | 1933 |
| builder/ios.mdx | 37758 | 843 | 433 | 25 | 4 | 5 | 1925 |
| plugins/inappbrowser/getting-started.mdx | 43342 | 1431 | 285 | 0 | 0 | 0 | 1899 |
| plugins/firebase-authentication/getting-started.mdx | 26650 | 987 | 345 | 0 | 0 | 0 | 1843 |
| cli/reference/bundle.mdx | 15797 | 309 | 385 | 108 | 0 | 0 | 1742 |
| builder/configuration.mdx | 18516 | 405 | 408 | 6 | 1 | 2 | 1613 |
| plugins/updater/debugging.mdx | 22508 | 863 | 289 | 3 | 0 | 1 | 1584 |
| plugins/social-login/apple/android.mdx | 14470 | 303 | 323 | 47 | 2 | 2 | 1463 |
| builder/github-actions.mdx | 22283 | 492 | 339 | 20 | 0 | 1 | 1430 |
| plugins/updater/settings.mdx | 12755 | 551 | 297 | 5 | 0 | 1 | 1367 |
| webapp/logs.mdx | 18137 | 240 | 373 | 9 | 0 | 0 | 1321 |
| plugins/youtube-player/getting-started.mdx | 16162 | 702 | 247 | 0 | 0 | 0 | 1301 |
| plugins/social-login/oauth2.mdx | 19161 | 641 | 254 | 5 | 0 | 1 | 1295 |
| builder/credentials.mdx | 22507 | 586 | 292 | 9 | 0 | 1 | 1268 |
| plugins/camera-preview/getting-started.mdx | 21750 | 831 | 223 | 0 | 0 | 0 | 1245 |
| getting-started/onboarding.mdx | 17134 | 561 | 262 | 33 | 0 | 1 | 1205 |
| plugins/social-login/facebook.mdx | 26214 | 752 | 177 | 9 | 0 | 1 | 1072 |
| live-updates/channels.mdx | 26104 | 331 | 286 | 8 | 0 | 1 | 1040 |

Intent's 3,805 ms row is the production rejection time. Its complete 1,221-object count and 4,470 ms full parse come from an isolated larger-ceiling copy, explicitly flagged in the data. Do not combine that complete count with a claim the production parser accepted it.

The slowest fifth contributes 54%; the remaining 415 files still contribute 46%. Median syntax-object count is 41; the total including the isolated outlier count is 35,591. Pearson association with milliseconds: objects 0.959, bytes 0.847, lines 0.738, JSX 0.474, expressions 0.176, imports 0.281. Correlation is not causal attribution. There are no relative MD/MDX document edges in this canonical corpus, so transitive document reparsing cannot explain this measurement.

Package import measured 11 ms; ten trusted facades cost 2 ms. Batching setup is already achieved in the benchmark. Current website preparation does parse every root, and a dirty target's `input()` parses it again. Moving helper startup into a batch did not remove these pure-parser costs. Mutable shared parser state is not an appropriate shortcut.

[Native instruction profile](native-profile.txt) for the real median-cost `plugins/intune/android.mdx` page totals 1,875,334,140 instruction references. Selected string/memory primitives account for about 57% of self instructions; expression dispatch, argument recognition and balanced-token scanning also contribute. This includes import/startup and measures instructions, not elapsed-time fractions or source-copy attribution. F-level inclusive rounded-millisecond instrumentation is perturbed, overlaps recursion and loses short calls to rounding; its zero position timings do not mean positions are free.

[Slow-page ablations](sample-mdx-no-nodes.json): baseline 32,403 ms, null positions 20,069 ms, null node/attribute constructors 34,492 ms. Removing positions changes output and is inadmissible; removing allocation alone did not help. A source-byte local view was inconclusive. A binary-search midpoint candidate improved one sample but needs an explicit integer conversion on returned line numbers. The corrected typed candidate passed 165 byte-exact serialized cases and integer-type checks, yet its [full corpus](corpus-midpoint-typed.json) costs 170,084 ms versus 166,779 ms baseline. Run variation prevents a reliable benefit claim; **do not ship it**. No production optimization is included.

## Trusted capacity, separate from performance

Intent Launcher is legitimate authored API prose: 611 Markdown spans plus 610 inline-code nodes, no JSX, expressions, imports or attributes. Preserving alternating prose/code spans explains the count; there is no unnecessary intermediate syntax object count to remove compatibly. The next-largest corpus document has 589 objects. The present 1,024 ceiling is insufficient for this legitimate trusted page.

A **provisional 2,048-object trusted ceiling** would cover the observed maximum with headroom while leaving bounded/untrusted limits unchanged. [Isolated boundary probe](capacity-probe.json) accepts exactly 2,048 objects and rejects 2,049 with a structured diagnostic, recording time and process RSS. This small observation does not establish a universal resource guarantee. Keep byte/line/graph/nesting bounds and measure the maximum supported workload across platforms before changing policy. No limit is raised in production. Faster render preparation should apply its own bounded source/graph/execution policy rather than tying semantic compilation to preservation-object count.

## Compiler dependency experiment and compatibility boundary

[Compiler audit](dependency-audit.json): 519 canonical MDX + 7 English blog MDX, zero AST/compile failures, 2,663.696 ms discovery, 3,767.516 ms compilation, 6,872.382 ms wall. It strips frontmatter with the production helper's existing source preparation, uses pinned MDX/GFM, recursively inspects mdast/ESTree import declarations, and records dynamic imports/reexports as unsupported. It does not evaluate content, execute project adapters, call Nift `@dep`, or certify graph confinement. Compilation and discovery are separate prototype passes; production could reuse the compile AST.

[Corpus comparison](corpus-import-parity.json) verifies identical source hashes and identical import specifier/dependency flags for all 518 accepted preservation parses. [312 existing/seeded/import/adversarial fixtures](dependency-fixtures.json) use byte-identical source transport. Both parsers accept 278; the semantic compiler rejects 34 inputs that the preservation grammar need not semantically validate. One jointly accepted fixture differs: a contrived mixed JSX/code-fence/CRLF region makes preservation count `./x.mdx`, while the compiler regards that text as code. This proves the proposed semantic rendering scan is **not a drop-in replacement** for preservation import discovery. Fences, code spans, comments, strings/templates and expression-contained false import text are tested; dynamic import and reexport detection are recorded for explicit refusal policy.

[Actual production helper latency](helper-latency.json), with ordinary no-import docs: Intent renders successfully in 557 ms process wall, of which 202 ms is compile/evaluate/render; the largest-by-byte Inappbrowser page renders in 441 ms wall, of which 93 ms is compiler/evaluation/render. This bypasses preservation only in the investigation; it does not make current `html(input(Intent))` succeed.

## Proposed architecture — investigate/report only

Keep `parse()` and `input()` unchanged, including no-process behavior, exact preservation shape and dependency contracts. Keep direct `html(input(...))` compatibility. Add a distinct render-only preparation contract, provisionally `prepare_paths(paths)` plus `html(prepared(path))`; these names are proposals, not implemented APIs. It supplies a source/frontmatter envelope and compiler-semantic graph instead of a fabricated empty preservation tree.

Required correctness design:

- Discover imports from the AST actually compiled; retain existing dynamic-import/reexport refusals, Markdown-leaf semantics, aliases/mapping allowlists and structured diagnostics. Do not evaluate modules during discovery.
- Use production realpath/stat confinement, cycle/depth/aggregate bounds and explicit execution policy. Track lexical requested paths and canonical targets; revalidate symlink retargeting, missing files, escapes and additions/removals.
- Produce complete per-root manifests for root, transitive MDX/MD, used adapter modules, configuration, plugins, declared assets, helper/runtime/lock identity and semantic options. Each consuming Nift target registers its dependencies **before** accepting HTML. Hook-only registrations cannot replace target registrations.
- Use stable per-root artifacts, atomic writes and source/options validation on every mandatory prebuild hook. A changing global nonce as a target dependency would dirty every target and defeat the incremental design.
- A persisted graph and reverse-consumer map can identify changed roots/closures. Current `prepare()` does not provide this already. Configuration/plugin/policy/runtime/environment changes invalidate affected or all roots; revalidate transitive graph identity even on cache hits. Never reuse stale graph edges because source bytes alone match.
- Certify no-change, one-page edit, imported MDX/MD edit, adapter/config/plugin/asset edit, unrelated target, deletion/addition, symlink retarget, cycle/escape, concurrent build and stale-hook rejection. Re-run supported-platform input/render integration separately; Node stat does not solve pure Windows `input()`.

The 8–15 s clean and 1–2 s incremental estimates are MDX-stage budgets conditional on this design, not whole-site guarantees. The present preservation route still incurs at least one roughly 167 s corpus pass per preparation; a clean build can also repeat preservation per target. Avoid promising fast incrementals if the hook still parses or recompiles every root.

## Failure ownership and next certification gate

[All 149 classified records](failure-classification.json) retain original diagnostics and ownership. Counts are primary first failures, not an exhaustive inventory of every failing import:

| Primary category | Count | Owner |
|---|---:|---|
| Starlight component import | 128 | Capgo adapter set |
| PackageManagers import | 3 | Capgo adapter set |
| Custom Astro import | 11 | Capgo adapters: 7 CTA, 2 YouTube, 1 PluginSetupSteps, 1 Mermaid |
| HTML style string / JSX style object | 7 | Capgo AST transformation/native-element adapter |
| Asset import / actual syntax compile failure / other | 0 primary | Asset and alias requirements can be masked by earlier imports |

The generic diagnostic `mdx_compile_failed` also covers an import-policy refusal; it is not proof of an actual syntax rejection. All 526 isolated compiles succeeding supports that distinction. Actual AST inventory additionally includes relative image assets, configuration imports, questionnaires and plugin-directory data. Default/named/namespace mapping and component factories are already reusable package capabilities. Asset copying/URLs, Capgo aliases/data/localization, components, and HTML style normalization belong to the project. Normalize style with a proper project AST transform or adapter, not raw-source regex rewriting.

See [smallest Capgo adapter plan](CAPGO-ADAPTER-PLAN.md). Next gate: render all 526 with adapters, test semantic text/link/media/interaction behavior, certify exact incremental changes and measured budgets, then pursue visual parity. CP22 remains open while this route is assessed; no blanket permanent rejection of Capgo is implied.

## Reproduction

Use the current Nift 4.6 executable (`NIFT` override supported), pinned upstream clone and optional renderer dependencies. Global pinned dependencies are available through `MDX_NODE_MODULES=/usr/local/lib/node_modules`; local installation remains supported. The global `/usr/local/bin/nift` on this workstation is older and was not used.

```sh
python3 investigation/followup/filesystem_probe.py
python3 investigation/followup/profile_corpus.py /tmp/capgo-upstream-planning
python3 investigation/followup/variants.py
python3 investigation/followup/profile_sample.py src/mdx.f /tmp/mdx-no-positions.f /tmp/mdx-no-nodes.f
python3 investigation/followup/profile_corpus.py /tmp/capgo-upstream-planning /tmp/mdx-midpoint-typed.f midpoint-typed
MDX_NODE_MODULES=/usr/local/lib/node_modules node investigation/followup/dependency_audit.mjs /tmp/capgo-upstream-planning
python3 investigation/followup/dependency_fixtures.py
python3 investigation/followup/capacity_probe.py
python3 investigation/followup/helper_latency.py
```

Variant scripts write temporary copies only. Experimental variants must not be installed as the package. Timings are single-run observational evidence, not statistical performance guarantees. Historical checkpoint results remain retained separately.
