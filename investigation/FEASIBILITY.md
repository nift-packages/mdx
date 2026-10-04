# Dependency-aware MDX → HTML feasibility

Investigation date: 2026-10-04. Baseline: `nift-packages/mdx` commit `55843fa`, version 0.1.0. This is a report and isolated prototype, not the production rendering implementation. Nift core, the production parser, limits, manifest, and existing tests remain unchanged. Capgo implementation has not started.

## Decision

`mdx.html(mdx.input("content/page.mdx"))` is feasible without changing Nift core. Recommend an additive facade method, optional pinned Node renderer machinery, `@mdx-js/mdx` compilation, and React **only at build time** using `renderToStaticMarkup`. Output is ordinary HTML. Keep `parse/input` usable without processes or npm installation. The normal production path must be batched before full-site certification; a synchronous scalar method cannot transparently batch separate page builds without orchestration or persistence.

Suitable for `capgo` as a rendering architecture, **not yet a certified drop-in Capgo implementation**. Parser performance/limits, Starlight/Astro adapters, asset imports, configuration invalidation, and executable-content policy must be resolved first. Static MDX output does not make the whole Capgo project static-only: downloadable applications can use users' own APIs. Capgo styling may use blue/light themes; Labs catalogue/report UI retains dark/no-blue rules. Use JavaScript for pagination.

## Current contract and guarantees

Read the complete README, manifest, 965-line source, contract test and Python regression driver; history contains the initial feature commit. Only `mdx.parse(source)` and `mdx.input(path)` are public. Result keys are exactly `ok,source,path,frontmatter,imports,exports,nodes,dependencies,diagnostics`. Keep this ordered shape and existing diagnostics unchanged. `html` consumes the preserved source; the existing preservation nodes are not a Markdown semantic AST and should not be directly translated into HTML.

Nodes preserve source, type, name/value, attributes, children and UTF-8 byte positions. Recognized regions include Markdown, fences, inline code, imports/exports, expressions, JSX elements/fragments. JSX names and supported prop syntax are deliberately narrow. Expression scanning balances delimiters while handling strings, comments, template literals and practical regexes; it does not evaluate or validate all JavaScript semantics. This is a bounded MDX-like preservation parser, not a complete MDX compiler.

Raw frontmatter is recognized only at byte zero with exact delimiter lines. It has `present,source,body,start,end`; body is raw YAML text, not parsed data. Unclosed frontmatter fails. `parse` is pure; source/type/structural issues produce structured results, retaining in-limit source on structural errors. Out-of-bound source is not retained. Nift filesystem/dependency primitives can still cause hard runtime failures.

`input` normalizes project-relative paths, registers root and traversed local `.mdx` files via private `@dep`, reads each once, and returns DFS dependency records with path/from/specifier/depth. Local `.md` imports are registered but **not opened or recursively parsed**. Supported graph imports are relative, case-sensitive `.md/.mdx`, without query/hash; bare packages, JS/TS components and re-export dependencies are not followed. Cycles/dedup/missing files/lexical escapes have diagnostics. Symlink confinement ultimately belongs to Nift `@dep`, not a JS check. Renderer support must not reinterpret that boundary.

Tests cover exact API/result shapes, manifest purity, private members, arity, forbidden execution capabilities, ASCII source, installed/direct use, pinned Git installation with removed origin, deterministic no-process parsing, generated/malformed/boundary corpora, UTF-8/path behavior, recursion/cycles/limits, timing bounds, and a two-target incremental website. Existing final inventory assertion expects exactly seven package files and erroneously includes `.git`: test from a clean archive for baseline certification. Future implementation must intentionally extend inventory and capability checks to distinguish pure parsing from optional rendering, while preserving the substantive tests.

Installed `/usr/local/bin/nift` 4.5.0 rejects `encode("utf-8")`; local `/home/nick/Repositories/nift/nift/nift` 4.6.0 runs the parser. Thus document and verify the minimum supported Nift version, rather than advertising compatibility with the older installed binary. No core rebuild or edits were made.

## Compiler and renderer

