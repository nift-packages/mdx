# MDX HTML rendering investigation

Read [FEASIBILITY.md](FEASIBILITY.md) for the recommendation, contracts, risks and measured timings; [GAMEPLAN.md](GAMEPLAN.md) is the implementation checklist. Production parser/core remain unchanged.

The isolated prototype copies the current parser and adds only an experimental `html` method. It is not the installed package API. It executes trusted MDX; do not use untrusted documents.

```sh
cd investigation/prototype
npm ci --ignore-scripts
/path/to/nift-4.6.0 demo.f
python3 verify.py
python3 build-verify.py
python3 benchmark.py
```

Set the `NIFT` environment variable to your tested binary path. Node22.22.1 was used. The benchmark performs300 actual cold helper launches and three1000-document batches; it may take several minutes. Compile-only Capgo verification accepts source paths as arguments to `capgo-compile.mjs`; it does not port or render the upstream components.

`demo.html` and saved JSON/log evidence are checked in. Generated modules, node_modules, temp benchmark requests and build directories are ignored. `mdx-prototype.f` is intentionally a copy so production parser results can be tested unchanged. Generated helper ESM files are prototype artifacts, not a production cache.

Baseline tests were run from a Git archive of55843fa because the original suite's final seven-file inventory includes .git and does not allow investigation artifacts. Do not remove .git to satisfy it.
