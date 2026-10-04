# Capgo adapter plan — semantic certification before site work

Planning only. Implement no adapters, visual parity or websites in this investigation. Keep Capgo behavior in Capgo-owned modules and map upstream specifiers through the generic package's existing default/named/namespace import and component-factory capabilities. The public contract remains document → HTML; React is a replaceable build-time detail. Prefer semantic HTML with vanilla JS for simple interactions. Later framework islands remain available for complex stateful behavior.

| Component | Minimum semantic output and behavior | Dependencies and certification |
|---|---|---|
| Steps | Ordered list preserving nested Markdown and step content | Verify list semantics, nested children and numbering |
| Card | Heading, optional icon, body content | Preserve heading/text and accessible icon labels |
| CardGrid | Group of cards retaining authored order | Preserve children and responsive grouping; visual parity later |
| LinkCard | Real anchor with title, description and optional icon | Preserve target, external-link policy and accessible name |
| Tabs / TabItem | All panels as readable labeled sections, progressively enhanced to tabs | Vanilla JS buttons, unique IDs, ARIA, keyboard navigation, selected state; preserve every panel without JS. Use opaque factory children consistently, not a public React-specific contract |
| Code | Escaped pre/code with language, optional title | Verify code bytes and escaping; optional copy button with vanilla JS |
| FileTree | Nested semantic list retaining names and hierarchy | Optional disclosure controls with keyboard support; verify hierarchy |
| PackageManagers | Generated npm/pnpm/yarn/bun commands from `pkg`, `type`, `args`, `pkgManagers` | Reuse tab/code adapters; verify upstream command generation and allowed options |
| MermaidGraph | Accessible diagram plus source/fallback; preserve `graph`, `ariaLabel`, `fullWidth` | Pinned build-time SVG renderer or explicit browser Mermaid enhancement. Track renderer/config/source dependencies. Plain text alone is not diagram parity |
| YouTubeEmbed | Responsive titled iframe or useful linked fallback | Preserve video identifier and authored options; validate URL construction and accessible title |
| BuildCredentialsQuestionnaire | Authored questions, choices, branch results and useful links | Export explicit project rules/data; vanilla JS branch updates and keyboard/form semantics. Test every leaf and no-JS reading path |
| ConditionalQuestionnaire | Conditional question flow preserving rule and result semantics | Same rule-driven strategy; assess an island only if actual complexity warrants it. Do not substitute an empty placeholder |
| BlogMidArticleCta | CTA text, docs/pricing links, correct locale | Preserve default `docsPath`, overrides and translation/configuration data dependencies; test all used locales |
| PluginSetupSteps | Parameterized install/sync commands and steps | Preserve package/plugin options and command order; reuse Steps/Code |
| PluginsDirectory | Real plugin data, routes, filters and resulting list | Explicit config/data imports, dependency declarations, vanilla JS filtering with usable initial HTML |

Use the actual pinned source definitions and authored props as the behavioral authority. Frontmatter stays source-preserved; rendering transforms operate on the compiler AST. Capgo pages may follow existing Capgo styling, including light mode and blue. The dark/no-blue rule applies only to lab.nift.dev experiments. This plan does not require the eventual downloadable projects to be static-only: real API configuration and working behavior remain permitted.

Handle imported PNG/WebP assets through project-controlled copied URLs and declared file dependencies. Map `@/components/...`, Starlight, PackageManagers and configuration/data aliases explicitly. Do not execute arbitrary Astro source; port the small semantic behaviors into trusted adapter modules. Normalize authored HTML `style="..."` using a proper CSS-aware AST transform or native-element adapter, preserving custom properties and authored semantics. Do not rewrite preservation source or install Capgo-specific behavior in the generic package.

Suggested implementation order once the render-preparation design is agreed:

1. Inventory every imported specifier and used prop from the authoritative compiler AST. Establish explicit alias/asset/config maps and source provenance.
2. Add basic wrappers, Code/FileTree and Tabs; verify rendered text, headings, links, escaping and all tab panels.
3. Add PackageManagers, media/diagram, PluginSetupSteps and PluginsDirectory; verify commands, routes, assets and diagrams.
4. Add questionnaires and localized CTA; exhaustively exercise branch results and locale/default-path behavior.
5. Render all 519 canonical MDX plus 7 English blog MDX. Resolve secondary failures masked by the original first-error audit; do not equate isolated compilation with semantic rendering certification.
6. Certify changed root/imported document/adapter/config/plugin/asset, unrelated targets, no-change builds, symlink/escape/cycle/deletion behavior and stale-hook rejection. Measure clean and one-page MDX stage times on supported platforms.
7. Report semantic corpus coverage and remaining explicit exclusions. Only then proceed to approved site and visual work under the existing CP22 gate.

Generic package work, if approved separately: distinct render-only preparation, exact per-root dependency manifests and cache invalidation, compiler AST discovery reused during compilation, bounded transport and structured errors. The project owns its adapters, data, CSS, client enhancements and content-specific transforms.
