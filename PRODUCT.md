# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

delegated: static HTML/CSS/JavaScript for the landing page so it can be opened locally without a build pipeline. The product itself is a Windows CLI built with Python 3.13, Typer, Rich and PyInstaller.

## Users

Primary users are technical SAGE50 operators: system administrators, developers/integrators, ERP consultants and advanced finance users who need quick database checks, exports or scripted maintenance without opening heavier tools.

Assumption inferred from PRD/README/docs: landing visitors are evaluating whether S50Info is the right technical utility for support, integration, automation or maintenance workflows around SAGE50.

## Product Purpose

S50Info is a free console utility for SAGE50 that centralizes common technical operations: show active connection information, run read-only SQL queries, export results, execute Python scripts with SAGE50 context and reset system logs.

Success means a technical user can verify, extract or automate SAGE50 data flows from one portable command-line tool.

## Positioning

S50Info is not a BI dashboard or end-user reporting product. Its differentiator is exposing SAGE50-aware SQL syntax and context through a portable CLI: shortcuts like `#clientes`, `[COMU]tabla`, `--sqlyear @`, `--groupby`, and injected script helpers let technical users work directly with SAGE50 data conventions.

## Operating Context

- Windows-only target.
- Distributed as a standalone PyInstaller executable that does not require Python on the end-user machine.
- Requires access to a SAGE50 installation, SQL Server credentials and the configured ODBC driver.
- Configuration lives in `config.ini`, with optional `.env` overrides.
- Typical automation contexts include PowerShell, `.bat` files and Windows Task Scheduler.
- Release/update workflow is supported by project tooling using ZIP artifacts, signed manifests, GitHub Releases and MkDocs documentation publishing.

## Capabilities and Constraints

- Commands: `info`, `sql`, `export`, `run`, `reset`.
- SQL execution is restricted to read queries (`SELECT`/`WITH`).
- SAGE50 SQL syntax supports management tables, comunes tables and fiscal-year selection.
- Export formats confirmed by PRD/docs: TXT, CSV, JSON, XML and XLSX. README also mentions HTML; because PRD/docs command reference does not list HTML, the landing should avoid making HTML a primary claim.
- TXT exports can use templates with `{CAMPO}` placeholders.
- Exports can be compressed with `--zip`.
- Scripts run with an initialized `proceso` object and helper functions such as `query_to_dict`, `samplebi` and `samples_disponibles`.
- Reset behavior targets SAGE50 log tables such as `log_analisis` and `log_error`.
- Not a replacement for SSMS, not an ETL, not a SQL Server admin suite, not a web app or REST API, and not multiplatform.

## Brand Commitments

- Product name: S50Info.
- Project/product id: `s50info` / `tool-sage50`.
- Existing positioning: free technical CLI for SAGE50; Sage50BI is recommended for end-user dashboards and visual reporting.
- Landing visitor copy should be neutral/professional Spanish because the source documentation and expected users are Spanish-speaking.

## Evidence on Hand

- `PRD.md`: product scope, target users, capabilities, architecture, non-goals and roadmap.
- `README.md`: public positioning, user fit, common commands and free-tool framing.
- `docs/index.md`: installation, command examples, SQL syntax, scripting API and FAQ.
- `c/product.json`: version `2.1.8`, manifest URL and GitHub/docs release configuration.
- `c/RELEASE/README.md`: signed release manifest and full/partial update workflow.
- No customer logos, pricing, testimonials or performance benchmarks beyond PRD targets should be fabricated.

## Product Principles

- Make technical SAGE50 operations faster than opening heavy tools for every check.
- Keep operations scriptable and automatable from the Windows command line.
- Preserve SAGE50 vocabulary instead of hiding it behind generic abstractions.
- Prefer safe read access and explicit maintenance actions over broad database administration.
- Be honest about the boundary between CLI utility and visual BI/reporting products.

## Accessibility & Inclusion

For the landing page, maintain semantic HTML, visible focus states, good contrast and responsive layouts so technical users can evaluate the product on desktop and mobile.
