<a id="ATLAS-HOOK-DIRECT-PATH-RETIRE"></a>
## ATLAS-HOOK-DIRECT-PATH-RETIRE — Retire direct hook build branches [patch] — todo
- Outcome: remove unreachable direct clippy, nextest, rustdoc, and reproduce branches from the owned pre-push hook and
  every registered copy through one provider rollout.
- Evidence: fetched default `027957bdd14179fdb74ad2355c490aba1aab928d` retains the fallback. Its introductions,
  `81458f71085883c3a8fe7dfb2aa6940f1bb57827`, `b1a3643d86dfe9bc86d230697443765cdb026fd6`, and
  `f0ade407b8863a7c8dde6880dad32fddfb0527e9`, predate the current identity work.
- Oracle: real mandatory-identity success and failure outcomes remain unchanged; a failed environment identity command
  cannot create a verified artifact; owned/copy blobs, modes, member pins, and fleet gates agree after rollout.
- priority: tightening
- needs: none
- basis: 027957bdd14179fdb74ad2355c490aba1aab928d
- scope: `scripts/git-hooks/pre-push`, all 28 registered `.githooks/pre-push` copies, and affected hook/identity tests
- Links: [meta index](../backlog.md#ATLAS-HOOK-DIRECT-PATH-RETIRE), [Atlas PR #500](https://github.com/ryancinsight/atlas/pull/500)
- Next step: remove the owner branches, prove mandatory identity behavior, publish exact copies, and land all selected pins.
