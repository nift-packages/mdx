# Installed MDX example

Linux/macOS with the certified Nift commit/Node 22 or 24. Windows Nift file input
is currently excluded; see the package's portability evidence.

Copy this directory outside the package checkout, then run:

```sh
nift add mdx
npm ci --ignore-scripts --prefix .nift/packages/mdx/renderer
nift build --all
nift build
```

If using the exact globally installed packages instead of the npm installation:

```sh
export MDX_NODE_MODULES="$(npm root -g)"
```

The pre-build script prepares the entire document batch. The template retains
`mdx.html(mdx.input(...))` composition and registers prepared/component/child
inputs with Nift. The second build leaves the target up to date. No browser
framework runtime or generated script is required.

Only use the explicit trusted policy with reviewed authored MDX and adapters.
