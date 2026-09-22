<a id="atlas-privacy-naming-1"></a>
## ATLAS-PRIVACY-NAMING-1 — Remove confidential consumer identity from stack artifacts [patch] — in-progress
outcome: tracked identity appears only in .gitignore; other Atlas and RITK references use generic wording. History and the private checkout remain untouched.
scope: Atlas meta-repository artifacts and RITK; Kwavers is handled by PR #828.
acceptance: tracked-file case-insensitive search finds identity only in .gitignore; verify root scripts and affected member searches.
integrator: root; regions: meta-root backlog/docs/scripts/tests and RITK registration example, ADR 0023, backlog.
