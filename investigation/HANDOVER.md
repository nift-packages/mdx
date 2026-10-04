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
