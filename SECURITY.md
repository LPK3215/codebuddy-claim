# Security Policy

## Supported versions

Only the latest commit on `main` is supported. This is a single-file tool and fixes land on `main` directly.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting on this repository. If that is unavailable, open an issue that describes the problem without any sensitive detail.

Never include real `access_token` or `refresh_token` values, or a credential file, in a report. Redact them first.

## How credentials are handled

- Credential files and the Cockpit Tools store are opened read-only. The tool never writes back.
- Credentials are only sent to `https://<domain>/billing/meter/*`, the same origin the account page uses.
- Token values are never printed, logged, or written to the claim history. The history records account identifiers and per-item status only.
- Proxy settings are disabled on purpose, so traffic does not silently pass through an intermediary.
- The tool is meant for credentials you own, on your own machine.

## Out of scope

- The reward endpoints belong to the platform. A change on their side is not a vulnerability of this tool.
- Credentials leaked by copying a `data/` file into a repository or a public location are a user-side mistake. The shipped `.gitignore` excludes `data/` for that reason.
