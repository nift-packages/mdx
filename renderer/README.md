# Optional build-time MDX renderer runtime

Nift parsing/input remains dependency-free and usable with `--no-process`.
Rendering requires a supported Node runtime (development verified with22.22.1)
and exactly the versions in package-lock.json. Nift4.6.0 is the tested minimum;
4.5.0 rejects the existing parser's UTF-8 encode method. Rendering is not yet
released/certified across platforms.

After `nift add mdx`, provision the optional renderer explicitly:

```sh
npm ci --ignore-scripts --prefix .nift/packages/mdx/renderer
node .nift/packages/mdx/renderer/dependencies.mjs --check
```

Installation is separate from rendering. No render operation runs npm or fetches
packages. For offline provision use `npm ci --offline --ignore-scripts` with an
already populated npm cache, or preserve the provisioned tree. The frozen lock
pins transitives/integrities. Direct dependencies are MIT; dependency packages
retain their own license notices in node_modules. Do not strip those on redistribution.

To use an explicitly provisioned global tree instead:

```sh
export MDX_NODE_MODULES="$(npm root -g)"
node .nift/packages/mdx/renderer/dependencies.mjs --check
```

`MDX_NODE_MODULES` is the containing node_modules directory, not a package path.
The loader prefers an ordinary local install; falls back only to the configured
root, verifies exact direct versions, and fails on missing/mismatched dependencies.
Global installs alone do not imply that native ESM imports find them. No global
package-manager command or network discovery runs while loading/rendering.

React is build-time machinery behind the MDX document → HTML abstraction. No
React/JSX assets need to ship to the browser. Neither a local nor global install
is a sandbox for authored MDX: the eventual rendering policy must explicitly
select trusted execution.

## Execution policy

Rendering requires `.nift/mdx-render.json` containing `{"policy":"trusted"}`.
Without explicit opt-in, `html/prepare` and the helper refuse execution. Parsing
and dependency discovery never execute expressions. Trusted rendering can execute
MDX expressions, exports and later configured adapters with the helper's ordinary
OS privileges, including filesystem, network and subprocess access. This is for
reviewed authored project sources, not remote/user-submitted content. The worker
deadline bounds execution time but is not an OS sandbox; terminating it does not
roll back I/O or necessarily terminate subprocesses authored content created.
There is no advertised safe/untrusted rendering mode. A future restricted mode
requires an AST allowlist, not HTML sanitizing or merely removing expressions.

Ordinary static output requires no React/JSX/hydration in the browser. Local
framework islands remain a separate calling-application decision. Current
unsupported imports fail explicitly rather than inheriting Node's loader.
