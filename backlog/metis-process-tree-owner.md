<a id="metis-process-tree-owner"></a>
## METIS-PROCESS-TREE-OWNER — Run metis mutation jobs through the stack's process-tree owner [patch] — blocked
- Outcome: `repos/metis/scripts/mutation.py` launches through atlas `scripts/process_tree.py`, and metis's copy (`scripts/process_tree.py`) is deleted.
- Evidence: metis carries its own process-tree module; ryancinsight/atlas#396 makes atlas `scripts/process_tree.py` the one owner. Two copies fork tree-kill behaviour the day either changes.
- Oracle: metis mutation runs kill the whole tree at their deadline (the #396 tree test, run through metis's entry point), and `git -C repos/metis ls-files scripts/process_tree.py` is empty.
- priority: tightening
- needs: ryancinsight/atlas#396 merged
- scope: repos/metis/scripts/mutation.py, repos/metis/scripts/process_tree.py
- Next step: after #396 lands, resolve the owner from the stack root the way member hooks resolve the owned gate.
