# Repository Guidelines

## Project Structure & Module Organization
- `autoedit/`: core pipeline code. Key areas include `cli/` (Typer commands), `backends/` (local + Beam interfaces), `core/` (pipeline stages), `schemas/`, and `exporters/`.
- `services/`: deployable GPU microservices (FastAPI) for Beam Cloud offload.
- `docs/`: reference material, including Beam onboarding (`docs/beam/`).
- `tests/`: pytest suites mirroring module layout.
- `infra/`: CI/CD scaffolding and deployment notes.

## Build, Test, and Development Commands
- `python3 -m venv .venv && source .venv/bin/activate`: create/activate local virtualenv.
- `pip install -e .[full]`: install the AutoEdit package with optional dependencies.
- `pip install beam-client`: Beam CLI for remote deployments.
- `pytest`: run the full test suite.
- `ruff check .` / `black --check .`: lint and format checks (see Coding Style).
- `autoedit ingest ...`, `autoedit stt ...`, etc.: CLI entry points for end-to-end runs.

## Coding Style & Naming Conventions
- Python 3.11+, formatted with Black (100-char line length); lint with Ruff.
- Type hints required for public APIs; prefer descriptive function names (`transcribe_url`, `select_segments`).
- Directories and modules follow snake_case; classes use PascalCase; CLI options use kebab-case flags.

## Testing Guidelines
- Use pytest with tests placed under `tests/` mirroring source paths (e.g., `tests/core/test_ingest.py`).
- Prefer deterministic fixtures and avoid network calls; mock Beam HTTP clients where needed.
- Run `pytest` locally before opening a PR; add regression tests for new features or bug fixes.

## Commit & Pull Request Guidelines
- Follow Conventional Commits (`feat:`, `fix:`, `docs:`, etc.). Example: `feat(core): add diarization adapter`.
- Each PR should include a clear summary, linked issue (if available), validation evidence (tests/CLI run), and mention any configuration changes.
- Keep changes focused; open separate PRs for orthogonal updates (e.g., docs vs. core pipeline).

## Security & Configuration Tips
- Never commit secrets. Store Beam tokens as environment variables (`BEAM_API_TOKEN_*`).
- Use `.env` or secret managers for local development; rotate access keys regularly.
- Review `docs/beam/accounts.md` before configuring remote GPU access.
