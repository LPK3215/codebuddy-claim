# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-16

### Added

- Batch claim of DeepSeek compensation and welcome gift rewards across every account.
- Two credential sources: an exported JSON file via `--data`, or the encrypted local store of Cockpit Tools.
- `list` and `claim` subcommands, with `--dry-run` to report claimable rewards without claiming anything.
- `--account` filter and `--cockpit-root` override.
- Automatic refresh attempt through `refresh_token` when an access token is rejected.
- Claim history appended to `claim-history.jsonl` under the system user data directory.
- Credentials format sample with randomized values under `examples/`.
- MIT license, contribution guide, security policy, FAQ, issue and pull request templates.
- `README.md` in English with `README.zh-CN.md` as the Chinese companion, cross-linked at the top of both.
- Packaging metadata in `pyproject.toml`, exposing a `codebuddy-claim` console command.
- Pre-commit configuration covering text hygiene, syntax checks and private key detection.

### Fixed

- `--cockpit-root`, `--data` and `--account` are accepted both before and after the subcommand.
- Accounts without an `id` are no longer merged together. The deduplication key falls back to `uid`, then to the token itself.
- Numeric `id` and `uid` values no longer raise an error during filtering.
- `claim-history.jsonl` rotates to `.1` once it grows past 5 MiB instead of growing forever.
- Python 3.9 is declared as the minimum version, matching the `HTTPResponse.status` usage.