[MDX compiler API](https://mdxjs.com/packages/mdx/) produces JavaScript/VFile, not HTML. `compile` gives a useful explicit compiler stage and plugin pipeline. `run` executes function-body output with a JSX runtime; `evaluate` combines those operations, making separate timing/error stages less convenient. Program output is useful for imported modules. React is one supported automatic JSX runtime, not intrinsically required by MDX. A custom runtime could make HTML strings but must correctly implement escaping, fragments, children, props, components, DOM attributes and compiler/runtime semantics; that burden is unjustified initially.

The proposed chain is MDX source → compiler → component/module → JSX runtime and static renderer → HTML. [React static renderer](https://react.dev/reference/react-dom/server/renderToStaticMarkup) provides noninteractive HTML, with limited Suspense behavior. Require synchronous static adapters; do not accidentally render a fallback when async data was expected. No React/JSX scripts or hydration need to ship. Tabs/search/forms can attach small vanilla JS modules to semantic HTML; their scripts/assets remain ordinary project dependencies.

Prototype exact direct pins: `@mdx-js/mdx@3.1.1`, `react@19.3.0`, `react-dom@19.3.0`, `remark-gfm@4.0.1`, `rehype-slug@6.0.0`; direct packages are MIT. Lockfile pins transitives/integrities; transitive notices need a release audit. Installed tree measured 19 MiB, 138 added packages. Install with `npm ci --ignore-scripts`; render never installs or fetches dependencies. Offline use requires a previously provisioned matching tree/cache. MDX is ESM-only; select/test a current supported Node LTS, not merely its historical minimum Node 16. This investigation ran Node 22.22.1. Bun was unavailable and is **not certified**; npm dependencies alone are not proof of Bun support.

## Invocation options and API

| Choice | Assessment |
| --- | --- |
| External argv-based helper | Feasible with existing `run`; portable initial scalar implementation, expensive cold starts. Avoid shell interpolation. |
| One process for an explicit batch | Required normal production architecture; use an internal helper batch protocol and project build-stage orchestration. Add `html_many` only if needed after API design. |
| Persistent helper | Potentially useful for repeated scalar calls, but lifetime/socket/concurrency/restart/auth/process-policy complexity. Not required to establish feasibility; not benchmarked. |
| FFI/embedded JS | Nift has C ABI FFI, not an existing embedded MDX/Node bridge. Native runtime distribution would add substantial complexity. No core changes recommended. |
| Public companion package | Keep renderer internals optional/separate while retaining the `mdx.html` facade. Avoid forcing users to abandon the preferred composition. |

Recommended `html(document, options?)` returns a string on success and fails the target on error. Keep parser diagnostics distinct and refuse documents with `ok:false`. Reserve a structured `render` result internally rather than changing parser objects. Options should identify trusted component/config paths and policy; Nift JSON values cannot transport JS function closures. No `input_html` duplication is needed. `parse(source)` supports inline content; relative imports need an explicit base path and dependency registration, otherwise reject them.

A JSON request/response protocol should include version, request ID, document/source/path, dependency manifest, config/policy, HTML or structured diagnostics and renderer-discovered dependencies. Use temp request files or documented stdin streaming, not large argv payloads; Windows and OS argument limits matter. Response caps, deadlines, stderr isolation, atomic output/cache writes and exit-code checking are required. `--no-process` leaves parsing available and causes rendering to fail clearly. It is a capability restriction, not an OS sandbox.

Prototype deliberately uses a small argv request, stdout HTML for the Nift facade and JSON for benchmarks; production transport is not implemented. It supports only registered relative MD/MDX imports and detects cycles. It rewrites compiler ESTree import sources into generated ESM modules. It is not a general JS/Astro loader, component dependency collector, secure sandbox, cache, or production facade. Imported child documents in this prototype do not automatically inherit the root component mapping; production must propagate mapping/context and test components inside transitive documents.

## Components, frontmatter and Markdown

Use project-owned JS adapters returning React elements, selected by an explicit mapping configuration. Named MDX components receive evaluated props and rendered child elements. `<Aside type="warning">` maps to `<aside data-type="warning">`; Steps to ordered structure, Cards to links/sections and Tabs to accessible semantic structure plus small JS. Unknown components throw, rather than disappearing. Avoid arbitrary string concatenation or `dangerouslySetInnerHTML`; optional HTML-returning adapters need a deliberate escaping/trust contract. Nift or schema templates are possible for a limited literal-only subset but not a natural general JSX execution interface.

Imported Starlight components override name injection: Capgo requires an explicit compiler import rewrite/resolver mapping for `@astrojs/starlight/components`, not just a `components` object. Astro files cannot simply be loaded by Node/React. Resolve aliases/asset imports intentionally. PackageManagers, MermaidGraph, YouTubeEmbed, PluginsDirectory, questionnaires and blog CTA require adapters; interactive features need their own browser behavior. This work has not ported them.

Render document body while preserving frontmatter unchanged. Production should slice using the preserved UTF-8 end offset and translate compiler line positions back to original source. The prototype strips the delimiter block; this is not the finalized position mapping. YAML interpretation is not necessary for HTML. No local YAML package was found in the inspected package tree; optional metadata integration should be separate and verified if introduced.

Default CommonMark covers headings, paragraphs, nested lists, links/images, fenced and inline code. [MDX extension documentation](https://mdxjs.com/docs/extending-mdx/) identifies `remark-gfm` for tables, literal autolinks, strikethrough, task lists and footnotes. `rehype-slug` adds heading IDs; require deterministic duplicate IDs and a prefix policy to avoid DOM clobbering in consuming pages. Explicit JSX HTML tags work; MDX is not an unrestricted raw-HTML Markdown parser (HTML comments and JSX-invalid attributes/syntax can fail). Do not enable `rehype-raw` blindly. Syntax highlighting is an optional pinned rehype/code adapter; smart punctuation optional `remark-smartypants`, not default. Images emit markup; imported assets need the resolver/asset pipeline. Start with CommonMark + GFM + heading IDs, adding features only with real fixtures.

## Execution policy and diagnostics

Compilation/rendering can execute expressions, ESM exports/imports and adapters. MDX authors can run filesystem/network/process code with helper privileges. A subprocess and React escaping do not sandbox it. Recommend explicit project opt-in to `trusted` rendering; initial default rejects executable rendering until policy is selected. Full trusted mode is appropriate for version-controlled authored Capgo content after review. A future restricted mode must enforce an AST allowlist before execution, including exports, computed props, spreads and import paths; rejecting braces alone is inadequate. Sanitizing HTML does not prevent build-time execution. Remote/untrusted MDX must not run in the trusted helper.

Produce diagnostics `{stage,code,message,path,line,column,component?}` plus compiler cause. VFile compiler errors offer locations; component/runtime errors often require source-map/AST instrumentation and cannot always honestly supply a location. Frontmatter removal requires offset correction. Batch failures should retain request identity and fail affected targets, never cache partial success as valid output. Prototype catches errors with coarse stage/message and optional compiler positions; full mapping remains planned.

## Dependency ownership and caching

Nift owns incremental invalidation; helper owns resolution/compilation. Before output is accepted, Nift must register root/transitive MD/MDX and every resolved local JS adapter/import closure, renderer config, plugin source/config, asset read by adapters, lockfile and helper/runtime version marker. Bare dependencies should be covered by lock/install identity; arbitrary undeclared FS reads cannot be tracked reliably, so require explicit dependencies or restrict adapters. Do not equate import discovery with all possible I/O.

Keep existing `input` discovery unchanged. The rendering path may register additional dependencies and return helper discoveries to a private Nift wrapper for `@dep` registration/confinement. For `.md` imports decide whether pure Markdown or MDX syntax applies; do not silently promise recursive discovery from today's `.md` registration-only contract. Re-exports/dynamic imports need explicit support or rejection. Prototype validates MDX dependency membership but has not implemented adapter/plugin invalidation.

Start without cache. Nift no-change builds already skip clean targets. Later helper-owned content-addressed cache should key source, all transitives, config/adapters/assets, compiler/plugins/runtime/helper versions and rendering policy; include relevant declared environment/data inputs or disable caching for nondeterministic adapters. Register dependencies even on cache hits. Cache output must not conceal missing files or failed confinement. Generate manifest deterministically and commit writes atomically; invalidation must not depend merely on mtimes. Prototype generated imported modules are a compilation artifact, not a validated persistent HTML cache. Cache-hit/daemon benchmarks are therefore not claimed.

## Limits and Capgo corpus

Current limits protect allocation/scanner/recursive interpreter work: 4,096 bytes/file, 1,024 logical lines, 16,384 bytes/physical line (currently shadowed), 1,024 syntax objects including attrs, 256 imports, expression depth64, JSX depth48, delimiter run256B, 64 recursively opened MDX files including root, graph depth16, aggregate MDX16,384B, path4,096B/specifier4,000B. `.md` is not read/count-limited in the MDX traversal. Whole-file open means byte checks do not prevent an oversized read allocation.

At Capgo commit `7d5b69d6ba8a6630384dffc7d012431ee3ed22ec`, canonical `apps/docs/src/content` has 519 docs MDX files; 242 (46.6%) exceed4KB. Median3,782B, p95 16,576B, p99 27,257B, max43,342B. Seven blog MDX files were previously identified separately; this table concerns docs only, not duplicate legacy content directories. Corpus measurements are saved in `capgo-corpus.json`.

Candidate trusted-build profile for evaluation: 256KiB/file, 8,192 lines,64KiB/line,16,384 objects,256 imports, existing nesting/delimiter/path bounds,256MDX files, depth32 and8MiB aggregate. These are **provisional test targets**, not measured-safe defaults. Keep current bounded profile available; profile/scanner optimization and large-file pathological tests must precede approval. All canonical docs fit candidate byte bound, but syntax/graph admissibility is not yet certified. No production or prototype parser limits were raised. The current interpreter's nontrivial 1.6KB parsing cost makes blindly lifting limits risky.

## Performance method and findings

See `prototype/benchmark-results.json` and reproducible driver. Linux, Node22.22.1, Nift4.6.0, serial calls, three single-case repetitions; synthetic fixed fixtures of26B,1,661B and2,444B. Each batch recompiles100/1000 requests; repeated fixtures improve V8 warming and do not represent all content diversity. Benchmark helper receives source-only document-shaped requests, so batch renderer times **exclude Nift parsing, transport from a live Nift build and graph discovery**. Single parser figures include Nift startup/package load and are not pure scanner CPU times. Peak RSS is Node `resourceUsage().maxRSS` KiB, not whole-system concurrent RSS. Source timings for imported modules would double-count nested compile time; published benchmark fixtures contain no imports.

The numeric table is generated after the benchmark completes. Each100-per-file result is measured, not extrapolated.1000-per-file is omitted because it would repeat hundreds of seconds of startup without resolving another architectural question.1000 batched requests are measured. Baseline empty Node launch isolates engine startup; full helper cold load minus measured compile/evaluate/render gives an approximate module-load/transport overhead, not a perfectly isolated profile. No persistent daemon/cache-hit numbers are reported.

## Acceptance and remaining scope

`prototype/verify.py` validates actual Nift composition, transitive import HTML, frontmatter exclusion/preservation, no scripts, unknown/malformed errors, trusted expression execution and process denial. `build-verify.py` validates a real two-target rendered website, no-change skip, nested edit affecting HTML, unchanged unrelated output and exactly-once MDX dependency metadata. These are feasibility checks, not final regression coverage. Existing parser suite is run unmodified from the baseline Git archive. Cross-platform macOS/Windows and Bun tests remain outstanding. Package resources/optional install layout and Nift minimum-version docs require implementation design; no core enhancement is assumed.

### Measured timing table

| Fixture | Nift parse process median | Renderer process median | 100 processes | Batch100 | Batch1000 | Batch1000 peak RSS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| small (26B) | 0.035s | 0.326s | 45.98s | 0.42s | 1.06s | 121.3MiB |
| realistic (1661B) | 1.537s | 0.401s | 41.35s | 1.44s | 10.07s | 276.0MiB |
| components (2444B) | 1.909s | 0.770s | 47.77s | 2.94s | 20.32s | 269.9MiB |

Empty Node process median: 0.114s. Cold single-request stage medians:
- small: compile 19.46ms; evaluate 0.27ms; static render 6.25ms; inside-helper total 26.11ms; cold RSS range 87.7–95.5MiB.
- realistic: compile 48.58ms; evaluate 0.41ms; static render 11.11ms; inside-helper total 60.18ms; cold RSS range 94.4–96.0MiB.
- components: compile 133.29ms; evaluate 0.88ms; static render 33.68ms; inside-helper total 171.23ms; cold RSS range 93.7–95.7MiB.

Real prototype build: initial 0.599s; no-change 0.009s; nested edit 0.614s. Inspect saved stdout for actual rebuild counts. No cache or persistent helper was enabled.

### Additional real-content check

The largest canonical Capgo docs MDX file (43,342B) compiled successfully through MDX+GFM+slug in102.03ms, peak Node RSS97.9MiB. This is compile-only evidence: its imported adapters were not executed and Nift’s unchanged4KB parser rejects it. The component-heavy2,444B Nift parser process measured10,416KiB peak RSS via `/usr/bin/time`; other parser fixture peaks and raised-limit memory have not been measured. Raw observations are saved alongside the benchmark. Baseline suite:121 corpus cases,13 malformed cases,22 boundaries; full archive run118.991s, including real @dep incremental certification.
