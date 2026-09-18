<a id="atlas-third-party-check-always-red"></a>
## ATLAS-THIRD-PARTY-CHECK-ALWAYS-RED-2026-09-09 — A check that fails on every pull request [patch] — blocked (decided 2026-09-10; awaiting the uninstall)

- **outcome:** the `recurseml/analysis` check either reports a real verdict on Rust workspaces of this size, or is removed, so the check list carries only checks whose colour is load-bearing.
- **Measured:** it fails ("Error occurred during analysis") on every recent merged PR across 9 of 10 sampled members; it's a third-party commit status, not a required check, so nothing is blocked mechanically — but every reviewer must manually confirm which red to ignore.
- **Decided 2026-09-10 (option 1 of 3 offered): uninstall** the `recurseml` GitHub App from the `ryancinsight` account.
- **Blocked — not executable by an agent session:** the session's token cannot enumerate or manage GitHub App installations (`gh api user/installations` → 403). Manual step required: Settings → Applications → Installed GitHub Apps → recurseml → Uninstall.
- **Re-open trigger / close when:** a PR opened after the uninstall shows no `recurseml/analysis` entry in `gh pr checks`.
