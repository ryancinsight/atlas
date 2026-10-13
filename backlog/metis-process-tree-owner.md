<a id="metis-process-tree-owner"></a>
## METIS-PROCESS-TREE-OWNER — Run metis mutation jobs through the stack's process-tree owner [patch] — todo
- Outcome: `repos/metis/scripts/mutation.py` launches through atlas `scripts/process_tree.py`, and metis's copy (`scripts/process_tree.py`) is deleted.
- priority: tightening; dependency: [Atlas PR 396](https://github.com/ryancinsight/atlas/pull/396) is merged. Evidence: Metis still carries its own process-tree module; Atlas `scripts/process_tree.py` is the owner. Two copies fork tree-kill behavior when either changes.
- Oracle: metis mutation runs kill the whole tree at their deadline (the #396 tree test, run through metis's entry point), and `git -C repos/metis ls-files scripts/process_tree.py` is empty.
- Next step: resolve the owner from the stack root the way member hooks resolve the owned gate; update `repos/metis/scripts/mutation.py` and remove the duplicate module after the real tree-deadline oracle passes.
