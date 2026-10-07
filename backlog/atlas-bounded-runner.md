<a id="atlas-bounded-runner"></a>
## ATLAS-BOUNDED-RUNNER — Launch every agent process through one bounded runner [patch] — todo
- Outcome: one committed runner, callable from bash, pwsh and cmd, starts a command in its own process group or Job Object, kills the whole tree at a deadline, samples resident memory against a recorded ceiling, and tags each run with session, item, command and deadline. Orientation lists tagged runs and kills those past their limit.
- Evidence (2026-10-02): a Claude `until grep …; do sleep 10; done` waiter ran 31 h; two pre-push hooks built for 2 h; a Codex process-tree script ran 13.6 h at 12 GB; this session found its own waiters at 14-29 h. Shell `timeout` resolves differently in Git Bash and pwsh.
- Oracle: a test launches a tree (parent plus grandchild sleeping past the limit) from each shell; at the limit no process of the tree survives, the exit reports the limit and the stage, and a memory ceiling breach kills the tree. A listing finds a run past its limit by its tag.
- priority: correctness
- needs: none (builds on the process-tree owner in ryancinsight/atlas#396)
- scope: scripts/process_tree.py, scripts/windows_process.py, a new runner entry under scripts/, scripts/tests/
- Next step: land #396, then add the runner CLI over `process_tree` with the tag store under the shared target's `.atlas/`.
