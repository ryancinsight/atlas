# ADR 0053: Kwavers–Hephaestus visualization collaboration boundary

- Status: Proposed coordination contract
- Date: 2026-08-21
- Class: `[major] [arch]`
- Supersedes: none
- Related: ADR 0051

## Decision

Atlas takes ownership of coordination, acceptance criteria, inventory, and
cross-repository evidence. Atlas does **not** take ownership of peer-owned
provider source checkouts or overwrite active provider branches.

Hephaestus owns all concrete GPU runtime implementation: device and adapter
selection, queues, buffers, bind groups, pipelines, shader dispatch, resource
transfers, and backend capability errors. Kwavers analysis and simulation
layers may define and consume provider-neutral visualization roles, but may not
construct or store concrete WGPU resources.

The work is collaborative rather than a takeover of peer source ownership:

| Area | Owner | Collaboration boundary |
|---|---|---|
| Registration-driven Python inventory/stubs | Atlas | Provider reviews generated artifacts and exact exports |
| `Simulation::run` GIL slice | Atlas/provider clean lane | Preserve solver behavior; no GPU ownership changes in this slice |
| Provider-neutral visualization role contract | Atlas + Hephaestus | Contract review before implementation |
| Concrete GPU implementation | Hephaestus | Must use the approved role contract |
| Kwavers callers and dependency graph | Kwavers provider owner | Update only in a clean, explicitly claimed lane |
| Hosted gates, pointer evidence, and PM synchronization | Atlas | No pointer advance without terminal evidence |

## Non-negotiable constraints

1. Do not edit the dirty detached Kwavers checkout in place.
2. Do not edit the active Hephaestus branch in place for Atlas coordination.
3. Do not add a reverse `kwavers-analysis -> kwavers-gpu` dependency while
   `kwavers-gpu -> kwavers-analysis` remains present.
4. Do not add a second concrete WGPU implementation or forwarding wrapper.
5. Do not claim GPU migration closure from static source edits alone.
6. Preserve peer-owned branches, worktrees, lockfiles, and unrelated PM files.

## Handoff contract

The next implementation lane must be created from fetched provider defaults and
must claim only the smallest caller/contract set. Before source changes, the
lane owner must attach:

- the exact base revisions for Kwavers and Hephaestus;
- a dependency graph proving the proposed direction is acyclic;
- the provider-neutral role signatures and unavailable-capability error;
- value-semantic transfer tests, including multi-field and distinct-input cases;
- the exact hosted gate list and pointer-update condition.

Atlas will review that evidence, update the root PM records, and coordinate the
provider merge and gitlink advance. A provider owner may reject or revise the
contract; rejection is collaboration feedback, not permission to edit around
the owner.
