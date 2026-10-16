# Contributing

## Reporting issues

- Bug: describe the symptom, the steps to reproduce, your environment and the command output.
- Feature: describe the use case and the behaviour you expect.

Never paste `access_token` or `refresh_token` values. Redact them before posting any output.

## Pull requests

1. Branch off `main`, one small change per pull request.
2. Keep the single-file layout. Do not add third-party dependencies, and keep using the standard library for HTTP.
3. Everything printed to the terminal or written to logs must be ASCII English. Comments may be Chinese.
4. Run `list` and `claim --dry-run` locally before opening the pull request, and describe how you verified the change in the description.

## Hard rules

- The script treats every credential source as read-only. No change may write back to one.
- Never commit a file that contains a token.
- Endpoint paths, timeouts and retry counts are volatile values, keep them in the constants block.

## Local checks

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe codebuddy_claim.py --data examples/sample-accounts.json list

.\.venv\Scripts\python.exe -m pip install pre-commit
.\.venv\Scripts\python.exe -m pre_commit run --all-files
```

Packaging metadata lives in `pyproject.toml`. Verify it still builds and installs before touching it:

```powershell
.\.venv\Scripts\python.exe -m pip install .
codebuddy-claim --data examples\sample-accounts.json list
```

Remove the `build/` directory and the `*.egg-info/` directory that the install leaves behind, both are git-ignored and easy to forget.
