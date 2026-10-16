# FAQ

## Which credentials does the script need?

Only two fields per account are mandatory: `access_token` and `domain`. Everything else is optional and only affects display or filtering. See the field table in the README.

## Can I use a tool other than Cockpit Tools?

Yes. The script only reads a JSON credentials file. Export the accounts from whatever tool you use and reshape them into the documented format. Cockpit Tools is one convenient source, not a requirement.

## Why does an account show INACTIVE?

There is no claimable campaign for it right now. Accounts on the international site, www.codebuddy.ai, have no matching domestic campaign and normally show INACTIVE. No action needed.

## Why does an account show CHECK-FAILED http=401?

The server revoked that account's token. The JWT expiry stored locally is only a claim made inside the token, the server decides. Log the account in again in your account manager, then rerun.

## Why does `list` report VALID for an account that then fails with 401?

`list` can only compare the local `expires_at` against the clock. A token can be perfectly unexpired and still be revoked server-side. The 401 is the authoritative signal.

## Can a claim be duplicated by running the command twice?

No. Before claiming, the script asks the server whether the reward was already taken. Already claimed accounts are skipped, so repeated runs are safe.

## Does the script work behind a proxy?

No, and that is deliberate. It builds its opener with an empty proxy handler to force a direct connection. If you swap in another HTTP client, disable proxies explicitly.

## Where is the claim history stored?

In `claim-history.jsonl` under the system user data directory: `%LOCALAPPDATA%\codebuddy-claim\` on Windows, the user home directory elsewhere. The file rotates to `.1` once it grows past 5 MiB.
