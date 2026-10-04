# MDX HTML implementation gameplan

Status: investigation/prototype complete; production implementation authorized; checkpoints in progress. Preferred public API: `mdx.html(mdx.input("content/page.mdx"))`. Work in small checkpoints; every checkpoint ends with relevant tests, saved acceptance evidence, a small commit, and updated HANDOVER/status notes. Do not mark a checkpoint complete on implementation alone.

## Required architecture before Capgo integration

The normal production rendering path must be batched. The measured 41.35s versus
1.44s for 100 realistic renderer fixtures makes batching a requirement, not an
optional late optimization. Establish batch protocol/orchestration early (CP03),
and certify it in CP15/CP21; retain convenient mdx.html(mdx.input(...)) semantics
without losing per-target transitive dependency registration. Scalar one-off
support must not make process-per-page spawning the normal site-build path.

Preserve lightweight pure mdx.parse/input, ordinary HTML with no browser React/JSX,
and a renderer-neutral public MDX document → HTML abstraction. React static
rendering is a replaceable build-time implementation detail. Measured trusted-build
limits/parser performance, adapters, explicit execution policy, diagnostics,
adapter dependency invalidation and cross-platform certification remain release
gates. Do not modify Nift core. This stays the next dedicated package task;
The user authorized package implementation in the subsequent handoff; neither
Capgo website is authorized in this task.

