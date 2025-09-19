# Beam Account Configuration

We maintain three Beam Cloud accounts for GPU offload. Keep the issued API tokens private—store them locally via environment variables or your secret manager, never commit them to the repository.

| Alias        | GitHub handle | Recommended env var       | Purpose                         |
|--------------|---------------|----------------------------|---------------------------------|
| beam-ljniox  | @ljniox       | `BEAM_API_TOKEN_LJNIOX`    | Primary Beam workspace          |
| beam-sdbdkr  | @sdbdkr       | `BEAM_API_TOKEN_SDBDKR`    | Secondary capacity / failover   |
| beam-jniox   | @jniox        | `BEAM_API_TOKEN_JNIOX`     | Extra parallel GPU capacity     |

## Adding Tokens Locally

```bash
# Example (do not paste raw tokens into source control)
export BEAM_API_TOKEN_LJNIOX="<paste token here>"
export BEAM_API_TOKEN_SDBDKR="<paste token here>"
export BEAM_API_TOKEN_JNIOX="<paste token here>"
```

You can also supply a comma-separated list via `BEAM_API_KEYS` if you prefer a single variable, but the per-account variables above keep things explicit.

## How AutoEdit Uses These Tokens

- The CLI discovers all variables that start with `BEAM_API_TOKEN_` and rounds through them on each remote transcription call.
- If no prefixed tokens are set, it falls back to `LIGHTNING_API_KEY` for backward compatibility.
- Tokens are cycled in alphabetical order by environment variable name, enabling simple load distribution or round-robin usage.

## Parallel Workflows

- For parallel task execution, run multiple CLI processes—each request will automatically pick the next token in sequence.
- For shared runners (CI/CD), inject the appropriate tokens via your secret manager (e.g., GitHub Actions secrets) and export them before invoking the CLI.

Always rotate tokens through the Beam dashboard if one is compromised, and update the corresponding environment variable.
