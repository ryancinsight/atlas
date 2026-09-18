<a id="ratchet-regression-set"></a>
## ATLAS-RATCHET-REGRESSION-SET-2026-09-08 - Seven ratchet regressions arrived with peers' merges [patch] - todo

Parent: [`#slop-burndown`](backlog.md#slop-burndown).

- **outcome:** the fleet ratchet returns to zero regressions, by fixing the
  debt rather than by raising the baseline.
- **surfaced by advancing twenty-three gitlinks** at `49db31fc9`. These counts
  were already on the members' default branches; the meta-repo simply could not
  see them while its pins were behind. That is the ratchet's blind spot,
  recorded earlier in this item, doing its damage in the other direction: debt
  lands invisibly and then arrives all at once.

  | Member / class | Was | Now |
  | --- | --- | --- |
  | aequitas / `manifest_implementation` | 0 | 2 |
  | apollo / `existence_only_assertions` | 0 | 1 |
  | apollo / `manifest_implementation` | 24 | 25 |
  | kwavers / `oversized_files` | 107 | 109 |
  | kwavers / `target_forks` | 0 | 1 |
  | ritk / `oversized_files` | 44 | 45 |
  | ritk / `type_suffixed_fns` | 69 | 76 |

- **`aequitas` and `apollo` going 0 → n matters most.** A class at zero is a
  floor someone reached; crossing back is worse than never having been clean,
  because the ratchet's guarantee is exactly that it does not happen.
- **the instrument behaved correctly and I misread it once.** `generate`
  refuses to raise, printing the refusal on stderr. Having redirected stderr, I
  saw it write nothing while `check` reported violations and concluded the two
  modes disagreed. They do not: one was declining to launder the other's
  findings. Worth recording because "the tool is broken" was the wrong
  conclusion from a real observation, and the check that settled it was running
  the same command without the redirect.
- **`kwavers/target_forks` is regrowth, not a new instance.** Three
  repo-local `target/` trees were deleted earlier today and one is back at
  7.5 GB with cargo processes live in it. The generator survives the cleanup,
  which `context_and_memory` (slop pattern library) says makes finding the
  generator the priority defect rather than repeating the sweep. Not deleted
  this time: a build is running in it.
