# Beam Cloud: Quick Start Extract

Reference upstream doc: https://docs.beam.cloud/v2/getting-started/introduction

## Core Concepts
- Beam lets you package Python or Node functions and run them on managed CPU/GPU workers.
- You describe a function with the `@beam.function` or `@endpoint` decorator; Beam handles provisioning, scaling, and scheduling.
- Deployments are immutable—push a new revision to update your endpoint.

## Install The CLI
```bash
pip install "beam-client[gpu]"
beam login
```
- `beam login` opens a browser to authenticate. Use `beam configure` in headless environments to paste a token.

## Author An Endpoint
```python
from beam import endpoint

@endpoint()
def handler(payload: dict):
    return {"echo": payload}
```
- Save this as `app.py`. Beam automatically detects dependencies via `requirements.txt` or the optional `Python` object in the decorator.

## Deploy
```bash
beam deploy app.py:handler --name autoedit-demo
```
- Beam builds a container, uploads assets, and exposes an HTTPS endpoint.
- `beam status autoedit-demo` shows build & runtime logs.

## Invoke
```bash
beam call autoedit-demo --json '{"message": "hello"}'
```
- Or use the generated HTTPS endpoint + API key directly from your app.

## GPUs & Custom Images
- Start with the default CPU image; add `gpu="A10G"` (or another SKU) when you need acceleration.
- Provide custom Dockerfiles or apt/pip packages by passing the `Python`/`Node` objects in the decorator (`pip_packages=[...]`, `apt_packages=[...]`).
- See `docs/beam/gpu acceleration.txt` for GPU-specific notes.

## Storage & Artifacts
- Temporary artifacts can be written to `/tmp`; use external object storage for large results.
- Beam offers managed storage via `beam.storage.bucket`, or integrate with S3/GCS using standard SDKs.

## Observability
- Logs stream to `beam logs <name>`.
- Metrics & traces are available in the Beam dashboard; configure alerts per endpoint.

## Lifecycle Tips For AutoEdit
1. Package STT/diarization services as Beam endpoints using the patterns above.
2. Store audio chunks in object storage and pass signed URLs as payloads.
3. Prefer small, stateless handlers; use `gpu_count` or job queues for heavy transcodes.
4. Keep the `lightning` backend flag in AutoEdit until imports are renamed to `beam`.
5. Export multiple `BEAM_API_TOKEN_*` variables (see `docs/beam/accounts.md`) to enable round-robin token usage.

## Useful Commands
- `beam init` – scaffold a new project interactively.
- `beam deploy app.py:function --watch` – live-reload code during development.
- `beam delete autoedit-demo` – remove an endpoint when finished.

Always double-check the upstream documentation for the latest features and limitations.