- [x] **1. Freeze the baseline.** Archive/tag the current result/API corpus and successful Nift4.6.0 regression evidence. Correct the test inventory to exclude Git metadata and admit intentional investigation/helper files; retain all parser assertions. Acceptance: clean-checkout suite passes and exact parse/input compatibility snapshots are preserved.
- [x] **2. Specify optional renderer installation.** Define supported Nift/Node versions, helper location/package resources, pinned lockfile, licenses/notices and explicit offline install steps. No installation during rendering. Acceptance: fresh install, offline second install/use, missing runtime and parse-only/no-process use all tested.
- [x] **3. Fix the renderer protocol.** JSON request IDs/version, bounded source/output, file/stdin transport, structured errors, exit status, stderr, timeout and temp lifecycle. No shell interpolation. Acceptance: spaces/Unicode/quotes/newlines, malformed JSON, missing helper, timeout and process failure fixtures.
- [x] **4. Promote basic compilation/static rendering.** Pin compile+run and React static markup; no client React assets. Acceptance: headings, paragraphs, links, nested lists, images, fences and inline code with escaping snapshots; output script/runtime scan.
- [ ] **5. Expose additive scalar facade.** `html(document, options?)` succeeds with a string, refuses parser errors and fails builds on render error. Keep parse/input result shapes and pure behavior identical. Acceptance: parsed and input documents plus composed expression work from installed package; no redundant input_html API.
- [ ] **6. Define execution policy before broad imports.** Explicit trusted opt-in, documented helper privileges and unsupported untrusted use. Defer restricted mode until an AST policy exists. Acceptance: process denial, missing policy, executable expression/export/prop/import cases and trusted success; no misleading sandbox claims.
- [ ] **7. Separate frontmatter/body accurately.** Use preserved UTF-8 positions, retain raw frontmatter and correct compiler source lines. No mandatory YAML parser. Acceptance: LF/CRLF, Unicode, empty/absent/unclosed blocks and positioned body errors.
- [ ] **8. Specify components/config.** Project JS adapters, evaluated props, children, synchronous static-only contracts, unknown-component failure and HTML escaping. Acceptance: Aside, nested JSX, fragments, boolean/string/expression props under policy, named/unknown components, throwing/async adapters.
- [ ] **9. Resolve local document modules.** MDX default/named imports, transitive imports, repeated shared modules, cycles, missing paths and `.md` semantics. Preserve existing @dep ownership/confinement. Acceptance: direct/transitive MDX, MD, graph failures and helper/Nift resolution agreement including symlinks.
- [ ] **10. Collect new dependency classes.** Local JS adapter closure, re-export policy, config/plugins/helper/lockfiles/assets; dynamic I/O must be declared or prohibited. Return manifest for Nift @dep registration before accepting output. Acceptance: edits to each dependency invalidate only consuming targets; undeclared/dynamic import policy tested.
- [ ] **11. Establish the small default Markdown pipeline.** CommonMark + GFM + heading IDs/prefix; optional highlighting/smart punctuation. Acceptance: tables, literal autolinks, strike/task lists/footnotes, duplicate headings, JSX HTML syntax failures, nested lists and code language hooks.
- [ ] **12. Profile the current scanner.** Measure byte scanning/substr/stringification overhead on1–64KB plain/JSX/adversarial fixtures; optimize package code if necessary without changing nodes/positions. Acceptance: golden parity, established latency/memory bounds and documented before/after data. No Nift core edits.
- [ ] **13. Approve configurable limit profiles.** Evaluate provisional256KiB/file and8MiB graph targets, line/object/depth safeguards and pre-read limitations. Keep existing bounded mode and document defaults/compatibility. Acceptance: exact/over every limit, pathological inputs, memory ceilings and actual Capgo corpus admissibility.
- [ ] **14. Complete source-aware diagnostics.** Stage/code/path/line/column/component where supported, frontmatter translation and source maps/runtime attribution. Acceptance: malformed compile, import, unknown component, adapter exception and process failure; no fabricated locations.
- [ ] **15. Implement batch orchestration.** One helper invocation handles many requests, independent error identities, deterministic outputs and bounded concurrency. Establish the required normal production batch integration: project orchestration versus additive html_many API; scalar calls alone cannot batch across targets. Acceptance:100/1000 diverse docs, mixed failures, parity with scalar output and measured whole-build time including parser.
- [ ] **16. Evaluate cache only after tracking is correct.** Content-addressed helper cache covering all source/transitive/config/version/policy/environment inputs; atomic writes and dependency registration on hits. Acceptance: cold/warm parity, each key input mutation, missing file, corrupt cache, concurrent access and cache-disable behavior. Skip implementation if Nift incrementality plus batching is sufficient.
- [ ] **17. Consider persistence only if scalar workloads justify it.** Compare daemon startup amortization to batch and full parsing cost, then explicitly decide to defer or implement. Acceptance if implemented: lifecycle/restarts/ownership/multiprocess builds/Windows/process-policy tests; otherwise document deferral evidence.
- [ ] **18. Expand and run regression certification.** Preserve existing generated/adversarial parser tests and add rendering/policy/limits/dependency cases from preceding checkpoints. Acceptance: complete clean-checkout suite, unrelated target stability, no-change rebuild, generated HTML correctness and security-policy enforcement.
- [ ] **19. Certify portability.** Linux/macOS/Windows supported Node versions, file URLs, CRLF/UTF-8, paths/spaces, subprocess quoting, cleanup and package install. Bun is optional and must earn separate support. Acceptance: CI matrix evidence; document exclusions rather than implying untested compatibility.
- [ ] **20. Publish documentation and examples.** Parsing vs rendering, API/options, install/offline requirements, no browser runtime, mappings, execution policy, dependency declarations, profiles, errors and batch tradeoffs. Acceptance: copy/paste installed-package example tested by automation; no stale dependency-free rendering claims.
- [ ] **21. Certify a representative installed Nift site.** Direct composition, frontmatter, components, document/adapter/config/plugin/asset edits, unrelated target and no-change builds. Acceptance: @dep metadata exactly once; outputs/memory/full-build measurements; compare scalar and batch paths including parsing.
- [ ] **22. Gate Capgo implementation on real fixtures.** At pinned upstream commit, cover Starlight import rewriting, Steps/Cards/Tabs/Code/FileTree, PackageManagers, media/Mermaid/questionnaires, BlogMidArticleCta, asset/alias handling and largest pages. Acceptance: reviewed semantic/visual parity, all required MDX accepted or explicit exclusions, interactive vanilla-JS features, corpus-scale budget and provenance. Only then start capgo website work.

No production changes above are approved by this document alone. Each decision that changes parser defaults, executable-content policy or public API must be recorded before its implementation checkpoint.
