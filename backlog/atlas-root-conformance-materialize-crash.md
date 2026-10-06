<a id="atlas-root-conformance-materialize-crash"></a>
## ATLAS-ROOT-CONFORMANCE-MATERIALIZE-CRASH — The checker crashes materializing the root repo on Windows [correctness] — todo

- priority: correctness
- outcome: a push from the atlas root runs the conformance checker to completion on every host.
- evidence: after #501 lets a root push match its own stack, the gate's checker invocation crashes on Windows: `materialize_member` -> `link_snapshot` calls `content.mkdir(parents=True)` on `<scratch>/atlas` and the path already exists, so `FileExistsError [WinError 183]` aborts the member scan and the ratchet compares against garbage and blocks the push with a phantom raise (the board push of 2026-10-06 was blocked this way; the same args on the CI host pass). Root cause candidate: the root repo materializes twice or its member-path collides with the baseline materialization.
- next: reproduce with `atlas-conformance.py check --repo report --member-path D:/atlas ...` on a Windows host, fix `link_snapshot` to tolerate an existing content dir (and find why it exists), then push the board closure the gate refused.
- acceptance: the root push's checker run completes with real counts on Windows and Linux, and the phantom-raise block is gone.
