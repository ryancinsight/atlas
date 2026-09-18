<a id="atlas-third-party-check-always-red"></a>
## ATLAS-THIRD-PARTY-CHECK-ALWAYS-RED-2026-09-09 — A check that fails on every pull request [patch] — blocked (decided 2026-09-10; awaiting the uninstall)

- **Integrator:** unclaimed; **lease:** none.
- **Measured 2026-09-09.** The most recently merged pull request in nine of ten
  sampled members — CFDrs #422, consus #71, helios #95, hephaestus #295, leto
  #179, kwavers #751, ares #2, asclepius #40, ritk #246 — carries a failing
  `recurseml/analysis`, every one reporting "Error occurred during analysis".
  The tenth (coeus #384) does not. It is a third-party app, not a committed
  gate, and it is not a required check, so nothing was blocked.
- **Why it is worth an item anyway.** Every pull request in the fleet displays a
  red X that means nothing, and the judgement each reviewer then has to make —
  human or agent — is "which red do I ignore". That is the habit the merge gate
  depends on not existing. Six pull requests were merged in this session over
  exactly this signal, each after opening the check list to confirm the
  committed gates were green; the confirmation is the cost.
- **Acceptance:** either the app reports a real verdict on Rust workspaces of
  this size, or its integration is removed from the members so the check list
  carries only checks whose colour is load-bearing.
- **Absorbed `ATLAS-RECURSEML-STATUS-ERROR-2026-09-03`,** which measured the
  same thing from the other end and is deleted below. What it established and
  this did not: the failure is a *commit status*, not a check run -- no
  output, no summary, no log, and a target URL pointing at the PR files page
  rather than at a run, so there is nothing to read and nothing to act on. It
  also predates any branch it appears on (aequitas `a65ade0c`, CFDrs
  `2561f8d0` and `39a0f45a`, all on their default branches), which is what
  rules out "a finding about this diff" without having to trust the message.
- **Still true 2026-09-10,** on every pull request opened today: mnemosyne
  #139 and #140, atlas #159 and #160. Each merged on the committed gates after
  opening the check list to confirm which red meant something.
- **The attempt, and why this is blocked rather than todo.** Removing or
  reconfiguring the app is an installation change, and the session's token
  cannot see installations at all:

      gh api user/installations
      403: You must authenticate with an access token authorized to a
      GitHub App in order to list installations

  That is an authorization failure on the attempt, not a judgement call, so
  it files as the request rather than as more analysis.
- **The request, one of three, in preference order.** (1) Uninstall the
  `recurseml` GitHub App from the `ryancinsight` account -- Settings ->
  Applications -> Installed GitHub Apps -> recurseml -> Uninstall; it gates
  nothing, so nothing is lost. (2) Keep it and restrict its repository access
  to a single member, so one repository carries the noise and the other
  twenty-seven do not. (3) Raise the analyzer error with the vendor and leave
  it installed meanwhile, accepting that every check list keeps a red X that
  means nothing. Recommendation is (1): a status that cannot pass trains
  reviewers to skim red, which is the one habit a merge gate cannot survive.
- **Re-open trigger:** the app is uninstalled or scoped, or the vendor's
  analyzer starts returning a verdict on a member workspace.
- **Decided 2026-09-10: option (1), uninstall.** The question was put with all
  three options and the 403 that made it a request rather than a judgement
  call; the answer was to uninstall the app from the account. Nothing in the
  repositories changes -- the check gates nothing, so there is no required
  status to unwire first, and no member workflow references it.
- **Not executable by an agent session.** Uninstalling is an account-level
  GitHub App operation and this session's token is not authorized to a GitHub
  App at all, so it cannot even enumerate installations. The step is
  Settings -> Applications -> Installed GitHub Apps -> recurseml -> Uninstall.
- **Close when** a pull request opened after the uninstall shows no
  `recurseml/analysis` entry in `gh pr checks`. Until then the item stays open
  so the next session does not re-litigate a settled decision.
- **Risk / change class:** [patch]; repository integration settings only.

