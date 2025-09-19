# Coding Guidelines

These guidelines define how we write, format, test, and review code for the AutoEdit MVP. They aim to keep the codebase simple, consistent, and easy to maintain.

## Languages & Versions
- Python 3.11+ only
- Shell scripts: POSIX sh/bash if needed

## Project Structure
- Keep modules within the existing layout:
  - `autoedit/cli`: CLI entry points (Typer)
  - `autoedit/core`: core pipeline logic (ingest, scene-detect, selection)
  - `autoedit/backends`: interface + implementations (local, lightning/beam)
  - `autoedit/exporters`: timeline/export code (MLT, etc.)
  - `autoedit/schemas`: Pydantic models for artifacts
  - `services/*`: deployable FastAPI services (GPU offload)
  - `tests`: unit/integration tests

## Style & Formatting
- Use Black for formatting with a 100‑char line length
- Use Ruff for linting (errors, warnings, and simple cleanliness)
- Imports: prefer standard library → third‑party → local order; Ruff’s isort rules may be enabled later
- Strings: prefer double quotes for user‑facing text; single quotes acceptable if consistent in file
- Avoid wildcard imports; be explicit

## Typing & APIs
- Type hints are mandatory for public functions/classes
- Use `from __future__ import annotations` in new modules
- Pydantic models define artifact schemas; favor explicit fields and types
- Return structured data (models/dicts) to the CLI; let CLI handle presentation

## Error Handling & Logging
- CLI: raise `typer.BadParameter` / `typer.Exit(code)` for user errors, otherwise fail loudly
- Library code: raise meaningful exceptions; don’t `print()` from non‑CLI modules
- Logging
  - CLI: use `rich` for friendly output
  - Services: structured JSON logs (stdout), include request IDs when feasible
- Fallbacks: for optional heavy deps (e.g., `faster-whisper`, `scenedetect`), provide graceful fallbacks with clear hints

## Configuration & Secrets
- Prefer explicit parameters; allow overrides via YAML/env
- Never commit secrets; support `.env` for local only
- Keep config examples in `config.example.yaml`

## Tests
- Pytest for unit/integration tests
- Unit tests: core modules, exporters, adapters (mock external calls)
- Integration: short sample media (≤10s)
- Keep tests fast and deterministic; avoid network calls

## Commit Messages
- Follow Conventional Commits where possible:
  - `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `ci:`
  - Scope optional, e.g., `feat(cli): add export command`

## Review Checklist
- [ ] Types and docstrings present for public APIs
- [ ] No prints in library code; CLI-only user output
- [ ] Errors are actionable; fallbacks documented
- [ ] Formats with Black; lint passes with Ruff
- [ ] Tests added/updated and pass locally
- [ ] Artifacts and I/O paths align with `runs/<id>/...` layout

## Tooling
- Format: Black (line length 100)
- Lint: Ruff
- Type-check: mypy (optional early); ignore missing imports
- Git hooks: pre-commit

See `MVP-Global-Dev-Infrastructure-Plan.md` for architecture and pipeline details.
