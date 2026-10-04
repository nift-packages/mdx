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

## Static component mappings

Set `components` to a project-relative ES module in mdx-render.json. Prefer a
factory that receives a semantic element constructor; the Nift API remains
renderer-neutral:

```js
export function components({element}) {
  return {
    Aside: ({type = 'note', children}) =>
      element('aside', {'data-type': type}, children)
  }
}
```

The factory and adapters are synchronous. Evaluated props and rendered children
are provided at build time; unknown components and adapter errors fail clearly.
`element` handles ordinary HTML attribute/text escaping through the build-time
renderer. No arbitrary HTML-string insertion API is provided. Importing React
inside a project adapter is possible only with its own provisioned module scope;
it is not required by this mapping interface. Async adapters are rejected rather
than quietly emitting Suspense fallback output. Mapping files are declared render
inputs; their transitive closure is addressed by the dependency checkpoint.

## Local document imports

Relative MD/MDX imports must appear in mdx.input's registered dependency graph.
The helper refuses undeclared local imports, missing files, cycles, re-exports,
dynamic imports and arbitrary JS/package imports until explicitly supported.
Default/named/namespace MDX imports are compiled recursively in the same worker;
imported document defaults inherit the configured component mapping. `.md`
imports use Markdown semantics (JSX/expressions are text), with frontmatter
removed. Existing mdx.input registers `.md` without recursively parsing it;
rendering does not silently reinterpret that parser contract. All rendered local
files are reported back for per-target Nift dependency registration.

## Declared render dependencies

Static local ES-module imports/re-exports in adapters/plugins are parsed with
Acorn8.18.0 already present in the locked MDX tree. Dynamic import/require and
implicit bare-package adapter imports are rejected; node: builtins are allowed
under trusted policy. Keep modules local and explicit. Adapters performing
filesystem reads must list assets/config/data paths in `dependencies`; undeclared
I/O cannot be inferred from arbitrary trusted JavaScript and is outside the
reproducible-build contract. Network/environment inputs need explicit frozen
snapshots or uncached nondeterministic workflows. A worker is not a sandbox.

`imports` maps MDX import specifiers to project adapter modules; e.g.
`{"@astrojs/starlight/components":"components/starlight.mjs"}`. This is a
configured adapter boundary, not native Astro execution. `remarkPlugins` and
`rehypePlugins` accept `{path, options}` entries for explicitly local plugins.
Renderer output reports adapter closure, plugins, declared assets/config and
installed helper/lock files for Nift per-target registration. Config itself is
registered by the facade. Prepared artifacts are per-document and byte-stable;
no unchanged batch timing data is written into them.

For build-hosted use prefer the normal Git package installation. Local path
installation creates a symlink; Nift correctly refuses an out-of-project symlink
when templates import it. The tests use a Git-installed real package tree.
