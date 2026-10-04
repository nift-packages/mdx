# Investigation handover

Current state: optional trusted production renderer, batch orchestration, profiles,
dependency closure, cache and source-aware diagnostics are implemented. CP01–21
pass their recorded acceptance checks, with CP19 explicitly excluding Windows
Nift file input. CP22 real-corpus gate assessment remains blocked. Capgo remains blocked; no Nift core
or Capgo website changes. The public API is parse/input/with_profile/prepare/html.

## Historical feasibility handoff (before production authorization)

Completed: full package inspection; official compiler/renderer research; pinned Node helper; actual Nift input→html composition; transitive MDX; rendered two-target incremental site; baseline parser regression archive;100-process versus100/1000-batch measurements; corpus byte analysis; report and22-checkpoint implementation gameplan.

Recommendation: additive mdx.html facade with optional pinned build-time Node/MDX/React renderer, explicit trusted execution, preserved parse/input contracts, new dependencies registered with Nift, required normal production batched rendering before full-site certification. No browser React runtime. Parser profiling/limits are a release gate.

Not implemented/certified: production API, stable transport, config/adapter dependency closure, safe expression subset, cache/daemon, Starlight/Astro adapters, all Capgo content, raised limits, macOS/Windows or Bun. No Nift core or Capgo implementation edits.

Saved evidence: benchmark-results.json, build-results.json, demo-document.json/demo.html, capgo-compile-results.json, parser-memory-results.txt, baseline-regression.txt, capgo-corpus.json. Test sources remain available to reproduce. Recorded paths describe this workstation; install pinned npm dependencies before running elsewhere.

Planning clarification: capgo is the human+agent reference and capgo-agent the
normalized agent-first sibling. React remains a replaceable build-time renderer
detail; the public abstraction is MDX document → HTML. No implementation began.

## Production implementation progress

Authorized by the user’s subsequent handoff. CP01 complete: baseline tag and
unchanged parser contracts, corrected inventory check, full Linux Nift4.6 suite
passed. Checkpoint evidence is under investigation/checkpoints/. No Capgo work.

CP02 complete: optional local/offline and explicit global dependency loading,
exact direct pins, transitive lock, installation staging and license inventory.
No mandatory npm cost for parse/input consumers.

CP03 complete: bounded versioned file-based batch protocol with worker deadline,
project-confined paths, atomic responses and structured errors; seven tests pass.

CP04 complete: pinned compiler and build-time static renderer; Markdown/escaping
and mixed-batch failures verified, nine tests. Imports remain explicitly denied.

CP05 complete: installed prepare/html additive facade; file-backed HTML consumes
prepared per-document artifacts, never falls back to process-per-page. Intentional
inline one-off rendering supported. Full parser regression and ten renderer tests
pass. Node capability probe adds one cheap process per batch before temp writes.

CP06 complete: explicit trusted policy documented/tested; twelve tests. No
untrusted/sandbox claim; synchronous authored loop is stopped by worker deadline.

CP07 complete: frontmatter preserved, body compiled via verified UTF-8 boundary,
compiler locations map to original lines/byte columns; fifteen tests pass.

CP08 complete: project component factory with semantic element constructor,
synchronous props/children contracts, root dependency reporting; seventeen tests.

CP09 complete: registered relative MD/MDX imports, inherited child components,
named/namespace support and graph failures; twenty renderer/facade tests pass.

CP10 complete: static adapter/plugin closure, declared assets/config, helper/lock
dependencies and explicit MDX import mappings.24 tests plus actual site checks
prove incremental invalidation and unrelated/no-change behavior. Local package
links outside project cannot be used by build templates; use Git-installed copy.

CP11 complete: default CommonMark/GFM/prefixed IDs documented and verified,
including footnotes/duplicate headings/inert code and JSX HTML boundaries.

CP12 complete: native plain-span/line/backtick operations, cached byte length;
165 exact baseline parity cases and full parser suite pass.4KB prose3,003→14ms;
dense JSX2,929→2,165ms and backticks3,502→1,591ms. Dense syntax remains a gate.

CP13 complete: independent opt-in64 KiB/2 MiB trusted capacity profile; default
bounded behavior unchanged. Full regression and26 renderer tests pass. Actual
pinned Capgo scan accepts 518/519 canonical docs, cumulative parser
204.836s. Retained syntax-object exclusions and parser
cost remain CP22 release gates. No Capgo website implementation started.

CP14 complete: compiler/import original positions, mapped root/imported runtime
expressions and component/adapter attribution;28 renderer tests pass. Unmapped
process/adapter/generated locations remain null. No client source-map runtime.

CP15 complete:1,000-document independent failures/scalar parity pass; actual
installed100/500/1,000-target builds use one renderer helper each. Full cold
6.944/36.222/80.117s and warm3.648/18.769/44.821s. Pre-hook parsing dominates;
Capgo latency remains an unresolved release gate. Raw stage evidence committed.

CP16 complete: optional content cache off by default; full content/runtime/env
keys, atomic writes/checksums, hit dependency registration, invalidation and
concurrent-write tests.30 renderer tests pass.100-page third unchanged build
hits100 entries but remains3.981s; parser cost remains the release bottleneck.

CP17 complete: daemon explicitly deferred. One batch helper already amortizes
startup; the39s parser share of a44.8s warm1,000-page build would remain.

CP18 complete: fresh e2dab30 Git clone passes full original parser,165 exact
parity cases,30 renderer tests and profile boundaries. Linux evidence saved.
Core checkout remains clean; Capgo sites remain untouched.

CP20 complete: parsing/rendering/install/policy/profile/batching documentation and
copyable Git-installed basic example. Final local renderer suite34 tests passes
45.573s; original parser regression passes53.853s. Windows integration and Capgo
certification exclusions are explicit. Example automated build and no-change
rebuild validate ordinary HTML and exact dependency registration.

CP19 assessed with exclusions: CI37188684163 passes all Linux/macOS Node22/24
suites and all30 independent Windows helper tests on both majors. Windows pure
parse parity passes, but file input/integrated builds remain unsupported because
of the unchanged core directory predicate. Bun/UNC are not certified.

CP21 complete: isolated installed100/500/1000 full-build/memory evidence saved.
One helper per build;100-source scalar49.892s vs batch2.937s with identical HTML.
Parser remains the large-build bottleneck.

CP22 assessed, not certified: pinned536 real fixtures (519 docs MDX,10 MD,7
blog MDX), complete source hashes/import/component inventory and per-file failures
saved. Default helper renders377/519 docs MDX and all10 MD;142 docs MDX and7
blog MDX fail. Starlight/Astro/asset/interactive semantic/visual parity remains
unimplemented and unverified. Parser518/519 acceptance and204.836s corpus cost
remain release blockers; core stays untouched. Capgo and capgo-agent remain
planning-only. Do not treat the helper-only audit as production corpus acceptance.
