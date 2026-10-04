# Investigation handover

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
