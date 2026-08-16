# Design

## Surface

`landing/` is a static persuasive landing page for S50Info. It can be opened locally without a build pipeline and uses only `index.html`, `styles.css`, and `script.js`.

## Direction

The visual world is a SAGE50 support-engineer control bay: dark Windows service-bench surfaces, phosphor command strips, amber operational warnings, schema-blue rails, and terminal panels that show the product mechanism immediately.

The page refuses generic SaaS cards and abstract productivity copy. It proves the product by showing a real command moving through SAGE50-aware context into export output.

## Palette

- Background: near-black green service-console tones.
- Primary action and safe state: phosphor green.
- Secondary data/context rails: schema blue.
- Warnings and maintenance/release notes: amber.
- Boundaries or non-goals: red.
- Text: high-contrast off-white with green-tinted secondary copy.

## Typography

- UI/display stack: Windows-oriented sans stack (`Bahnschrift`, `Aptos`, `Segoe UI`, system fallback) to stay native to the product environment without external dependencies.
- Code/data stack: `Cascadia Mono`, `Consolas`, `SFMono-Regular`, monospace.
- Large headings are compressed and high-impact; command and state text uses code typography only where it represents commands, data, or machine state.

## Components

- Sticky service header with compact product mark.
- Full-viewport hero with split copy and console mechanism.
- Terminal panels with topbars, command input, flow rail and output state.
- Signal strip for core facts: SQL safety, SAGE50 syntax, export formats and standalone distribution.
- Translation board showing technical input and SAGE50 context resolution.
- Command rows rather than equal generic feature cards.
- Runbook panel with copyable command.
- Boundary panels for explicit fit/non-fit statements.
- Quickstart block for local operational steps.

## Interaction

- Hero chips change `--sqlyear` and export format in the command demonstration.
- Runbook copy button copies a base command with a textarea fallback for non-secure local contexts.
- Navigation is anchor-based and keyboard-focusable.

## Accessibility

- Semantic landmarks and section headings are used throughout.
- Focus states are visible and amber.
- Text and controls are high contrast on dark surfaces.
- Responsive breakpoints collapse the console, command rows and boundary panels into a single-column mobile layout.
- Motion is minimal and respects `prefers-reduced-motion`.

## Constraints

- No external build, package install, images, logos, customer claims, pricing, testimonials or unsupported feature claims.
- Export claims emphasize TXT, CSV, JSON, XML and XLSX because those are confirmed by PRD/docs.
- The landing positions Sage50BI only as the recommended visual reporting alternative because existing README/docs already state that boundary.
