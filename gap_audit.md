# atlas — cross-repository integration gap audit

## Incremental releases toward the first stable stack

The 28 member plans below start from default-branch manifests reviewed on 2026-11-23. Each row follows one named package or application. The member checklist owns the other packages, acceptance tests and distribution channel. Versions are planning targets. When a gate closes through verification alone, carry the existing artifact forward. Select a new number only for a change that ships, after checking the registry and the package’s own compatibility baseline.

The 29 planning PRs are merged. The [critical feature gate](docs/parity/contracts.md#critical-features-required-for-10) requires a complete, reviewed inventory for each repository and passing product-path evidence for every entry. The initial inventories are empty and all 29 V1 exits remain open.

### What to start first

1. **Close the critical feature inventories.** The provider reconciliation is complete. Each member now needs an independently reviewed list of the features required by its supported workflows and passing end-to-end evidence for every entry. [Verified provider and consumer revisions](#provider-reconciliation-and-consumer-verification).
2. **Unblock the two coupled consumers.** Run an Ares structural partition through a complete Harmonia window and record transfer, rollback and work balance. Use that evidence to review Harmonia’s distribution decision and resolve the required registry dependencies of Ares Coupling and CFDrs 2D. Their independent solver tests can proceed now.
3. **Develop independent roots in parallel.** Start with the Eunomia subnormal power oracle, Iris zero-extent views, Melinoe disjoint partitions and Themis fallback topology. Use the existing [provider waves](#provider-development-waves) to select downstream consumers for each verified increment.
4. **Carry delivered work into the new baseline.** The Kwavers Physics/Solver 5.2.0 and Moirai Crypto 0.12.1 receipts are recorded below. Coeus has eight published CPU packages at 0.15.0. RITK has already passed the four-load Chromium replay, all nine browser scenarios and the three-plane native Safari comparison on ARM and Intel. Its next access milestone covers viewer export, reopen and the remaining nine maintenance findings. [RITK browser and dependency evidence](https://github.com/ryancinsight/ritk/blob/85280aa0b7ffb3b5376780ebf1cb2bae296fe83b/backlog/ritk-stable-qualification.md).

The Atlas board checker (`scripts/atlas-board-lint.py --file`, read on 2026-11-24 at the Atlas board of this revision and at each of the 28 `.gitmodules` members' fetched default ref) passes for 19 of 29 candidate boards. Apollo, Asclepius, Gaia, Harmonia, Hephaestus, Horae, Hyperion, Iris, Kwavers and Leto exit nonzero with schema findings. Each member audit records its count and the qualification work to clear it.

### Provider reconciliation and consumer verification

[All 29 planning PRs](https://github.com/ryancinsight/atlas/pull/781) merged. All 74 workflows triggered on those default-branch revisions completed successfully. The member PRs below migrated consumers before the three provider reconciliations merged. Each consumer’s merged Git revision resolved and compiled from a separate external Cargo project. Each project started without a lockfile or provider overrides, then passed `cargo check --locked --all-targets` on the resolved graph. After all three providers merged, six new external projects repeated this resolution and compilation. Each selected the same provider versions and crates.io sources. The local compiler cache was reused across these builds.

| Published provider | Reconciled default branch | Migrated consumers |
| --- | --- | --- |
| Hephaestus Core, WGPU, CUDA, Metal and ROCm 0.32.0 | [hephaestus #562](https://github.com/ryancinsight/hephaestus/pull/562) · [default-branch checks](https://github.com/ryancinsight/hephaestus/commit/fbc786279dd4d2abe48037cf80b45bb55409ffd4/checks) | [apollo #728](https://github.com/ryancinsight/apollo/pull/728) and [coeus #690](https://github.com/ryancinsight/Coeus/pull/690) |
| Horae Time 0.4.0 | [horae #140](https://github.com/ryancinsight/horae/pull/140) · [default-branch checks](https://github.com/ryancinsight/horae/commit/6dbe9a1cdb73001727d8b9c180841bc584a749fd/checks) | [harmonia #107](https://github.com/ryancinsight/harmonia/pull/107), [prometheus #101](https://github.com/ryancinsight/prometheus/pull/101) and Ares through Harmonia |
| Proteus Mat 0.3.0 | [proteus #122](https://github.com/ryancinsight/proteus/pull/122) · [default-branch checks](https://github.com/ryancinsight/proteus/commit/9bb6e2915d9e82461f1129d43a81dec241c1d2da/checks) | [ares #100](https://github.com/ryancinsight/ares/pull/100) and [hyperion #116](https://github.com/ryancinsight/hyperion/pull/116) |

The member suites below exercised the migrated contracts. Cargo nextest counts disabled or filtered tests in the skipped column. The Coeus suite requires a Metal device on Apple silicon. CUDA and ROCm cases can return after an availability check on this host. Two hosted WGPU jobs on the Coeus merge timed out during compiler-cache startup. Both passed on the same commit on [attempt 2](https://github.com/ryancinsight/Coeus/actions/runs/45282697078/attempts/2).

| Merged consumer | Selected contract | Passed | Skipped |
| --- | --- | ---: | ---: |
| [apollo `b5e8b70b583a`](https://github.com/ryancinsight/apollo/commit/b5e8b70b583a59ed824c8c4c2ee6af58aa50b8b6) | FFT with WGPU and CUDA | 682 | 15 |
| [coeus `3c8b71ae4f14`](https://github.com/ryancinsight/coeus/commit/3c8b71ae4f14bd94b25d62f6196f3049787b2224) | WGPU, CUDA, Metal and ROCm adapters | 182 | 0 |
| [harmonia `66f93f57d11c`](https://github.com/ryancinsight/harmonia/commit/66f93f57d11cfd7f3fbab1a117b824501f3b433f) | Interface partition and checkpoint replay | 91 | 0 |
| [prometheus `d190167170c3`](https://github.com/ryancinsight/prometheus/commit/d190167170c305957c266d4cbdf828eab55c685a) | Reaction kinetics with std | 47 | 0 |
| [ares `26b32a05efa3`](https://github.com/ryancinsight/ares/commit/26b32a05efa3a3591e981b03ff38a96ba645d030) | Coupling through Harmonia and material contracts | 120 | 0 |
| [hyperion `94a46b823dd7`](https://github.com/ryancinsight/hyperion/commit/94a46b823dd72b84b308cdcfdef5e2067a4536f4) | Diffusion and material reference values | 37 | 0 |

[hephaestus-metal 0.32.0](https://github.com/ryancinsight/hephaestus/releases/tag/crate-hephaestus-metal-v0.32.0) and [hephaestus-rocm 0.32.0](https://github.com/ryancinsight/hephaestus/releases/tag/crate-hephaestus-rocm-v0.32.0) each resolve the published Core 0.32.0. The provider audit records the archive checksums and embedded source revisions. Local and hosted checks covered native Metal and the Linux ROCm SDK with adapterless contracts. Native AMD device execution remains open for V1 until the CFDrs `rocm-laplacian` feature has a reviewed, hashed device run at the candidate revision. [Device evidence requirements](docs/parity/contracts.md#critical-features-required-for-10). Kwavers also passed four device-capacity cases and a requested-output simulation. Helios verified the helical timing and attenuation laws in both supported precisions.

### Atlas integration checkpoints

| Proposed stack target | Evidence required to advance |
| --- | --- |
| 0.1.0 [minor] | Close the four WP-001 inventories against their frozen references. Run WP-002 and reconcile the denominators, missing definitions and ownership gaps. |
| 0.2.0 [minor] | Complete WP-003/004 mapping and provider decisions. For each admitted provider, record a real consumer, resolved versions and the observed output. Track private distribution and device evidence per member. |
| 0.3.0 [minor] | Assemble the candidate on reviewed gitlinks in dependency order. On that graph, exercise the integrated scientific and viewer workloads, including rejection and recovery. Resolve each failed or unexecuted required lane. |
| 1.0.0-beta.1 → 1.0.0-rc.1 → 1.0.0 [major] | Freeze the supported contracts and channels at beta. At RC, replay the definition and release verdicts and independently install the declared artifacts. Promote the verified revision after all member and integration exits hold. |

These targets describe Atlas integration snapshots. Members keep their own versions and release authority under [proposed ADR 0072](docs/adr/0072-stack-stability-qualification.md).

### Member version checkpoints

| Member plan | Reviewed manifest and channel | First checkpoint | Following checkpoint before stable promotion |
| --- | --- | --- | --- |
| [aequitas](https://github.com/ryancinsight/aequitas/pull/174) | `aequitas 0.5.0` (indexed) | 0.5.1 | 0.6.0 if the fractional-dimension proposal lands |
| [apollo](https://github.com/ryancinsight/apollo/pull/727) | `apollo-fft 0.31.0` (indexed) | 0.32.0 | 0.33.0 → 0.34.0 → 0.35.0 |
| [ares](https://github.com/ryancinsight/ares/pull/99) | `ares-solid 0.3.0` (unindexed) | 0.3.0 source qualification | 0.4.0 proposed after scope review |
| [asclepius](https://github.com/ryancinsight/asclepius/pull/129) | `asclepius 0.5.0` (indexed) | 0.5.1 | 0.6.0 if the adapter boundary changes |
| [athena](https://github.com/ryancinsight/athena/pull/183) | `athena-krylov 0.5.0` (indexed) | 0.5.1 | 0.6.0 proposed for additive device support |
| [coeus](https://github.com/ryancinsight/Coeus/pull/689) | `coeus-core 0.15.0` (indexed) | 0.15.1 if CPU repairs are needed | 0.16.0 if reviewed additions are needed |
| [consus](https://github.com/ryancinsight/consus/pull/233) | `consus-hdf5 0.6.0` (indexed) | 0.6.1 | 0.7.0 if interop additions are needed |
| [eunomia](https://github.com/ryancinsight/eunomia/pull/222) | `eunomia 0.12.1` (indexed) | 0.12.2 | 0.13.0 |
| [gaia](https://github.com/ryancinsight/gaia/pull/241) | `gaia-mesh 0.8.0` (indexed) | 0.8.1 | 0.9.0 proposed for the scalar seam |
| [harmonia](https://github.com/ryancinsight/harmonia/pull/106) | `harmonia 0.1.4` (Git only) | 0.2.0 | 0.3.0 |
| [helios](https://github.com/ryancinsight/helios/pull/225) | `helios-domain 0.2.1` (indexed) | 0.2.2 | 0.3.0 proposed for additive capability |
| [hephaestus](https://github.com/ryancinsight/hephaestus/pull/561) | `hephaestus-core 0.32.0` (published and reconciled) | 0.32.1 if compatible fixes are needed | 0.33.0 proposed for reviewed backend additions |
| [hermes](https://github.com/ryancinsight/hermes/pull/310) | `hermes-simd 0.10.0` (indexed) | 0.10.1 if a dispatch repair is needed | 1.0.0-beta.1 |
| [horae](https://github.com/ryancinsight/horae/pull/139) | `horae-time 0.4.0` (published and reconciled) | 0.4.1 if compatible fixes are needed | 0.5.0 only for additive integration contracts |
| [hyperion](https://github.com/ryancinsight/hyperion/pull/115) | `hyperion 0.1.1` (Git only) | 0.1.2 | 0.2.0 |
| [iris](https://github.com/ryancinsight/iris/pull/100) | `iris-viz 0.1.4` (indexed) | 0.1.5 | 0.2.0 |
| [kwavers](https://github.com/ryancinsight/kwavers/pull/1145) | `kwavers-driver 0.5.0` (indexed) | 0.5.1 if Driver repairs are needed | 0.6.0 if Driver needs API changes |
| [leto](https://github.com/ryancinsight/leto/pull/437) | `leto 0.52.0` (indexed) | 0.52.1 | 0.53.0 proposed after sparse-storage review |
| [melinoe](https://github.com/ryancinsight/melinoe/pull/101) | `melinoe 0.10.0` (indexed) | 0.10.1 if a correctness repair is needed | 0.11.0 |
| [metis](https://github.com/ryancinsight/metis/pull/590) | `metis-ui 0.5.0` (indexed) | 0.5.1 | 0.6.0 proposed for additive host capabilities |
| [mnemosyne](https://github.com/ryancinsight/Mnemosyne/pull/278) | `mnemosyne-memory 0.10.2` (indexed) | 0.11.0 | 0.12.0 |
| [moirai](https://github.com/ryancinsight/Moirai/pull/724) | `moirai-runtime 0.12.0` (indexed) | 0.12.1 if Runtime requires a compatible fix | 0.13.0 |
| [prometheus](https://github.com/ryancinsight/prometheus/pull/100) | `prometheus-kinetics 0.1.0` (unindexed) | 0.1.1 if compatible oracle fixes land first | 0.2.0 |
| [proteus](https://github.com/ryancinsight/proteus/pull/121) | `proteus-mat 0.3.0` (published and reconciled) | 0.3.1 if compatible fixes are needed | 0.4.0 only for additive material contracts |
| [ritk](https://github.com/ryancinsight/ritk/pull/1121) | `ritk-snap 0.3.1` (private viewer) | 0.3.2 if viewer fixes precede access | 0.4.0 |
| [themis](https://github.com/ryancinsight/themis/pull/148) | `themis-topology 0.11.5` (indexed) | 0.12.0 | 0.13.0 |
| [tyche](https://github.com/ryancinsight/tyche/pull/140) | `tyche-core 0.5.0` (indexed) | 0.5.1 only for compatible repairs | 0.6.0 |
| [CFDrs](https://github.com/ryancinsight/CFDrs/pull/584) | `cfd-core 0.3.0` (unindexed) | 0.3.1 proposed for compatible solver repairs | 0.4.0 proposed for additive solver or binding work |

<a id="stable-stack-baseline"></a>
## Stable stack qualification — 2026-11-22

Atlas main `17b0124a7548ad81e817284afc5cb115c1d1bc78` registers 28 members. The table pairs each reviewed **default-branch** source with its Atlas pin. Counts are exact, unyanked crates.io name/version matches divided by Cargo workspace members with publication enabled. They measure registry presence. Archive identity, API compatibility and a working consumer require separate evidence. The manifest column names one package so independently versioned siblings retain their own baselines. In particular, Kwavers ships a 5.0.0 facade, 5.1.0 Physics and Solver, four 6.x crates and a 7.x GPU crate. Driver is at 0.5.0.

### Development order

1. **Restore the known failing default check.** Kwavers Security Audit reports RUSTSEC-2026-0592 and its aggregate CI gate fails at `cb2c7ecdb714`. Across the 29 sampled default heads, GitHub returned 338 successful, 405 skipped and two failed check runs. Branch protection and release approval were outside this inventory. [Failing job](https://github.com/ryancinsight/kwavers/actions/runs/45037646079/job/137255042083).
2. **Resolve the two private-provider edges.** Harmonia 0.1.4 disables publication. The required dependencies of ares-coupling and cfd-2d make their registry releases conditional on its graduation. Exercise transfer and rollback with a real consumer first, then review the provider's public distribution and verify both downstream package graphs. Hyperion also disables publication and has a Git-first scope.
3. **Close the definition gap while unblocked providers develop.** Of 38,096 candidate declarations, 2 are source-specified, 96 are partial and 37,998 are unmapped. All four public inventories are open. The evidence register has zero execution records. Complete WP-001/002, then WP-003/004. For each assigned family, establish an oracle, supported domain and actual target before growing coverage. Coeus's nine completed tensor milestone checks remain useful local evidence. [Program and dependency order](docs/parity/execution.md).
4. **Release by crate dependency, verify by member contract.** Both the pinned and default-source order checks place 207 publish-enabled packages in 43 layers, with zero unresolved required cycles. There are 184 exact index matches. The 23 missing versions belong to CFDrs (11), Coeus (7), Ares (3), Moirai WebView (1) and Prometheus (1). Determine the intended cohort and enabled features before opening publication work. Close the member's named milestones, repeat tests on released providers, then qualify the actual integration. Compatible existing upstream versions can already support development.
5. **Reconcile the selected sources.** The observed defaults differ from the pins for Coeus, Kwavers and RITK. Coordinate Coeus #686 and RITK #1104 with their owners. Advance only reviewed child revisions after their gates pass. On the resulting exact Atlas candidate, require both parity qualification verdicts and the application-level scientific and viewer workflows.

### Follow-up verification

- Kwavers fixed the [URL advisory](https://github.com/ryancinsight/kwavers/pull/1140). The published [Physics 5.2.0](https://crates.io/crates/kwavers-physics/5.2.0) and [Solver 5.2.0](https://crates.io/crates/kwavers-solver/5.2.0) archives match the index checksums and the same release source. The independent Solver consumer resolves the published Physics package and exercises the gas-transfer model. The [release record](https://github.com/ryancinsight/kwavers/pull/1143) retired the stale 5.1.0 publisher cohort. Its [main security and CI gates](https://github.com/ryancinsight/kwavers/actions/runs/45071645699) passed. The [release planner](https://github.com/ryancinsight/kwavers/actions/runs/45071646095) completed with no uploads.
- Moirai published [moirai-crypto 0.12.1](https://crates.io/crates/moirai-crypto/0.12.1) from [the verified main revision](https://github.com/ryancinsight/Moirai/actions/runs/45069322772). A fresh Rust 1.95 registry consumer passed the TLS handshake and both key formats across six signing schemes. [Metis #589](https://github.com/ryancinsight/metis/pull/589) removes the RSA waiver and updates both locks. [RITK #1107](https://github.com/ryancinsight/ritk/pull/1107) clears both RSA and URL advisories. RITK retains 13 unmaintained-version findings and a yanked async-executor. Six of eight [saved-study browser scenarios](https://github.com/ryancinsight/ritk/actions/runs/45070084596) passed. WebKit file reading and the hosted WebGPU adapter remain on the viewer checklist.
- [Harmonia #104](https://github.com/ryancinsight/harmonia/pull/104) records 91 passing tests. [Ares #97](https://github.com/ryancinsight/ares/pull/97) records six structural coupling tests, including the interface-work identity. A real consumer still needs to run a coupled window. Ares also reproduced five zero-dimension panics and verified the adjacent unit-segment load before proposing a constructor change.
- [Coeus #686](https://github.com/ryancinsight/Coeus/pull/686) merged after the baseline above. At `0f69d4a8`, eight physical-gradient tests passed, autograd built with default features disabled, and the release SemVer gate passed. The [release retry](https://github.com/ryancinsight/Coeus/actions/runs/45060488822/job/137331707512) completed all eight CPU packages. Each registry archive matches its checksum and the merge commit. A fresh Rust 1.95 consumer passed three base gradient tests with the feature off, then all three plus eight physical-unit tests with it on. [Coeus #687](https://github.com/ryancinsight/Coeus/pull/687) records the receipts. Seven workspace packages remain outside the released cohort.
- The [CFDrs](https://github.com/ryancinsight/CFDrs/pull/582) and [Coeus](https://github.com/ryancinsight/Coeus/pull/687) planning boards now pass the Atlas board schema check. CFDrs retains its P0/P1 urgency separately from the triage category. Thirteen of the fifteen boards flagged in the baseline still need reconciliation.

### Provider development waves

These are earliest integration waves for the required normal and build dependencies declared by the 28 Cargo workspaces. At each step, remove all members with no remaining required upstream member. Optional features, platform selection, private providers and the contract of the particular crate can change when a consumer is ready. Unrelated correctness repairs can start immediately.

| Wave | Members |
| ---: | --- |
| 1 | eunomia, iris, melinoe, themis |
| 2 | aequitas, hermes, mnemosyne |
| 3 | horae, leto, moirai, prometheus, proteus |
| 4 | hephaestus, hyperion |
| 5 | apollo, athena |
| 6 | coeus, consus, harmonia |
| 7 | ares, asclepius, gaia, metis, tyche |
| 8 | CFDrs, ritk |
| 9 | helios, kwavers |

### Member handoffs

The [Atlas planning PR](https://github.com/ryancinsight/atlas/pull/779) and all 28 member plans merged. Default-branch workflows passed on 28 planning merge commits. The remaining failure was the Kwavers release planner, corrected and verified above. Member links below open each checklist at its planning merge. The rows group related work for review. The crate-order tool determines publication precedence inside and across these groups. Follow the linked planning files for ordered tasks, value-based exits, scope ADRs and remaining approval gates.

| Member plan | Representative manifest | Default / Atlas pin | Indexed | Next deliverable |
| --- | --- | --- | ---: | --- |
| [eunomia](https://github.com/ryancinsight/eunomia/blob/31f90b4808c0847d48b3af8a96baf685cdeacdbe/checklist.md) ([#221](https://github.com/ryancinsight/eunomia/pull/221)) | `eunomia 0.12.1` | `cd2a7b388f0d` / `cd2a7b388f0d` | 2/2 | Close the subnormal integer-power proof across the shipped number formats. |
| [melinoe](https://github.com/ryancinsight/melinoe/blob/97a3e32fd9107dd8a347f4aa0a0859aae79621a7/checklist.md) ([#100](https://github.com/ryancinsight/melinoe/pull/100)) | `melinoe 0.10.0` | `e2d93b806a26` / `e2d93b806a26` | 1/1 | Qualify branded collections and disjoint parallel partitions. |
| [iris](https://github.com/ryancinsight/iris/blob/a902e959ed893baf899a96c5e973f1bfecc40df9/backlog.md) ([#99](https://github.com/ryancinsight/iris/pull/99)) | `iris-viz 0.1.4` | `a5812da9b70d` / `a5812da9b70d` | 1/1 | Qualify the field-view and color-map contracts used by renderers. |
| [themis](https://github.com/ryancinsight/themis/blob/8a38eb37152f608b46b627b225491b4d5c809103/backlog.md) ([#147](https://github.com/ryancinsight/themis/pull/147)) | `themis-topology 0.11.5` | `4ec2fb99b191` / `4ec2fb99b191` | 1/1 | Exercise the fallback topology path at the declared Rust floor. |
| [aequitas](https://github.com/ryancinsight/aequitas/blob/e28f4b0227811973b6d0d1723604da8ac563abb6/backlog.md) ([#173](https://github.com/ryancinsight/aequitas/pull/173)) | `aequitas 0.5.0` | `17c7c91e727e` / `17c7c91e727e` | 2/2 | Freeze the quantity and unit boundary on the published Eunomia line. |
| [mnemosyne](https://github.com/ryancinsight/Mnemosyne/blob/2326baa3ff1523b7015a77e011ef6c0fd1884986/checklist.md) ([#277](https://github.com/ryancinsight/Mnemosyne/pull/277)) | `mnemosyne-memory 0.10.2` | `b81d685a55bc` / `b81d685a55bc` | 11/11 | Resolve the allocator rescue queue against the current released source. |
| [hermes](https://github.com/ryancinsight/hermes/blob/3e382ba2524a0060f361de3fdb84b0eb46eb826c/checklist.md) ([#309](https://github.com/ryancinsight/hermes/pull/309)) | `hermes-simd 0.10.0` | `d95d1cbf894e` / `d95d1cbf894e` | 5/5 | Qualify runtime-dispatched scaled CSR accumulation. |
| [moirai](https://github.com/ryancinsight/Moirai/blob/11e299ac368973638df7f2479111611028313ed4/backlog.md) ([#720](https://github.com/ryancinsight/Moirai/pull/720)) | `moirai-runtime 0.12.0` | `11c5ffded3cd` / `11c5ffded3cd` | 18/19 | Finish the controlled transport evidence and reconcile the public WebView package. |
| [leto](https://github.com/ryancinsight/leto/blob/e929b7f8cb3eec824fa22a3b3e04f04a5d08cbe4/checklist.md) ([#436](https://github.com/ryancinsight/leto/pull/436)) | `leto 0.52.0` | `de7c3965e53b` / `de7c3965e53b` | 2/2 | Settle ownership of the duplicate sparse matrix representations. |
| [hephaestus](https://github.com/ryancinsight/hephaestus/blob/7c69a77ce6285805fb1698afdab3bc7671bd8f70/backlog.md) ([#560](https://github.com/ryancinsight/hephaestus/pull/560)) | `hephaestus-core 0.30.0` | `19b15aeeedc4` / `19b15aeeedc4` | 6/6 | Qualify the device seams that downstream solvers and tensors call. |
| [apollo](https://github.com/ryancinsight/apollo/blob/5226a46d73fdc9481ff4bc29b084f91873c405e3/checklist.md) ([#724](https://github.com/ryancinsight/apollo/pull/724)) | `apollo-fft 0.31.0` | `7b70b328f2bb` / `7b70b328f2bb` | 22/22 | Complete the dense FFT normalization and axis contract. |
| [athena](https://github.com/ryancinsight/athena/blob/0ad161c90b0747c4694f17b665ba9ea0e344e9d8/backlog.md) ([#182](https://github.com/ryancinsight/athena/pull/182)) | `athena-krylov 0.5.0` | `2be054244761` / `2be054244761` | 4/4 | Close the rectangular device-operator gap for LSQR. |
| [consus](https://github.com/ryancinsight/consus/blob/832899c5dbefaddb84cc2e8522c56fe0b110a445/checklist.md) ([#232](https://github.com/ryancinsight/consus/pull/232)) | `consus-hdf5 0.6.0` | `d1319313201c` / `d1319313201c` | 17/17 | Close the HDF5 handoff to Helios using the published reader. |
| [coeus](https://github.com/ryancinsight/Coeus/blob/69a2bfecf3acfb9101e570e2889d8f83b74dda41/backlog.md) ([#687](https://github.com/ryancinsight/Coeus/pull/687)) | `coeus-core 0.14.0` | `cc1961f51f12` / `4196389abc68` | 8/15 | Qualify the physical-autodiff cohort and settle the meaning of the local tensor milestone. |
| [horae](https://github.com/ryancinsight/horae/blob/935bea71a7996fa799750929efd94c43723e356d/checklist.md) ([#138](https://github.com/ryancinsight/horae/pull/138)) | `horae-time 0.2.2` | `40196ff641c4` / `40196ff641c4` | 1/1 | Close the time-integration order and rejection evidence. |
| [proteus](https://github.com/ryancinsight/proteus/blob/1ab9ef7492c74571a3bebeb61fc2d2ec6e499e94/backlog.md) ([#120](https://github.com/ryancinsight/proteus/pull/120)) | `proteus-mat 0.1.1` | `f571ea6adf1c` / `f571ea6adf1c` | 1/1 | Close the post-publication evidence for elastic validity and derived moduli. |
| [tyche](https://github.com/ryancinsight/tyche/blob/f490b7bb3bae0aa1fe81a349a5d4738aab90eb6a/checklist.md) ([#139](https://github.com/ryancinsight/tyche/pull/139)) | `tyche-core 0.5.0` | `47820cd1ef43` / `47820cd1ef43` | 1/1 | Close the durable study contract after the 0.5.0 Core release. |
| [harmonia](https://github.com/ryancinsight/harmonia/blob/3f3b0fd49273ac4ab5c2a4ad679dd7f2818e8659/backlog.md) ([#104](https://github.com/ryancinsight/harmonia/pull/104)) | `harmonia 0.1.4` | `3b16405022ba` / `3b16405022ba` | Git only | Prove a real coupling consumer and decide the registry route needed by two dependents. |
| [ares](https://github.com/ryancinsight/ares/blob/eacf5e9584b08e71a563412d31bc4a69eb5d6be3/backlog.md) ([#97](https://github.com/ryancinsight/ares/pull/97)) | `ares-solid 0.3.0` | `a75eae35688e` / `a75eae35688e` | 0/3 | Resolve the assembly boundary and obtain review of the proposed Phase 0 scope. |
| [asclepius](https://github.com/ryancinsight/asclepius/blob/49794f842d7990a72d1118f191cd826a74b168d5/checklist.md) ([#128](https://github.com/ryancinsight/asclepius/pull/128)) | `asclepius 0.5.0` | `b21df8fa4b77` / `b21df8fa4b77` | 2/2 | Qualify the law core and Coeus adapter at their public scalar boundary. |
| [hyperion](https://github.com/ryancinsight/hyperion/blob/e4dbb88fef35ab85eb71ccfdf7931465353c8cf0/backlog.md) ([#114](https://github.com/ryancinsight/hyperion/pull/114)) | `hyperion 0.1.1` | `19a8c90b19dd` / `19a8c90b19dd` | Git only | Derive per-quantity bounds for the diffusion-range tests. |
| [prometheus](https://github.com/ryancinsight/prometheus/blob/b98d17547cd33c78673993d37a682679817ba67a/backlog.md) ([#99](https://github.com/ryancinsight/prometheus/pull/99)) | `prometheus-kinetics 0.1.0` | `c1f85070ecf0` / `c1f85070ecf0` | 0/1 | Enforce rate-constant dimensions at the reaction boundary. |
| [gaia](https://github.com/ryancinsight/gaia/blob/ce7513c375ff4709e9863667635a4044d72ce4b1/CHECKLIST.md) ([#240](https://github.com/ryancinsight/gaia/pull/240)) | `gaia-mesh 0.8.0` | `19146d24ced6` / `19146d24ced6` | 1/1 | Reproduce the plane–segment midpoint error on the current geometry release. |
| [metis](https://github.com/ryancinsight/metis/blob/52ceb56843a71f61dca52e362fc7663bcfadbd59/backlog.md) ([#587](https://github.com/ryancinsight/metis/pull/587)) | `metis-ui 0.5.0` | `d7034d7d3dd5` / `d7034d7d3dd5` | 12/12 | Qualify the host lifecycle that RITK needs for its viewer. |
| [ritk](https://github.com/ryancinsight/ritk/blob/67e44819bfbce0b3a63d35f4147f969ae0ab7ac7/backlog.md) ([#1106](https://github.com/ryancinsight/ritk/pull/1106)) | `ritk-snap 0.2.0` | `533f2e07724d` / `762f0e92c1b5` | 32/32 | Qualify the DICOM export boundary in the real viewer. |
| [CFDrs](https://github.com/ryancinsight/CFDrs/blob/246d7fc16a7f4afe2a56bdef1ea5704edc260d33/backlog.md) ([#582](https://github.com/ryancinsight/CFDrs/pull/582)) | `cfd-core 0.3.0` | `40021147e365` / `40021147e365` | 0/11 | Close solver recovery and the unpublished coupling edge on separate tracks. |
| [helios](https://github.com/ryancinsight/helios/blob/6bf700eadd99fd49df1a61cf96f889d5182385ca/CHECKLIST.md) ([#223](https://github.com/ryancinsight/helios/pull/223)) | `helios-domain 0.2.0` | `b96d802f01b4` / `b96d802f01b4` | 12/12 | Verify archive admission through the released Consus reader. |
| [kwavers](https://github.com/ryancinsight/kwavers/blob/929c29793199665ab318469cf9ea2bbedc63fa16/backlog.md) ([#1141](https://github.com/ryancinsight/kwavers/pull/1141)) | `kwavers 5.0.0` | `cb2c7ecdb714` / `bee13af7268b` | 22/22 | Restore the release baseline and qualify the current simulation cohort. |

### Open verification work

- **Package gaps.** Check registry ownership and the intended first-release cohort for CFDrs's eleven 0.3.0 packages, Ares Solid/Operator/Coupling 0.3.0, and Prometheus Kinetics 0.1.0. Coeus's missing 0.14.0 versions are Dist, FFT, WGPU, Accelerator, CUDA, ROCm and Metal. Reconcile those with the existing 0.15.0 candidate before scheduling uploads. Moirai WebView 0.12.0 also lacks an exact index match.
- **Member board checks.** The whole-board lint, read on 2026-11-24 at each member's fetched default ref, passes for Atlas and 18 members. Status, priority or duplicate-ID findings remain in Apollo, Asclepius, Gaia, Harmonia, Hephaestus, Horae, Hyperion, Iris, Kwavers and Leto. During milestone reconciliation, verify delivered items against their source and retain every open dependency when compacting old entries.

### Reproduce the baseline

Use `git ls-tree HEAD repos/` and compare each entry with the member remote's default HEAD. At each reviewed member revision run `cargo +stable metadata --format-version 1 --locked --offline --no-deps`. Read the sparse index for each publish-enabled package and match its manifest version with `yanked = false`. This audit covers 246 workspace package entries. The publish-order tool also scans nonmember manifests and reports them separately.

Run `python3 scripts/publish-order.py --json --exact-gitlinks` for the pinned graph and omit `--exact-gitlinks` for the reviewed checkouts. Inspect both `required_unresolved` and `blocked_by_unpublishable`. Check hosted jobs at each reviewed commit with the GitHub Check Runs API. Run `python3 scripts/atlas-parity.py check`, then `qualify --gate definition` and `qualify --gate release`. At this review the structural check passes and both qualifications fail. No member Rust test suite, GPU benchmark, SemVer comparison or fresh consumer was executed by this planning audit. The [coordination checklist](backlog/atlas-stable-stack-001.md) tracks the outstanding work.

<a id="consus-050-adoption"></a>
## Consus 0.5.0 adoption

[Consus #227](https://github.com/ryancinsight/consus/pull/227) merged at
`2193675` and uses published Moirai runtime and async 0.12.0. All 17
Consus 0.5.0 registry archives match the crates.io checksums and identify
that commit. Raster uses the scoped `rust-release.yml` trusted publisher.
The hosted cohort published Core and Compression before the first ZIP
upload. NPY published after Cargo verified ZIP was indexed.
[Cohort workflow](https://github.com/ryancinsight/consus/actions/runs/44612778448)
and [NPY workflow](https://github.com/ryancinsight/consus/actions/runs/44613901901).

Post-merge Consus CI passes. A fresh registry consumer resolves all 17
packages and only published Moirai 0.12.0 providers. It reads exact Int32
values from standard GZIP and ZSTD Parquet, rejects the historical codec
fixtures, and reads an HDF5 signature and group through Moirai async.
Historical Parquet conversion requires provenance and retained original
bytes and hashes.

Atlas records the Consus release's documentation closeout at `bab9c35`
and the coordinated CFDrs, Gaia, Helios, Kwavers, Metis, RITK and Tyche
adoption heads. Their workspace locks and the Gaia and Metis fuzz locks
agree on the released Consus commit `2193675`.
The targeted locked tests pass 109 cases across HDF5, MINC, MAT v5, 3MF,
raster and archive persistence. Consus owns MAT v5 selection and decoding.
Kwavers retains the clinical transform.

The seven Consus adoption PRs landed in dependency order. The unyanked
Gaia Mesh 0.6.10 and RITK Codecs 0.8.0 archives match their registry
checksums and identify `e20ea48` and `cd22744`, respectively.
[Gaia publish](https://github.com/ryancinsight/gaia/actions/runs/44620322981)
and [RITK Codecs publish](https://github.com/ryancinsight/ritk/actions/runs/44622303109).

The RITK release planner found 22 approved versions waiting on registry
Coeus Autograd 0.12.0. The current Autograd dependency graph requires
Coeus CPU, which has no crates.io entry. Cargo packaging reproduces
that missing dependency after 107 Autograd tests pass with the Apollo
source candidate. Published Coeus Core and Ops 0.12.0 require Eunomia
0.9. Apollo #720 passes source CI. Its FFT 0.29.5 package verification
reproduced incompatible Eunomia 0.11 scratch types and Leto 0.47 views.
Mnemosyne #276 has since released Arena 0.7.2 and Memory 0.10.2 from
`b81d685a`. The registry tarballs match that revision and their index
checksums. Apollo Leto Interop 0.20.1 still exposes Leto 0.47 views.
Align the Interop and Hephaestus requirements before revalidating
Apollo FFT and Coeus Autograd.
[Mnemosyne #276](https://github.com/ryancinsight/mnemosyne/pull/276)
and [Apollo #720](https://github.com/ryancinsight/apollo/pull/720).

DICOM depends on the published RITK Spatial 0.4.0, which selects Leto
0.46.5. That Leto version excludes the Eunomia line
required by Aequitas 0.4.0, and registry packaging reaches a Rust trait
error. The current Spatial source packages with Leto 0.50.0. Its public
point, vector, and direction types expose Leto types, so the registry
repair requires a versioned API migration.
[RITK registry plan](https://github.com/ryancinsight/ritk/actions/runs/44620954860).

[Aequitas #166](https://github.com/ryancinsight/aequitas/pull/166) corrects
the SI catalog layout and preserves the 0.4.0 release evidence. The 0.4.0
release moved Eunomia to crates.io while 18 Atlas member locks still
select Aequitas 0.3.2 from Git. Horae reproduced a compile failure where
its Git Eunomia trait and Aequitas's registry Eunomia trait met at a
typed time boundary. A standalone candidate using the published Eunomia
passed 53 Horae tests. The Proteus candidate using the same provider
passed 77 tests. Leto's initial lock refresh reproduced the split
`UnitScalar` traits. A source preview with Eunomia 0.12.1 and the
aligned Hermes and Mnemosyne candidates passed all 458 Leto and Leto
Ops library tests. Release validation still requires real registry
resolution and locked checkouts.

Switching consumers to the published Eunomia 0.12.0 reproduced
incorrect complex folds and non-finite results for a finite maximum and
a bounded negative power. The Eunomia 0.12.1 maintenance release
preserves the published 0.12 API and passes 237 tests. Both crates.io
archives match their checksums and identify `b05dc06`. The standalone
registry consumer passes the corrected numeric cases and typed SI
round-trips on Rust 1.95. Aequitas #167 locks both packages and passes
190 Rust tests and the required hosted checks.
[Eunomia publish](https://github.com/ryancinsight/eunomia/actions/runs/44627714350)
and [Aequitas #167](https://github.com/ryancinsight/aequitas/pull/167).

The published Hermes 0.9.2 libraries cap Eunomia below 0.12. Hermes
re-exports these types and exposes them in backend implementations.
[Hermes #307](https://github.com/ryancinsight/hermes/pull/307) advances
the four libraries to 0.10.0. The archives match their registry
checksums and identify merge `a65c6c2`. A registry consumer uses one
`Bf16` type for both the Hermes sum and the Aequitas time conversion.
Horae, Proteus, Hyperion, and Mnemosyne also record the published
0.12.1 provider. [Hermes publisher](https://github.com/ryancinsight/hermes/actions/runs/44631113558).

[Leto #433](https://github.com/ryancinsight/leto/pull/433) merged at
`b65e6e0`. Both 0.51.0 archives match their crates.io checksums and
identify that commit. Leto Ops was published after Cargo resolved Leto
0.51.0. A fresh Rust 1.95 registry consumer evaluates the signed
Laplacian of `x² + 3y²` as exactly −8 at all 16 grid points in both
precisions and rejects zero physical spacing.
[Leto publisher](https://github.com/ryancinsight/leto/actions/runs/44634017171)
and [Leto Ops publisher](https://github.com/ryancinsight/leto/actions/runs/44634643054).
The initial Leto release probe also resolved Eunomia 0.11.0 through
the prior published Mnemosyne allocator. Leto, Leto Ops, Aequitas, and Hermes
share Eunomia 0.12.1 at the tested quantity and scalar interfaces.

Prometheus #96, Athena #177, Harmonia #101, Gaia #234 and #235,
Hephaestus #555, and Ares #93 integrate the scalar provider in Git.
Melinoe #98 aligns its standalone device contract. The Gaia library
and separate fuzz lock agree on Leto 0.51.0, Aequitas 0.4.0, Eunomia
0.12.1, and released Consus 0.5.0. All three fuzz targets compile under
Rust 1.97. Gaia 0.6.10 and Hephaestus 0.28.0 registry archives predate
these source integrations. The same plane constructor compiles and
returns offset −3 from the merged Gaia and Leto sources. The published
Gaia 0.6.10 constructor rejects the Leto 0.51 point and vector types
because its signature uses Leto 0.50.

Gaia #236 publishes Gaia Mesh 0.7.0 from `ee119e3`. A fresh crates.io
consumer constructs the plane through `(0,0,3)` with offset −3 and
exports a triangle in the three expected 3MF parts via Consus 0.5.
Hephaestus #556 publishes its six 0.29.0 libraries from `e499d489`.
A fresh Rust 1.95 consumer resolves all six and obtains −8 at all 16
grid points through both Hephaestus Host and Leto Ops. A short output
buffer returns an error. Each archive matches its registry checksum
and exact merge revision. The CUDA, ROCm, software WGPU, and native Metal
checks pass on the Hephaestus release revision.
[Gaia publisher](https://github.com/ryancinsight/gaia/actions/runs/44642096363)
and [Hephaestus publisher](https://github.com/ryancinsight/hephaestus/actions/runs/44644599072).

Athena #178 adopts both Hephaestus 0.29.0 dependencies at the release
revision. The locked migration passes 16 Core unit tests and 23
Hephaestus integration tests, including on-device residual, spectral,
and preconditioner cases. [Athena #178](https://github.com/ryancinsight/athena/pull/178).

Atlas #757 remains open for the remaining Aequitas consumer locks and
stack coherence checks. Apollo #720 is merged. Apollo #723 uses the
archived registry lockfiles to recover the release check that failed
while resolving the older NTT baseline. Apollo #723 merged as `7a8b226`.
All 20 Apollo archives match the registry checksums and source revision.
A fresh consumer verifies the Leto-backed impulse transform and the
documented frequency bins. Coeus #681 merged as
`7091030` and limits publication to eight CPU and tensor packages at
0.13.0. Core and CPU are indexed with matching archive checksums and
source revisions. A fresh Rust 1.95 consumer verifies the typed Leto view,
its final element, and the rejection of a short buffer. The Autograd
unit suite passes 107 tests. Coeus #683 adopted the archived-lock API
gate and published the remaining six packages from `998e244`. All
eight archives match the registry checksums and their source revisions.
A fresh registry-only Rust 1.95 consumer builds the eight packages and
computes the derivative of x² at x = 3 as exactly 6.

RITK #1061 published Spatial 0.5.0, Diffusion Scheme 0.4.0, and
DICOM 0.4.0 from `4c37314`. The archived checksums match crates.io,
and a fresh consumer verifies the typed point, the SI diffusion
weight, and PackBits decoding with truncated-input rejection. The locked source
suites pass 185 tests, with two opt-in cases ignored. The DICOM
archive resolves Aequitas 0.4.0, Eunomia 0.12.1, and Leto 0.51.0.
RITK #1065 publishes 11 more approved packages from `2804d35`. Their
archives match the crates.io checksums and source revision. A fresh Cargo
consumer resolves all 11 with one Aequitas 0.4.0, Eunomia 0.12.1, and
Leto 0.51.0. Its 2×2 image with values 0, 2, 0, 2 has minimum 0,
maximum 2, mean 1, and population standard deviation 1.
[RITK publisher](https://github.com/ryancinsight/ritk/actions/runs/44664017931).
The RITK #1066 release adds 16 verified archives from `49dc944e`.
Including Codecs 0.8.0 and the earlier releases, 31 versions are verified.
That includes 25 of the 26 authorized versions. IO 0.6.0 supersedes the
planned IO 0.5.0. The first Parcellation 0.2.0 upload clears the dependency
for Registration 0.56.0, which publishes on attempt two. A fresh registry
consumer resolves the native DICOM packages and passes five tests covering
exact big-endian samples, deflated character data, and invalid-transfer-syntax
rejection before overwrite. A second consumer resolves Registration and
Parcellation together. World coordinates (4, 4, 3) map to label 24, and
the bridge rejects a 23-label buffer for the 24-voxel grid.
[RITK publisher](https://github.com/ryancinsight/ritk/actions/runs/44667442964).

The Aequitas and Leto default branches now declare 0.5.0 and 0.52.0.
The 0.4 release candidates use the published Aequitas 0.4.0 and Leto
0.51.0 identities. The default-branch scan after Coeus #681 reports
56 incompatible requirements in 11 repositories and lock version drift
in 22 repositories. Reconcile the provider and consumer defaults for
the final pinned Atlas check. All eight repository updates have merged.
Atlas records the merged Apollo, Coeus, Metis, Asclepius, RITK, CFDrs,
Helios, and Kwavers revisions along with the published Mnemosyne
provider. These pins satisfy all declared Git dependency requirements.
Coeus #684 and Kwavers #1117 close the five backlog conformance
regressions. Ares #94, Hermes #308, and Tyche #136 resolve
Mnemosyne Arena 0.7.2 and Memory 0.10.2. Their locked workspace runs
pass 120, 540, and 58 tests respectively. Moirai #718 also aligns
those locks and passes 518 tests with allocator features enabled,
with two cases skipped. The Eunomia #220 merge contains the exact
crate sources shipped in both 0.12.1 archives. Consus #229 selects
that published scalar version through Apollo and passes 76 locked
raster tests, including independent JPEG and analytical transform oracles.

Asclepius Coeus 0.4.0 is verified against the registry checksum and
release revision. Helios #216 uses that archive with the registry
Coeus 0.13.0 packages. Updating Asclepius alone exposes distinct
Coeus tape-variable types. The aligned graph passes all 21 locked
planning tests, including exact and finite-difference gradients.
[Asclepius #127](https://github.com/ryancinsight/asclepius/pull/127)
and [Helios #216](https://github.com/ryancinsight/helios/pull/216).

The pinned stack has no unsatisfied Git package requirements and eight
member lockfiles still select older Mnemosyne versions. Eight member pins
fall outside the default-branch policy. The hosted scan against provider
defaults reports 24 incompatible requirements and 15 stale member locks.
The conformance inventory passes. The Aequitas 0.5 and Leto 0.52
provider releases and consumer updates remain the merge dependency.

### Aequitas 0.5 and Leto 0.52 rollout

Hephaestus #557 merges as `2cb352c52b0a908ef343dd3844248a372ac6506d`.
All six Hephaestus 0.30.0 archives and release tags match that commit.
Host verification, native Metal, software WGPU, and the adapterless CUDA
and ROCm checks pass. The NVIDIA and AMD hardware lanes report skipped.
The release API gate passes against 0.29.0. A fresh Rust 1.95 consumer
resolves one Aequitas 0.5.0, Eunomia 0.12.1, and Leto 0.52.0 provider
set. Host and Leto Ops return −8 at all 16 points for the negative
Laplacian of x² + 3y². Host rejects a buffer with 15 output slots.
[Hephaestus publisher](https://github.com/ryancinsight/hephaestus/actions/runs/44781764295).

Leto #435, Harmonia #103, Horae #137, Hyperion #113, and Proteus #119
merge after the hosted gates. Their standalone locks pass 1,253, 91, 53,
37, and 77 tests respectively. Harmonia uses the current Athena Core
0.4.0 source. Prometheus #98 adopts Aequitas 0.5 and Leto 0.52 and
passes all 47 tests on its merged revision.

The earlier releases Gaia Mesh 0.7.0, Athena Leto 0.4.0, and
Asclepius 0.4.0 pulled in both Aequitas 0.4 and 0.5, and Leto 0.51
and 0.52, when resolved with the new providers. Current releases close
parts of that boundary in dependency order.

- Apollo #722 publishes 20 archives from `7b70b328`. Archive checksums
  and source receipts match. A registry-only consumer builds the 20
  packages and checks a four-sample FFT against a unit spectrum.
- Coeus #682 publishes eight 0.14.0 archives from `4196389a`. The Core
  workflow upload succeeds and the remaining uploads use the local
  Cargo credential after the CPU credential rejection. A fresh Rust
  1.95 consumer checks a 2 × 3 Leto view, rejects a short buffer, and
  finds the exact autodiff derivative 6 for x² at x = 3.
- Gaia #238 publishes Gaia Mesh 0.8.0 from `bdac6214`. A registry-only
  consumer gives a Leto 0.52 box center (1, 2, 3) and volume 64, and
  checks inclusion on a boundary and rejection outside it. Métis #583
  produces the same 960 × 640 PNG and BMP as the Gaia 0.7 base.
- Athena #181 publishes Krylov, Leto, and Hephaestus 0.5.0 from
  `2be05424`. All three archive checksums and source receipts match.

Asclepius #124 publishes both 0.5.0 crates from `b21df8fa` with
matching checksums. Ares #96 uses the same registry Leto 0.52 identity
as Athena. Updating the adapter alone reproduces incompatible Leto view
and scalar types. The aligned locked build passes 120 tests on Rust 1.95.

Helios #217 lands native DICOM. Its latest provider candidates use the
verified Horae Time 0.4.0, Proteus Mat 0.3.0, and Hyperion Transport 0.3.0
archives. A single fresh lock passes a half-second typed time result,
rejects a zero step, and computes exact linear attenuation of 0.5 m⁻¹
from 0.125 m²/kg and 4 kg/m³. The releases follow the prior provider
release branches to retain the Git package contracts of active callers.

The earlier RITK graph pulled Aequitas 0.4, Leto 0.51, Coeus 0.13,
Gaia 0.7, and Apollo FFT 0.30 through Helios and the other integrators.
The dependency scan marks 28 of 31 reachable archives for coordinated
pre-1.0 minor bumps. RITK #1062 merges at `913be32f` after both required
hosted gates pass. The 28 packages and Model 0.5.0 match the registry
checksums and source commit. The release uses the local Cargo credential
for Block Matching, Image I/O, Parcellation, and VTK when the hosted
publisher cannot upload those versions. A fresh consumer resolves all
29 checksums and passes six synthetic DICOM and parcellation tests.
[RITK publisher](https://github.com/ryancinsight/ritk/actions/runs/44819699453).

Hephaestus Core, WGPU, and CUDA 0.32.0 use the same quantity and array
providers with the typed FFT capacity query required by Kwavers. The
three crates.io archives match the sparse-index checksums and the checked
release commit `fc9fba13`. A fresh Metal build rejects 65,535 workspace
bytes, accepts 65,536 bytes, and computes the expected impulse spectrum.
Kwavers #1123 packs the absorbing PSTD coefficients and spectral symbols
to fit the tested Metal device's 29 storage bindings.
[Hephaestus verification](https://github.com/ryancinsight/hephaestus/pull/559).

CFDrs #575 uses the published Consus 0.5, Leto 0.52, and RITK VTK 0.5
graph. The all-feature build and 55 focused Metal and I/O tests pass.
The shared Athena and Harmonia lock uses one Athena Core source.
[CFDrs #575](https://github.com/ryancinsight/CFDrs/pull/575).

Helios #220 adopts the published DICOM and registration providers at
the 0.2.0 boundary. The all-feature build, 115 focused tests, and all
six hosted gates pass. Helios #221 binds publication to the exact
11 approved package versions. The independent allocator uses 0.1.0.
All 11 registry archives match `86a8de1c` and tag `v0.2.0`. A fresh
registry consumer preserves the CT grid pose and voxel values −10, 10,
190, and 2036 HU through the native deflate writer.
[Helios #220](https://github.com/ryancinsight/helios/pull/220),
[publisher](https://github.com/ryancinsight/helios/actions/runs/44832659153).

Kwavers #1124 replaces its temporary RITK revision with the published
0.5-compatible cohort. The locked build and 15 Metal capacity, readback,
and CPU–GPU parity tests pass. Crates.io verifies 21 archives from #1124
and Driver 0.4.0 from #1125. A standalone consumer resolves all 22 archives,
passes the numerical smoke test, and type-checks with the CUDA provider.
The Atlas pin includes #1125. Kwavers #1127 changes the coupling API
after the registry release. CFDrs #576 and RITK #1094 also follow the
verified consumer and provider revisions. The pin-drift register records
the evidence required to advance each pin.
[Release record](https://github.com/ryancinsight/kwavers/pull/1128).

The Atlas overlay preserves the private Python binding's explicit Git
revision. A fresh Cargo probe under the generated overlay resolves the
binding and its caller to one published Aequitas 0.5 instance and
compiles the typed length boundary. The integrated overlay, coherence,
and gitlink checks cover all 28 recorded default revisions.
[Atlas #757](https://github.com/ryancinsight/atlas/pull/757).

Atlas's scheduled compile probe now builds the declared provider source.
It still compiles archived Git revisions for the historical Git pairing.
For crates.io it verifies one locked version and checksum for each
Eunomia package and checks Aequitas in isolation under `--locked`.

All 15 Moirai 0.12.0 prerequisites are verified on crates.io. Thirteen
archives use `c909e4fa`. QUIC and runtime use `139c47ac`, which excludes
tracked measurement archives from the QUIC Cargo package while retaining
the evidence in Git. The retargeted runtime gate passes and the fresh
consumer's timer task waits at least 12 ms and returns 2019.
[Moirai packaging change](https://github.com/ryancinsight/Moirai/pull/716)
and [runtime release](https://github.com/ryancinsight/Moirai/actions/runs/44606668518).

<a id="board-headroom"></a>
## Finding 2026-11-15: the atlas board has no headroom for a new item

Risk: `backlog.md` plus `backlog/*.md` hold 993 of the 1000-line budget after the 2026-11-16b filing sweep (948 at origin/main a74897f8c4b3, 999 on 2026-11-15), so the ratchet admits one more item of the smallest size (3 lines plus 1 index line) and filings must amend existing items.
Evidence: the sweep dropped seven findings of this file, six promoted to items (ATLAS-HOOK-SAFETY-RATCHET-NAME, ATLAS-CAST-CHECK-MEMBER-CI, ATLAS-HOOK-PROVIDER-BUMP-GATE, ATLAS-CONFORMANCE-LANDED-ROWS, ATLAS-MEMBER-BOARD-SCHEMA, ATLAS-HOOK-COMMIT-MSG) and one folded into ATLAS-STANDALONE-CRATES-BUILD, and filed two more (ATLAS-TEST-MAINTENANCE-RACE, ATLAS-HOOK-RELEASED-GATE-CHANGES), using 45 of the 52 free lines; `atlas-board-compact.py --dry-run` reports 141 items, 0 would delete. Remaining levers (judge /869): the 13 `ATLAS-REGISTRY-SLICE-*` items (about 95 lines, dependent slices of closed PR 587) and the four `ATLAS-SEMVER-*` follow-ups, which share one test module and pin sources.
Fix direction: consolidate the registry slices and the SemVer follow-ups, or deliver and delete items, so a filing sweep can add items; no budget raise.
Re-open trigger: a filing refused by the budget, or the slices' consolidation landing.

<a id="leaseless-peer-write"></a>
## Finding 2026-11-13: a leaseless peer write reaches a gate record

Risk: a peer that runs plain `cargo` (no identity lease) on the shared target while the hook's command runs, between clippy and tests or between tests and rustdoc, makes the gate pass and record stale outputs.
Evidence: at b408be289b21d88da9bf544d83c2b93371ce0ff2, atlas#688's single/repush table (`refs/pull/688/head`) has the P1 and P2 columns red for every peer kind (nextest, clippy, doc, buildrs, data). The stale probe, generated `gen.rs` and doc page were reproduced by three independent judges: [first](https://github.com/ryancinsight/atlas/pull/688#issuecomment-6845595294), [second](https://github.com/ryancinsight/atlas/pull/688#issuecomment-6853241893), [third](https://github.com/ryancinsight/atlas/pull/688#issuecomment-6856400115).
Fix direction: either such a peer write cannot reach a record, or the gate refuses to record it; the oracle is those P1 and P2 cells green through the harness of ATLAS-GATE-STAGE-MATRIX.
Re-open trigger: the harness lands and measures the P1 and P2 cells, or a second stale record from a peer's plain `cargo` run is observed.

<a id="sibling-standin"></a>
## Finding 2026-11-13: the sibling stand-in vouches for a peer's bytes

Risk: records copied through the sibling stand-in (ADR 0064; `scripts/atlas_build_identity.py:524-550`) vouch for a peer's bytes.
Evidence: at b408be289b21d88da9bf544d83c2b93371ce0ff2, atlas#688's single/sibling table is red for nextest, doc, buildrs and data at P0 and in every K column, where single/repush is green. The stand-in's real users are the cast-gate keys (`atlas-pre-push-casts-base`, `atlas-pre-push-casts-standalone` in `scripts/git-hooks/pre-push`), and that interaction is unmeasured. Design verdicts: [6845698837](https://github.com/ryancinsight/atlas/pull/688#issuecomment-6845698837), [6855341854](https://github.com/ryancinsight/atlas/pull/688#issuecomment-6855341854).
Fix direction: remove the stand-in, or make it sound under a revised ADR 0064; the oracle is those cells green and one cast-key cell measured through the harness of ATLAS-GATE-STAGE-MATRIX.
Re-open trigger: the harness lands and measures the sibling cells, or a record copied through the stand-in is shown to vouch for changed bytes in a push.

<a id="kwavers-deadline-margin"></a>
## Finding 2026-11-13: a two-package kwavers push misses the pre-push deadline

Risk: gated pushes of `kwavers-simulation` and `kwavers-solver` end at or past the 600 s hook deadline on a quiet host. One push passed with about 3 s to spare; the next, which adds two tests, was killed in rustdoc.
Evidence: ryancinsight/kwavers#1065, 2026-11-13. The push of its first head passed; its identity records were written 598.96 s after the hook started. The push of the next head was killed at 600 s, after clippy 62 s and tests 360 s (nextest: 1243 tests in 237.849 s), with rustdoc unfinished. The hook's stage lines use two clocks: `started` and `completed` come from the identity command's inner shell, whose `$SECONDS` starts at 0, and `verification completed` comes from the outer hook. So the first push's "verification 435-597 s" is not a stage. About 139 s of hook work precedes the inner clock's 0 (derived from file times of the killed push), and the hook records no per-step times. 47 tests of the two packages run exclusively (`threads-required = "num-test-threads"` in kwavers `.config/nextest.toml`), for CPU oversubscription by internally parallel solvers, not for a shared device.
Fix direction: record per-step wall-clock times in the hook, and keep the progress directory of a measured push (`ATLAS_GATE_PROGRESS_PARENT`). Then shorten the steps before the identity command and the exclusive test set, without raising the deadline.
Re-open trigger: a deadline kill of a gated push on a quiet host, or a push whose per-step times are recorded.

<a id="stage-records-rerun-cost"></a>
## Finding 2026-11-13: a rerun after a deadline kill cleans packages the killed run did not write

Risk: after a deadline kill the rerun cleans packages the killed run never wrote, so it costs more than a warm pass. No deadline failure occurred on a quiet host.
Evidence: kwavers#1065's head with main's identity code, one run per row: cold pass 847.2 s; rerun after a 600 s kill 471.9 s; warm pass 326.2 s; rerun after a rustdoc kill (Job Object) 446.2 s. The rustdoc-kill rerun cleaned 14 of 15 path packages ("Removed 5978 files, 3.3GiB total"): 13 are dependencies, which `fresh` (`scripts/atlas_build_identity.py:664-667`) never marks `building`; the 14th, `kwavers-solver`, was the package rustdoc was writing, which the 5 s heartbeat window refused (`scripts/atlas_build_writers.py:238-246`). The cold-kill rerun cleaned 92 Git packages through stale Git stamps.
Fix direction: a rerun cleans only the packages the killed run was writing. Marking dependencies `building` is unsound: it heartbeats shared dependencies over a peer's in-place write (finding G2 of [the design verdict](https://github.com/ryancinsight/atlas/pull/688#issuecomment-6855341854)). atlas#683 (`fix/gate-unit-prune`) is held pending a soundness oracle run through the harness of ATLAS-GATE-STAGE-MATRIX.
Re-open trigger: the harness lands and runs the soundness oracle, or a deadline kill of a gated push is followed by a rerun beyond its warm-pass cost.

## Finding 2026-11-11: the workflow-lint guard can lint an action a runner does not load when the checkout rule places no checkout

Risk: at cbce5fafe58f813a9d1b4f9510809c000df0c870 (the merge of atlas#677) the guard `scripts/atlas_workflow_lint.py` resolves at the candidate's root a step reference that the checkout rule (`governing` in `scripts/workflow_checkout_prefix.py`) maps to no checkout. For a job that checks the candidate out at `P` and then uses `./P/x`, the rule maps the reference to no checkout in five observed spellings: a later checkout into `P/sub`, of another repository or of the candidate; a later checkout of the candidate without `path:`; a later `docker://` step; and the first checkout's `path:` written `./P`. In each, a candidate that tracks `P/x/action.yml` is accepted whether or not it tracks `x/action.yml`, the reference stays as written, and the guard collects `P/x/action.yml` as its lint input, and not `x/action.yml` where the candidate tracks that file. Under the rule's stated assumptions (a checkout writes the tracked files of its commit into its path and nothing else that a reference can name; `path` is read relative to the workspace) a runner looks for `x/action.yml` in the checkout at `P` in the two `P/sub` spellings and the `./P` spelling: there a defect in `x` would pass the lint unseen, and a candidate without `x` would pass although the runner finds no action. In the spelling without `path:`, on a further premise that the rule does not make and that is not verified here (such a checkout writes the candidate into the workspace root; the rule treats it as a checkout of unknown location), the later checkout writes the candidate's own `P/x/action.yml` over that location, and the guard lints the file the runner loads. The rule treats the `docker://` step as a possible checkout of any location, so what a runner loads after it is not derived here. Every statement about a runner in this entry is derived from those assumptions, from the rule's opening premise that a job which checks out at `P` finds `./P/<rest>` at `<rest>` in that checkout, and, for the spelling without `path:`, from that further premise; none is observed on a runner. A candidate that does not track `P/x` is rejected in all five ("reference escapes or is missing from the checkout").
Evidence: two runs by the integrator on 2026-11-11 on an export of that commit (Windows, Python 3.13.12, PyYAML 6.0.3), calling `governing` and `snapshot` on a one-workflow candidate per spelling: with and without `P/x/action.yml`, and with `P/x/action.yml` but without `x/action.yml`. Controls in the same runs: a plain checkout at `P` rewrites the reference to `./x`, collects `x/action.yml`, and rejects a candidate without `x`; a later checkout of another repository into `P/x` is rejected ("checkout path is not shown to hold the candidate"); a reference `./x` with no checkout is accepted when `x` is tracked. The second verdict on atlas#679 (comment 6808026987) repeated the first run and reports the same for `P/sub/deeper`, a path differing in letter case, and `path: ./P/` (relayed). The first verdicts on atlas#677 (comment 6806845687, finding F1) and on atlas#679 (comment 6807230891, findings F1 and F3) report, on earlier commits and for the spellings they ran, that the rule maps the reference to no checkout and that the guard accepts the candidate with `P/x/action.yml` as its lint input (relayed). Re-open trigger: a member or Atlas workflow in which `governing` maps a `./P/...` reference to no checkout although an earlier checkout step of the job names `P`, with or without a leading `./` or a trailing `/`, as its `path:`, in a repository that tracks a directory named like the path. The trigger also fires for the spelling without `path:`, for which this entry derives no exposure only on the unverified premise above. Fix direction (not designed or tested): reject such a reference instead of resolving it at the root.

## Finding 2026-11-11: the workflow-lint guard ends with a traceback on a deeply nested lint input

Risk: `scripts/atlas_workflow_lint.py` creates the parent directories of each lint input with `Path.mkdir(parents=True)` and then writes the file (`_write_project`), and removes its analysis directory through `tempfile.TemporaryDirectory`. That `mkdir` calls itself once per missing ancestor, so a candidate in which a workflow references, directly or through another local action, a local action about 1,000 directories deep, or which holds a workflow file that deep under `.github/workflows`, ends the guard with `RecursionError` and exit status 1 instead of exit status 2 and a `workflow lint:` line. The job still fails, so nothing wrong is accepted; the failure is unreadable. `main` turns only the guard's two error types and `yaml.YAMLError` into that line, so an `OSError` from the same `mkdir` or from the write, a full disk for instance, would end the guard the same way (read from the code at 6c48f2ee640a5743590f32706ab63fc222ef050b, not run by the integrator).
Evidence: relayed from the third verdict on atlas#675 (comment 6805028337, findings G4 and F6), which reports that ending at c841c8fe53e8ee8e3785e85ab24542b81f090671 for an action held 1,000 directories deep, and on that pull request (not at `main`) a second ending, observed there only on Windows with Python 3.11.16, where the recursive `shutil.rmtree` fails at depth 988 while the analysis directory is removed and leaves an `atlas-workflow-lint-*` directory behind. Not reproduced at `main` by the integrator. The first verdict on atlas#680 (comment 6808546350, finding G1 and its evidence for oracle 4) reports at 6c48f2ee640a5743590f32706ab63fc222ef050b, on Windows with Python 3.13.12: `RecursionError` and exit status 1 for a workflow file 1,000 directories deep that references nothing and for a referenced action 1,000 directories deep, exit status 2 for the same workflow file 5 deep and for an unreferenced action 1,000 deep, and exit status 1 with a traceback when the `mkdir` or the write is patched to raise `OSError` (relayed). Re-open trigger: a member repository, or Atlas itself, that tracks a workflow file nested deeper than about 900 directories under `.github/workflows`, or in which a workflow references, directly or through another local action, a local action nested that deep; or a run of the guard that ends with a traceback. Fix: create and remove the analysis tree without recursion and end with a typed error.

## Finding 2026-11-10: build identity cannot read a manifest only cargo parses

Risk: `atlas_build_inputs._cargo_fuzz_manifest` parses each manifest with Python's `tomllib` (TOML 1.0), so a manifest written in TOML 1.1, for example a multi-line inline table that cargo accepts, raises `BuildIdentityError` in every caller of `effective_compiler_environment`. A push of such a root manifest is refused by the cast gate's `clippy` step with exit 2, although `resolved-changes` (atlas#637) gates every member.
Evidence: the judge of atlas#637 reproduced it with a two-commit fixture. Re-open trigger: any member manifest using TOML 1.1 syntax, or a Python whose `tomllib` reads TOML 1.1. Fix: read `package.metadata` from `cargo metadata --no-deps` instead of parsing TOML in Python.

## Finding 2026-11-10: the reused lock tree reads a mirrored cargo config on reused runs only

Risk: with atlas#630 the pre-push lockfile check runs in `$gate_root/lock-tree`, beneath the `$gate_root/.cargo/config.toml` that the gate writes later (the stack config minus `[patch]`). On a reused run `lockfile.py --check` and `cargo deny check sources` read that config; on a first or contended run they do not. Today it holds only build and profile keys, so resolution is unaffected.
Evidence: the judge of atlas#630 (its `scripts/git-hooks/pre-push`, lock tree export and mirrored config writes). Re-open trigger: any `[source]`, `[net]` or `[registries]` key added to the stack cargo config, or a lockfile verdict that differs between a first and a reused run. Fix: run both checks under one fixed config on every run.

## Finding 2026-10-28: parallel clones leave CI member checkout serial

Risk: member checkout consumes the fast job's unchanged ten-minute budget;
`git submodule update --jobs` overlaps clones but not worktree materialization.
The bounded CI helper freezes every committed direct pin and complete mapping,
registers serially, then updates four disjoint fresh destinations with root-state
and error/child-lifetime checks. Closure requires exact-head review and unchanged gates; #551's cohort remains held.

## Finding 2026-10-26: bounded provider checklists do not define four-framework parity

Risk: displacement tables, Coeus's implemented-family manifest and Leto's seeded matrix can appear complete while public comparator APIs, compiler/device/distributed variants and external performance remain unmapped. [The versioned program](docs/parity/README.md) retains source-linked candidates, explicit extraction gaps, separate evidence stages and provider ownership. Source audit corrects stale Coeus constructors/gradchecks and Leto's 28/28 headline without crediting unrun tests. The [JAX dtype policy](docs/parity/dtype-policy/README.md) adds finite symbolic joins and source/case/owner validation while retaining unrun acceptance and unresolved companion artifacts. The NumPy native dtype supplement preserves 78 receipts / 129 functions / 131 spans, 576 symbolic cells and 47 unrun targets, including unresolved temporal quotient and unregistered native-interop prerequisites, with no denominator or mapping-stage credit. Repaired Torch source definitions retain 66 UNRUN cases / 14 gaps and separate actual API ownership, facade proposal and numeric supplier; no mapping or runtime promotion. Independent canonical review adds exact package evidence/gap guards and typed scalar error normalization; same-reviewer final-head assessment remains pending. The [accepted public-evidence capture](docs/parity/reference/public-evidence/README.md) makes reviewed TF 492 and JAX/Torch six source facts durable with separate live owner joins; all 498 unresolved classifications and three uncertified NumPy internal proposals remain requirements, with no gate or stage relief. The [TF conversion capture](docs/parity/core-tensor/tf-conversion-20261026/README.md) retains 30 UNRUN cases / ten open gaps with ordered rounding and cotangent-range guards; its primary API stays unmapped, live owner joins are separate from frozen context, and native behavior remains unqualified. Owner: ATLAS-FULL-PARITY-001. Closure requires complete extraction/semantic classes, reviewed scope decisions and exact-revision qualification; no version bump occurs here.

The existing exact-release-cohort item had a level-one heading without the board's canonical status suffix, causing `atlas-board-index.py check` to fail on unchanged main. Its heading now uses the required anchor/blocked status; the historical status/evidence body remains intact. The generator synchronizes current source titles, retains the overlay's blocked owner hold while correcting its source ID typo, and moves the publisher retry-review pointer into its authoritative body. Hosted CI additionally catches noncanonical board states/priorities and the introduced root checklist; acceptance stays in canonical program items, and source fixes restore all four baseline board counts without changing the ratchet. No provider or publication work is declared delivered by this index repair.

<!-- Compacted 2026-09-26 under the 1,000-line board budget: a risk entry holds risk/evidence/re-open-trigger/owner in ~5 lines; closed findings and delivery narrative are gone -- the record of a closed finding is the commit or PR that closed it. Recover removed narrative with `git log -p -- gap_audit.md`. -->

## Finding 2026-10-26: Aequitas adoption is measured at getters, not formulas

Risk: the cohort audit now catches untyped trait getters, spanning requirements and misleading unit suffixes, but a typed signature does not prove the formula. Two measured examples: `prometheus::ReactionNetwork` stores each reaction's rate constant as a bare `T` documented as order-dependent (`s⁻¹`, `m³·mol⁻¹·s⁻¹`) and `mass_action_rate` accepts any coefficient dimension, so a wrong order wraps silently as `ReactionRate`; `ritk`'s spatial API is millimetre-native raw `f64` (ITK compatibility) with Aequitas used only in diffusion weighting. The sweep found three real errors of this class: `helios_solver::deposit_ray_terma` conserved areal energy [J/m²] but returned `AbsorbedDose` [J/kg] (now `EnergyPerArea`, with the mass-thickness calibration recorded in the Helios gap audit); CFDrs's Kunz cavitation term omitted the `½ ρ_l U_∞² t_∞` normalization, leaving a pressure in a `MassDensityRate` (now typed `reference_velocity`/`reference_time`, dimensionless coefficients); and CFDrs's `nusselt_number` dropped Fourier's sign, returning a negative value for a hot wall (now `−L(∂T/∂y)/(T_wall−T_bulk)` with an asserted `Nu = 2` oracle). A typed accessor is evidence of the unit at the boundary, not of the theorem behind it. Re-open/check: every law provider's analytical oracle is stated in the quantity it returns (a differential against the closed form in SI units), and a provider that stores a coefficient raw names the missing enforcement in its own gap audit. Owner: provider owners; kwavers' remaining raw calculators and CFDrs' kernel scalars are deliberate, documented boundaries, not candidates for a mechanical sweep.

## Finding 2026-10-21: lanes on worktreeConfig members misresolve into the gitdir

Risk: members with `extensions.worktreeConfig=true` (hermes, coeus, leto) resolve a linked lane's shared relative `core.worktree` against the per-worktree gitdir, so `--show-toplevel` becomes `.git/modules/repos/<m>` and checkout writes land in the gitdir while tracked files read deleted (observed 2026-10-21 on three lanes; commits intact). Re-open/check: lane creation writes a per-lane absolute `core.worktree`, asserted by a conformance row over every `worktrees/*` admin dir. Owner: unfiled.

## Finding 2026-10-16: pending publication has no package scope

Risk: an unrelated main merge can release an existing pending cohort. Evidence:
RITK's exact pinned selector returns 29 owned versions; an unrelated member
passes package verification. Check: explicit cohort identity/subset regressions
and empty-installation execution in ATLAS-PUB-EXPLICIT-COHORT-001. Owner: PR544;
Atlas acceptance awaits full gates; RITK adoption separately needs a coherent graph.

## Finding 2026-10-05: path-package identity follows repository revision

Risk: an unrelated commit can invalidate unchanged path-package records and trigger shared-target cleaning. Evidence: `atlas_build_inputs.py` assigns every path package one repository identity, and a clean tree's identity includes that repository's commit revision; observed contention is consistent with this static mechanism, but no benchmark attributes its runtime share. A replacement fingerprint must retain workspace/config, external, build-script, and Git-derived inputs rather than hashing `src/` alone. Owner: none. Re-open: a measured build-input redesign item is claimed.

## Finding 2026-10-02: the bare-cast gate runs only where the current hook runs

Risk: new bare `as` casts land unmeasured wherever the owned pre-push hook is not the current one. The gate (`scripts/atlas_cast_gate.py`, called from the hook's clippy step under the stack's identity leases) reaches only registered members of a stack whose fetched default carries the gate; a standalone clone resolves neither the stack scripts nor a registered member name, so its hook skips the gate; no CI job runs `atlas_cast_gate.py check`, so an admin merge or a push from an old hook lands casts no check counted. Check that would catch it: a member CI job running the gate on the pull-request range. Owner: none. Re-open: a merged cast on an added line in any member.

## Finding 2026-10-02: the bare-cast gate sees one configuration

Risk: clippy reports only casts it compiles: default features and the host target. A cast behind a non-default feature or another target's `cfg` passes on an added line, and a cast inside a `macro_rules!` body is one site at the body however many call sites expand it (probe 2026-10-02), so a new call of an existing casting macro adds none. Rows are measured `--workspace`, push counts `-p`. The push count is also held to the pushed base's count under the same selection when the range renames a file, changes a registered cast module (`cast_modules`), or changes a `Cargo.toml`, a package-root `build.rs`, `.cargo` config or `rust-toolchain` file (`base-triggers`; the base build costs one more closure build, 394-513 s for leto-ops measured 2026-10-03 under lock contention, so it does not run on every push): a moved file or a feature change cannot fill the difference. A source-level `cfg` flip, `#[path]`, `include!`, a new `mod` line naming a file not compiled before, or a build script at a custom `package.build` path or in a helper module triggers nothing and is held to the row alone. Only pushed packages are counted: a pushed package enabling a feature of an unpushed dependency compiles that dependency's casts unmeasured. A manifest whose base fails to compile in its own packages (a rustc error or a denied lint, with cargo naming one of them) leaves those packages to their rows (said on the push), so a fix to a default branch broken in its own source stays pushable; a base broken in a dependency, by unreadable or mismatched crate metadata, or by a compiler that exited abnormally (killed, out of memory, crashed, silent, or panicked: cargo's `Caused by: process didn't exit successfully`) refuses. Cargo's summary must say `due to N previous error`; a compiler fault that still prints that summary and no `Caused by` would pass as a compile error. Code under `cfg(not(feature = ...))` can lift a clean `-p` count above its row (the 2026-10-02 review found no row it breaks). Check that would catch it: run the gate under the feature matrix (`cargo hack --each-feature`) in the scheduled member CI job. Owner: none. Re-open: a cast found in feature- or target-gated code after merge, or a count failure on a push that adds no cast.

## Finding 2026-10-02: the pre-push gate skips the feature matrix CI checks

Risk: a change that compiles only with default features passes pre-push and fails CI. Evidence: ryancinsight/eunomia#143 (its pushed head before the no-std test fix) passed the owned pre-push gate; CI's `cargo check --all-targets --no-default-features` failed (`to_string` with no `std` in a test). The hook runs clippy and nextest with the default or CI-lint feature set only. Check that would catch it: the hook runs each member's committed feature-matrix list, as `cargo check` on the changed packages. Owner: none. Re-open: the next hook change, or the next CI-only feature failure.

## Finding 2026-09-24: Dioxus joins the GUI comparator set

Metis [ADR 0003](repos/metis/docs/adr/0003-framework-conformance.md) now pins
Dioxus 0.7.10 as a comparator (closest Rust GUI framework: one component tree
to browser/desktop/mobile WebViews plus a native wgpu renderer). First pass
closed state/routing gaps in Metis (PR #400) and native menu bars in Moirai
(PR #468). Open: nested layouts with history, SSR/hydration, Rust hot
patching, mobile bundles. The stack owns no Dioxus dependency; it is an
evidence comparator, not a requirement. Re-open trigger: a Dioxus minor
release, when the ADR table is re-read against the new crates.

## Finding 2026-09-09: six members enforce no merge gate

hermes, eunomia, leto, mnemosyne, moirai, and themis carry neither branch
protection nor rulesets, so a PR merges whatever CI reports — their green
history is a property of who has been merging, not of the repository. Each
needs its required contexts named from its own workflow, and `strict` must
ship with `allow_update_branch = true` (the fix already applied to Apollo and
Hephaestus after `strict` alone stalled auto-merge on a `BEHIND` branch).
Re-open trigger: any member merging a red PR, or the next merge-mechanics
pass.

## Finding 2026-08-21: print_dbg — not a safe mechanical sweep

`print_dbg` counts ~285 real production sites (CFDrs 257, ritk 17, kwavers
44 minus overlap, hermes 4) behind `println!`/`eprintln!`/`dbg!`, plus ~31
`build.rs` Cargo-protocol false positives and ~50 xtask/scratch sites. Each
real site needs a per-crate migration to a logging facade (`tracing`); it is
provider-owned, not an Atlas-side mechanical sweep. Re-open trigger: a
provider crate adopts `tracing` and the scanner's `build.rs` false-positive
class is fixed (exempt `cargo:` protocol writes).

## Finding 2026-08-21: missing_deny_docs — not a safe editorial sweep

`missing_deny_docs` counts 118 `lib.rs` files across 12 repos; 114 have
undocumented public items even in `lib.rs` alone, so adding
`#![deny(missing_docs)]` would break compilation. Only 5 crates have `lib.rs`
fully documented, and `deny(missing_docs)` applies crate-wide, so submodules
still need verification. Per-crate doc work is provider-owned (tracked by
ATLAS-KWAVERS-ALLOC-PROBE-DENY-DOCS-2026-08-21 for the kwavers pilot). Not an
Atlas-side editorial sweep.

## Finding 2026-09-21: rev-pin churn silts up the shared cache

A `rev =` advance on a first-party git dependency is a new source identity:
cargo compiles a fresh generation and never reclaims the old one. Fingerprint
directories per distinct build unit run 3-14x over baseline for repeatedly
re-pinned crates (mnemosyne 140/9, moirai 197/15) against unchurned themis
(41/1). `scripts/atlas-cache-retention.py` names the general eviction problem
but its units (profiles, `incremental/` children) don't reach per-rev
`deps/`/`.fingerprint` generations, and nothing invokes it from CI. Re-open
trigger: fingerprint-directories-per-build-unit exceeds ~2x for any
first-party crate in the shared cache.

## Finding 2026-08-20: target_forks regrows faster than the ratchet can see it

`is_cargo_target_dir` correctly reads 0 for registered members, but the class
is in `HOST_OBSERVED_CLASSES` and forced to 0 in the baseline regardless —
so a real regrowth reads as resolved. Two structural causes, not config
holes: cargo resolves configuration from cwd upward, so `repos/.cargo/
config.toml` never reaches a `--manifest-path` invocation run from outside
`repos/`; and a per-purpose directory (`ci-wheel-target/`, `bench-
replicated/`) bypasses any shared-cache config by construction. A private
per-member `target-dir` (e.g. asclepius) also defeats sharing while reading
as 0. Re-open trigger: any `repos/<member>/target*` satisfies
`is_cargo_target_dir` again, or the class is moved out of
`HOST_OBSERVED_CLASSES`.

## Finding 2026-08-19: Apollo PR #107 benchmark remains red

Apollo PR #107 (head `d408c738`) fails 17 counterbalanced benchmark cases
(sizes 64/96, Rader f32/31 and f64/53, composite primes), candidate slower in
all four orderings — an empirical performance residual, not a tolerance or
workload issue. No merge or instrument change is authorized until root-cause
profiling lands on the active branch. Re-open trigger: a profiled fix changes
the measured comparison.

## ATLAS-CFDRS-TEST-BUDGET — exact provider-head runtime residual (reopened 2026-08-17)

Two `cfd-validation` numerical-fidelity tests (`microventuri_35um_case_...`,
`cross_fidelity_trifurcation_dominance`) exceed the unchanged 30 s nextest
budget; the timeout is inherited from the production solver path, so no
workload or budget change is authorized. First bounded slice landed (CFDrs
PR #347, merged `84499e957`): removed a per-correction clone of the immutable
pressure CSR matrix, brought both cases to ~16.8 s locally. Re-open trigger:
the exact-head hosted run against the current budget; the broader
solver-budget residual remains open pending further profile-first slices.

<a id="atlas-us-capability-023"></a>
## ATLAS-US-CAPABILITY-023 — kwavers/ritk capability audit vs ITKUltrasound (open 2026-08-13)

Reference: `KitwareMedical/ITKUltrasound`, enumerated from its own tree (63
public headers) and verified per-capability against kwavers/ritk sources.
Present with no gap: analytic-signal, B-mode, TGC, box-sigma smoothing,
least-squares strain, block-matching parabolic interpolation, the VTK
structured-grid sink half, and the FFT backend role. Partial: curvilinear
scan conversion (2-D only, no inverse direction), 1-D frequency-domain
filtering (no N-D image seam), ultrasound HDF5 I/O, and block-matching
displacement estimation (ritk has only a scalar autodiff NCC metric).

Sub-findings, still open:
- **D3 placement (ATLAS-D3-PLACEMENT-034):** `block_matching` is
  dependency-light (imports only `anyhow`) but lives in `ritk-registration`,
  which pulls the full coeus autograd/nn/wgpu stack — forcing a physics
  crate to choose between a mandatory optional dependency or hiding a core
  kernel behind a feature flag. Corrective step (US-023-D4, not yet filed as
  its own item): move `block_matching` into a new dependency-light crate,
  the same pattern US-023-A5 used for the coordinate map into `ritk-spatial`.
- **Asymmetric fan (ATLAS-US-A3-FAN-028):** kwavers' and ritk's inverse
  curvilinear-fan maps agree on everything except the beam index; ritk's fan
  cannot express kwavers' asymmetric fan as filed. Unresolved as of last
  read.
- A3's original "delete the converter" plan was corrected: `CoordinateMap`/
  `CurvilinearArray`/`PhasedArray3D` moved to `ritk-spatial` (US-023-A5,
  merged via ritk PRs #132/#133), unblocking A3's remaining split (kwavers
  delegates polar math, keeps its own storage).

Open findings register (RITK-CI-1, US-023-A2) live on the owning item,
[ATLAS-US-CAPABILITY-023](backlog.md#atlas-us-capability-023).

<a id="atlas-ritk-ci-diag-035"></a>
## ATLAS-RITK-CI-DIAG-035 — RITK-CI-1 diagnosis (open)

Diagnosis, not a fix (another author's deliberate change): `3aa73ba0`
*fix(ritk-filter)!: Apply the direction matrix in index<->physical
transforms* (ADR 0020) is the origin. ADR 0020 claims axis-aligned tests
pass, but the three failing SimpleITK parity tests use identity
direction/zero origin/unit spacing — the axis-aligned case — contradicting
that claim; they run only in the Python-wheel smoke job, separate from Rust
suites, which is likely why they went unseen. Deviations: 2-D inverse
displacement field max error 2.23 (gate 1e-4), 3-D 0.082, iterative 0.171.
Owner: `3aa73ba0`'s author. Oracle: the three `test_simpleitk_cmake_data.py`
parity tests pass.

<a id="atlas-usct-fwi-024"></a>
## ATLAS-USCT-FWI-024 — kwavers audit vs FullWaveformInversionUSCT (open 2026-08-13)

Reference: `rehmanali1994/FullWaveformInversionUSCT` (Ali, SPIE Medical
Imaging 2022, Vol. 12038) — frequency-domain transmission-USCT FWI via the
angular-spectrum/split-step method, NLCG with Gilbert-Nocedal hybrid beta and
a linearized exact line search. Verdict: kwavers exceeds the reference on
forward-model rigor (convergent Born series beats split-step) and optimizer
machinery (source-scaling identifiability accounting), and is ahead overall;
residual gaps (F1/F2) are small and independently verifiable against the
reference. Owning item: [ATLAS-USCT-FWI-024](backlog.md#atlas-usct-fwi-024).

## Finding: kwavers legacy-migration residual (nalgebra/ndarray/burn/rayon)

Last measured 2026-07-08: kwavers still carried direct `nalgebra` at ~13
sites/5 manifests, `ndarray` at ~1,660+ line-hits across all 24 crates (only
1 crate on `leto`'s `ndarray-compat`), 41 residual `Zip::par_for_each` sites
pending a `moirai_parallel` migration, and a transitive `rayon` edge via
`ritk -> burn`. Three months of continuous kwavers development have passed
since this was measured — treat every count here as stale; re-measure via
`scripts/atlas-conformance.py` rather than trust this narrative. Owner:
unclaimed (provider-side). Re-open trigger: none filed; a re-audit is due
before this finding is cited as current.

## Finding: ATLAS-KWAVERS-REAL-COMPUTE-028's evidence is missing from this file

`backlog/atlas-kwavers-real-compute-028.md` cites
`gap_audit.md#atlas-kwavers-real-compute-028` for exact identity-return-path
locations, but that finding was dropped in the 2026-09-21 compaction pass and
never reconstructed here — the link is dangling. Do not fabricate the
locations; re-run the identity-path audit named in that item's outcome and
refile the finding under this anchor. Re-open trigger: the item is next
claimed.

## Shared incremental-cache growth — open

`target/debug/incremental` accumulated 27,085 session directories / 525 GB
in five days stack-wide; an idle-tree prune reclaimed the bytes but the
recurrence cause (no incremental-disable on clean CI runners, ~950 leaf
binary targets per ATLAS-BUILD-STRUCTURE-001) is unfixed. Re-open trigger:
the next clean Kwavers architecture run, to compare artifact bytes and peak
memory against the preferred 10 GiB clean-build budget.

## Finding 2026-09-25: cfd-math `ParallelAssembly::from_elements` is dead public surface

No stack consumer, caller, test, or doctest anywhere in the fleet
(`git grep from_elements` over CFDrs `origin/main` finds only the
definition). `cfd-math` is publishable, so removal is breaking. Re-open
trigger: a first consumer appears, or the next major removes it.

## Finding 2026-09-25: apollo-sft recovery bench fixture costs 137s against its 60s budget

`benches/recovery.rs` builds its input signal with O(N·K) trig at N=2^20,
K=16 before measurement starts — a fixture-design defect, not measured code.
Re-open trigger: the fixture drops the per-sample trig loop, or N shrinks
with the scaling-ratio claim preserved.

## Finding 2026-09-25: the hook publisher compares member working trees, not their defaults

`atlas-lock-form.py publish-hooks` diffs `repos/<member>/.githooks/` bytes
against a stale local checkout instead of `origin/HEAD`, so a reused sync
branch can republish another writer's hook — on 2026-09-25 this landed a
no-op hook over a UTF-16 copy on 24 members. Re-open trigger: the comparison
reads `origin/HEAD` in the member, as `sync-hooks --check` already
contracts.

## Finding 2026-10-08: `gh pr` subcommands without an explicit number act on the shared checkout's peer PR

`gh pr merge`/`view`/`ready`/`checks` with no `<number>` resolves to the
current branch's PR, and in shared trees the checkout routinely sits on a
peer's branch — so a bare invocation reads, readies, or auto-merges the
*peer's* PR. Observed twice in one session (2026-10-08): the peer PRs
atlas#512 and athena#99 were merged by commands aimed at freshly created
branches whose PRs the same shell had just failed to select. Both were
ready and green so landing matched their authors' intent, but the
invocation's target is what was hit-or-miss, and a draft or red peer PR
would not have been safe to touch. Root cause: the CLI's current-branch
default combined with checkout tenancy. Catching check: any agent-side
wrapper (or review grep) rejects `gh pr (merge|view|ready|checks)`
invocations lacking an explicit `<number>` when more than one open PR
exists. Re-open trigger: that wrapper lands in the stack tooling.

## Finding 2026-10-09: provider moves leave their exports below the crate root

Twice in one day a moved capability reached the owner's submodule
re-export list but not the crate-root `pub use` every sibling item
travels (leto#343: `solve_csr_via_dense_lu`; athena#103: the four saddle
preconditioners) — both first surfaced as consumer E0432s at the next
integration, not in the provider's own gates, because the provider's
tests import within the crate. Root cause: the moves edit the module
manifest but treat the root export list as untouched surface. Catching
check: for each moved pub item, the provider's PR checklist asserts the
crate-root `pub use` gained the name — mechanically, a one-line script
comparing the module's exports against the root list. Re-open trigger:
that check lands in the stack tooling.

<a id="precision-profile-tier-conflation"></a>
## Finding 2026-10-12: `CpuStorage::PROFILE` is one const on a storage type read by two tiers whose arithmetic disagrees

Risk: the CPU typed plans widen `f32`/`F16` storage into the owner `f64`/`Complex64` arithmetic, while the accelerator typed paths dispatch the same storage through `Complex32` device buffers and compute natively. A single `PROFILE` const on `CpuStorage` therefore describes one tier truthfully and the other falsely, and a caller of the lied-about tier is rejected. Measured on the apollo worktree base: `apollo-nufft` `type1_typed_storage_matches_represented_input` panicked with `InvalidPlan { message: "precision profile does not match typed NUFFT-WGPU storage" }` whenever a GPU adapter was present, and passed only because the test early-returns without one — a host without an adapter cannot observe this class of failure, so the CPU test gate is blind to it by construction. Only `NufftComplexStorage` was conflated; `apollo-{radon,sht,sft,stft}` and `apollo-fft`'s transform backend already bound on `GpuStorage` and were correct throughout. Evidence: apollo PR #650, whose `refactor(apollo)` commit splits the consts; on current `origin/main` #630 has reverted the widening rebase so `[F16; 2]::PROFILE` is `MIXED_PRECISION_F16_F32` again, which leaves the defect latent rather than fixed — the conflation returns the moment anyone re-adopts a widening descriptor.

Root cause: a profile is a property of a *path*, not of a storage type, and the trait stored it on the type. Two independent callers then read one value and disagree about what it means.

Catching check: the reference port on apollo rescue branch `rescue/apollo-nufft-device-profile` (preserved as PR apollo#677) adds a `DEVICE_PROFILE` const to the storage trait plus three host-runnable value-semantic tests that pin both tiers' profile values; its push is blocked by the conformance ratchet `apollo/manifest_implementation` rising because the additions return to the flattened module root. The check that must land is therefore structural: the accelerator tier names its own profile, and a test with no device asserts each type's profile on both tiers.

Re-open trigger: any change to `CpuStorage::PROFILE`, or a re-adoption of widening descriptors, which this finding cites as the reproduction path. Twin consolidation delivered under apollo #652 and consus #171 (both merged); the monomorphization review item is closed.

<a id="whole-file-writer-utf8-mangling"></a>
## Finding 2026-10-12: whole-file writers mangle non-ASCII into cp1252 double-encoding on Windows hosts

Risk: an agent's whole-file write that resolves the file as cp1252 instead of UTF-8 rewrites every non-ASCII byte pair as its Windows-1252 interpretation re-encoded in UTF-8, silently corrupting Rustdoc and test prose while leaving the file valid UTF-8, so no gate notices. Measured 2026-10-12 in the apollo worktree: five files carried `π`->`Ï€`, `Σ`->`Î£`, `è`->`Ã¨`, `∀`->`Ãž` and friends across module docs, proptest contracts and published references (`apollo-nufft/.../transform/dimension_1d.rs`, `.../dimension_1d/proptest_suite.rs`, `apollo-sft/.../transform/sparse.rs`, `sparse/plan.rs`, `sparse/tests.rs`). The corruption is recoverable only by re-encoding the runs back through cp1252, which is exactly what repaired it; the same class had already reached apollo's CHANGELOG.md, where it remains. This session's own first PowerShell heredoc reproduced the failure live, so it is not hypothetical.

Root cause: the writer, not the file. Every mechanism that rewrites a whole file from a shell heredoc, a `Set-Content`/`Out-File` without an explicit UTF-8 encoding, or an editor defaulting to the system code page can do this on a Windows host.

Catching check: a conformance scan over tracked text files rejecting any run of two or more characters in U+0080..U+00FF whose cp1252 re-encoding is valid UTF-8, plus a byte-level check that a file the agent rewrote is unchanged outside its intended edit. Both are cheap and deterministic; neither exists.

Re-open trigger: the scan lands in the stack tooling, or a second occurrence is observed. Pre-existing instance already recorded: apollo `CHANGELOG.md` at `main`.

<a id="apollo-scratch-rescue-weakening"></a>
## Finding 2026-10-13: apollo rescue ref preserves a defect-masking test weakening

Risk: `refs/rescue/apollo-scratch-order-isolation` (apollo checkout only, unpushed) preserves a hunk that renames the scratch-hook registry test and weakens its release-count assertion from an exact `assert_eq!` to `>= 1`; applying it would mask the thread-local hook leak instead of fixing it. Re-open trigger: the ref still exists; delete the ref and this finding together once its isolation hunk is confirmed landed on apollo main or obsolete against it.

<a id="fast-pytest-timeout-margin"></a>
## Finding 2026-11-10: the fast script-test job runs at its timeout

Risk: `script-tests / Run pytest (fast)` (`.github/workflows/python-tests.yml`, `timeout-minutes: 10`) is cancelled with every test passing, and the required ratchet verdict that needs it never runs. Evidence: run 42953704487 on ryancinsight/atlas#660 reported 2713 passed in 529.31 s and was cut after 602 s of job time; the seven successful runs before it took 391 to 539 s, against a five-minute verification target.

Catching check: the job's duration against a committed budget in the scheduled CI report, and the suite's slowest tests moved to the slow job or sharded until the fast job holds the five-minute target; the bound itself does not rise.

Re-open trigger: a second cancellation at the bound, or the fast job's median passing 480 s.

## Finding 2026-11-15: the member hook fleet restores locks unsynchronized and follows the checked-out branch

Risk: (1) the hook's `Cargo.lock` snapshot and restore is unsynchronized, so concurrent hooks can restore over each other; the selector and publisher fixes do not serialize it, and members whose stale hook refuses or times out the sync push are published through the git data API with the same bytes. (2) 25 members set `core.hooksPath=.githooks`, so the hook version follows the checked-out branch: `repos/CFDrs` on 2026-09-28 sat 80 commits behind and its pre-push failed on the `python3` Store stub until a peer switched the tree; only one member points at `D:/atlas/scripts/git-hooks`. Owner: [ATLAS-HOOK-FLEET-DUPLICATION-2026-09-06](backlog.md#hook-fleet-duplication). Re-open trigger: a lock restored over a peer's, or a refused push traced to a stale member checkout.

<a id="cast-gate-undeclared-package"></a>
## Finding 2026-11-27: a pushed package no tracked manifest names passes the cast gate's cfg scan with nothing scanned

Risk: `check --package <p>` passes with nothing scanned when no tracked `Cargo.toml` names `<p>` and none is unparsed (`package_sources`, `unparsed_manifests`), so a `#[cfg(not(clippy))]` bare cast in it goes unread. The hook takes `--package` from cargo metadata, so only a manifest the gate's listing misses opens this, and `is_manifest` (line 1299) compares the basename to `Cargo.toml` exactly. Witnesses at origin/main d0c92fbcf73d36bb3cbe8fbd89a3a5cb76088a9d: `crates/q/cargo.toml` beside a parsed member `p`, the cast in q's source, `--package q`: exit 0 (tracked as `Cargo.toml`: exit 1); a gitlink at `crates/s`, `--package s`: exit 0. That cargo reads the lowercase name on a case-insensitive host is recalled, not run. No member has either (judge of atlas#822, 28 members' HEADs). [ATLAS-CAST-GATE-CFG-CLIPPY](backlog.md#atlas-cast-gate-cfg-clippy) does not close before this is carried: its outcome, never passing `check` unmeasured, is false while this stands.

Catching check: `--package q` named by no manifest, the `cargo.toml` fixture and the gitlink fixture each exit 1 naming the package; `test_check_judges_a_pushed_range_end_to_end`, `test_check_reads_the_base_sites` and the last call of `test_a_cast_module_exempts_only_its_own_lines_under_a_base_count` track a manifest for each package they push.

Re-open trigger: a member tracks a gitlink or a manifest not spelled `Cargo.toml`.

<a id="cast-gate-glob-member-decoy"></a>
## Finding 2026-11-27: `members = ["crates/**"]` may let a nested decoy manifest count as the built package

Risk: with `members = ["crates/**"]`, a parsed manifest nested under a member (`crates/q/tests/fixtures/p`, package `p`) matches the glob, so `built_packages` (line 1371) counts `p` as built and the unparsed `crates/p/Cargo.toml`, whose `[[bin]] path` reaches outside its directory, is not refused. Witness at origin/main d0c92fbcf73d36bb3cbe8fbd89a3a5cb76088a9d, a predicate in the bin's file: exit 0; without the decoy: exit 1; one parsed `p` under `crates/**` beside an unrelated unparsed manifest: exit 0. The judge of atlas#822 recalls that cargo rejects two workspace members named `p`, so the hook's cargo metadata would fail first; not run.

Catching check (the settling method, and the next step): in a lane under D:/atlas, run `cargo metadata --no-deps --format-version 1 --manifest-path <fixture>/Cargo.toml` under a ten-minute deadline, with and without the decoy. If cargo refuses the decoy, a test skipped without cargo pins that and this entry deletes. If it accepts, the fixture must exit 1 and the control keep exiting 0; the remedy is a judge call, and counting names carried by exactly one member does not close it (`crates/p` does not parse, so the decoy is the one parsed `p`).

Re-open trigger: the metadata run, or a member whose `members` holds a `**` glob.

<a id="cast-gate-path-dep-member"></a>
## Finding 2026-11-27: a package built only as a path dependency of a member is refused beside an unrelated unparsed manifest

Risk: `built_packages` (line 1371) holds the root package and each parsed workspace member, so a pushed package the root builds only as a path dependency of a member is not counted, and any unparsed manifest elsewhere refuses its push (fails closed). Witness at origin/main d0c92fbcf73d36bb3cbe8fbd89a3a5cb76088a9d: root `members = ["crates/a"]`, `crates/a` depends on `b = { path = "../b" }`, `crates/b` parses, `tools/x/Cargo.toml` does not; `--package b`: exit 1 refusing `tools/x/Cargo.toml`. That cargo makes a path dependency inside the workspace directory a member is recalled from the Cargo book, not run. No member pays it (judge of atlas#822: 0 unparsed manifests at the 28 members' HEADs).

Catching check: that fixture exits 0 with `tools/x` named once on standard output, while a parsed `b` at `fixtures/b` that no member depends on stays at exit 1 (both exit 1 today); reverting to "any parsed manifest of the name declares" passes the first and fails the existing decoy fixture. First step: confirm the Cargo rule with `cargo metadata --no-deps` on the fixture in a lane.

Re-open trigger: a member's HEAD holds an unparsed manifest.

<a id="cast-gate-root-built-text"></a>
## Finding 2026-11-27: the unparsed-manifest messages say a parsed manifest declares a package, while the rule is that the root builds it

Risk: the refusal (line 646), the note (line 648) and the module docstring (line 31) of `scripts/atlas_cast_gate.py` say "no manifest that parses declares" and "a manifest that parses declares", while `built_packages` counts only manifests the root builds; in the decoy fixture (unparsed `crates/p`, parsed `fixtures/p`) a parsed manifest carries the name, so the refusal is false. The docstrings of `unparsed_manifests` and `built_packages` also leave out that a repository with no root `Cargo.toml` builds nothing (`built_packages` returns an empty set), and the excluded standalone crate's refusal follows only from two adjacent sentences. Witnesses at origin/main d0c92fbcf73d36bb3cbe8fbd89a3a5cb76088a9d: no root `Cargo.toml` beside an unparsed `tools/x`, `--package p`: exit 1 (0 without `tools/x`); an excluded crate `q` beside it: exit 1 (0 without it).

Catching check: the decoy refusal and the unrelated-manifest note contain "root builds" and not "parses declares", `git grep -n "parses declares" -- scripts/atlas_cast_gate.py` lists nothing, and both docstrings state the no-root and excluded-crate refusals, each pinned by a test.

Re-open trigger: any change to `built_packages` or to those messages.

<a id="cast-gate-root-second-mount"></a>
## Finding 2026-11-27: an unparsed root manifest's targets are reported as a member's second cast-module mount

Risk: the second-mount walk (`target_mounts`, line 687; `second_target_problems`, line 711) attributes every registered cast module under an unparsed root's directory to the root, so root targets that mount a member's module are reported as the member's second target. Witness at origin/main d0c92fbcf73d36bb3cbe8fbd89a3a5cb76088a9d: root `[package] name = "top"` plus `[workspace] members = ["crates/core"]` plus a table `tomllib` rejects, root `src/lib.rs` and `src/main.rs` each mounting `../crates/core/src/cast.rs`, `core` parsing and mounting it once, `--package top`: exit 1 with two lines, the root-manifest refusal and "core: cast module crates/core/src/cast.rs is compiled by more than one crate target (src/lib.rs, src/main.rs)". The push is refused either way, so the harm is a misattributed line (over-refusal, derived, not run).

Catching check: that fixture exits 1 with the root-manifest line and no line naming `core`; skipping the report for every module under an unparsed manifest's directory is the wrong fix, since the acceptance case (unparsed member `crates/core`, `lib.rs` and `main.rs` mounting `src/cast.rs`, `--package core`) must still name `core`'s two targets (it does at that commit).

Re-open trigger: a change to `target_mounts` or `second_target_problems`, or a member root manifest `tomllib` rejects (0 at the member HEADs, judge of atlas#833).

<a id="cast-gate-cfg-macro-forms"></a>
## Finding 2026-11-27: a `cfg` predicate naming `clippy` that a macro assembles is not seen by the cast gate's cfg scan

Risk: the module docstring of `scripts/atlas_cast_gate.py` states that a predicate built by macro substitution has no `cfg(` token and is not seen. Witnesses at origin/main d0c92fbcf73d36bb3cbe8fbd89a3a5cb76088a9d, a bare `as` cast beneath each in a member `p`: `macro_rules! g { ($($t:tt)*) => { #[cfg($($t)*)] ... } }` with `g!(not(clippy));`: exit 0; the same through `$m:meta` (`#[cfg($m)]`): exit 0; `#[cfg_attr($($t)*)]` with `g!(clippy, cfg(any()));`, which leaves the item to rustc and hides it from clippy: exit 0, and its expansion written directly: exit 1; the direct `#[cfg(not(clippy))]`: exit 1; a macro with no `cfg` fragment: exit 0. `include!(concat!(..))` and a macro-written `mod` are the same class (judge of atlas#805, F4; not run). Owning item: [ATLAS-CAST-GATE-CFG-CLIPPY](backlog.md#atlas-cast-gate-cfg-clippy).

Catching check: the three macro fixtures exit nonzero naming the file and line while the direct and no-`cfg` controls keep exit 1 and 0; matching the literal transcriber `$($t:tt)*` closes the first only. Refusing a `macro_rules!` whose transcriber puts a `$` fragment inside `cfg` or `cfg_attr`, versus reading the macro-expanded crate, is a judge call.

Re-open trigger: `git grep -E 'cfg(_attr)?[[:space:]]*\([^;{]*\$' -- '*.rs'` matches in a member (0 at the member HEADs, judge of atlas#833).

<a id="cast-gate-outside-file-push"></a>
## Finding 2026-11-27: a push that changes only a file outside every package, mounted by a package, runs no cast gate

Risk: `cargo_input_owners` (`scripts/atlas_cargo_inputs.py`, line 56) walks a changed path up for a `Cargo.toml`; for `shared/extra.rs` in a virtual workspace it finds none and selects no package, and `scripts/git-hooks/pre-push` returns at "no package owns the changed files" (line 1863) before the cast gate runs, so a package's `#[path]` or `include!` mount of that file is never judged. Observed at origin/main d0c92fbcf73d36bb3cbe8fbd89a3a5cb76088a9d: `cargo_input_owners` on a synthetic virtual workspace with member `core` mounting `shared/extra.rs` selects `()` for `shared/extra.rs`, `shared/unmounted.rs` and `README.md`, and `('core',)` for `crates/core/src/lib.rs`; the hook's early return was read, not run. The judge of atlas#786 derived the gap (F3).

Catching check: in `scripts/tests/test_atlas_cargo_inputs.py`, `shared/extra.rs` selects `("core",)` while `shared/unmounted.rs` and `README.md` still select `()`; selecting every package for any outside path is the wrong fix, since it fails the second. Where the mounted-file set comes from (`compiled_files` in `scripts/atlas_cast_gate.py`, or cargo metadata's target roots) is a judge call.

Re-open trigger: a push is observed to end at that message with a changed file a package mounts.
