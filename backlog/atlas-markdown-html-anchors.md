<a id="atlas-markdown-html-anchors"></a>
## ATLAS-MARKDOWN-HTML-ANCHORS — Resolve HTML fragment IDs [patch] — todo
- outcome/oracle: Resolve local and cross-file HTML IDs; absent IDs and code-only IDs report exact missing fragments. Preserve heading, URL-decoding and file checks.
- evidence: RITK manual at bfebdf06a36353ee85dfc252a01fd53e44b500c7 resolves 222 local destinations; three literal HTML IDs exist but `heading_ids` reports them missing.
- scope: scripts/check_mdbook_links.py, scripts/tests/test_check_mdbook_links.py, docs/mdbook/link-detector-internals.md; priority: verification; needs: none; basis: 1bf5e7456114e89c4f53eee3d26bb11cb045e6df
- next: Extend the existing fragment resolver; keep valid manual links.
