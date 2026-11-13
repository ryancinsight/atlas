<a id="atlas-ci-ubuntu-2604-apt"></a>
## ATLAS-CI-UBUNTU-2604-APT — Apt-installing atlas workflow jobs run on a runner image that moved [patch] — todo
- Outcome: every atlas workflow job that runs `apt-get install` is pinned to a named image or shown green on `ubuntu-26.04` by a named run, so a package renamed in 26.04 cannot fail a release job unseen.
- Evidence (origin/main 12708acf3ae4892d4443627f0d6d5016ddeb29d7): `book-pages.yml` installs `libfontconfig1-dev` (lines 225-227, job at line 102); `crates-publish-pending.yml` (apt step lines 85-92) and `semver-gate.yml` (lines 221-224 and 366-369) install the caller's `apt-packages`. All run on `ubuntu-latest`, now 26.04; the wheel and k-Wave jobs already broke on it ([ATLAS-CI-UBUNTU-2604](../backlog.md#atlas-ci-ubuntu-2604)). Only CFDrs passes `apt-packages` (`libfontconfig1-dev`: `ci.yml`:38, `rust-release.yml`:48 and :79).
- Shown green so far: CFDrs run 43379776153 (2026-11-13, job 131734577702, `Plan version-change publish`) on image ubuntu-26.04 installed `libfontconfig1-dev` 2.17.1-3ubuntu1 and succeeded. Not yet shown: the `semver-gate.yml` apt steps and `book-pages.yml`.
- Oracle: for each of the three workflows' apt-using jobs, a pin to `ubuntu-24.04` in the file, or a run id whose image line reads `ubuntu-26.04` and whose apt step succeeded, listed in the closing PR.
- basis: 12708acf3ae4892d4443627f0d6d5016ddeb29d7; priority: verification; needs: none
- scope: `.github/workflows/book-pages.yml`, `.github/workflows/crates-publish-pending.yml`, `.github/workflows/semver-gate.yml`
- Next step: find a CFDrs semver run and a member book-pages run on ubuntu-26.04; pin whatever has no green run.
