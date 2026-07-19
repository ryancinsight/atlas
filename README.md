# atlas

Meta-repository for the Rust workspaces that form the Atlas multiphysics
simulation stack. Atlas coordinates numeric laws, memory and execution
providers, reusable scientific domains, and end-user simulation suites without
collapsing their independent release histories.

## Repository model

`atlas` is an orchestration repository, not a Cargo workspace. Each package is
an independent Git repository mounted at `repos/<name>` as a submodule.

The root repository owns:

- the exact package set and remotes in [`.gitmodules`](.gitmodules);
- a reproducible stack revision through the recorded submodule gitlinks;
- cross-package build and verification drivers in [`scripts/`](scripts);
- stack-wide architecture decisions in [`docs/adr/`](docs/adr).

Each package owns its crate topology, direct dependencies, lockfile, tests,
release policy, and detailed documentation. The package's `Cargo.toml` and
`Cargo.lock` are authoritative for direct dependency edges; this README
documents bounded-context ownership and must not be read as an exact Cargo
dependency graph.

Shared first-party capabilities follow provider-first ownership. A missing
operation is implemented in the provider that owns its bounded context, then
consumers update their pins. Consumer-local compatibility layers and duplicate
provider implementations are not part of the Atlas model.

## Current stack

At this revision, [`.gitmodules`](.gitmodules) records 17 packages.

| Layer | Repository | Canonical role |
| --- | --- | --- |
| Integrator | [`CFDrs`](repos/CFDrs) | Computational fluid dynamics, coupled flow simulation, validation, and scientific output. |
| Integrator | [`helios`](repos/helios) | Radiation-therapy dose, planning, imaging, and delivery simulation. |
| Integrator | [`kwavers`](repos/kwavers) | Acoustic, ultrasound, therapy, imaging, and coupled wave simulation. |
| Domain | [`apollo`](repos/apollo) | Fourier, spectral, wavelet, number-theoretic, and related transforms. |
| Domain | [`coeus`](repos/coeus) | Strided tensors, automatic differentiation, neural networks, optimization, and sparse operations. |
| Domain | [`consus`](repos/consus) | Native scientific storage formats, compression, and data transport. |
| Domain | [`gaia`](repos/gaia) | Geometry predicates, topology, watertight meshes, and mesh generation. |
| Domain | [`ritk`](repos/ritk) | Medical-image formats, processing, registration, visualization, and VTK data models. |
| Compute | [`hephaestus`](repos/hephaestus) | GPU device, buffer, transfer, and kernel substrate for WGPU and CUDA. |
| Compute | [`hermes`](repos/hermes) | CPU SIMD/SWAR vocabulary, ISA dispatch, and vector kernels. |
| Compute | [`leto`](repos/leto) | N-dimensional host arrays, layouts, views, operations, and linear algebra. |
| Compute | [`mnemosyne`](repos/mnemosyne) | Allocation, arenas, heaps, staging memory, and allocator instrumentation. |
| Compute | [`moirai`](repos/moirai) | Scheduling, parallel iteration, async execution, synchronization, and transport. |
| Foundation | [`aequitas`](repos/aequitas) | Physical-quantity law: type-level SI dimensions, transparent quantities, and linear-unit conversion over Eunomia scalars. |
| Foundation | [`eunomia`](repos/eunomia) | Datatype law: scalar, complex, packed, conversion, and numeric-trait vocabulary. |
| Foundation | [`melinoe`](repos/melinoe) | Branded capability evidence for memory access and synchronization. |
| Foundation | [`themis`](repos/themis) | Placement law for NUMA nodes, workers, locality domains, and memory tiers. |

The diagram is a layer map, not a literal manifest graph. Higher layers consume
contracts owned below them, and a package may legitimately skip an intermediate
layer.

```mermaid
flowchart TB
    subgraph Integrators
        CFDrs
        helios
        kwavers
    end

    subgraph Domains["Reusable scientific domains"]
        apollo
        coeus
        consus
        gaia
        ritk
    end

    subgraph Compute["Compute, data, memory, and execution"]
        hephaestus
        hermes
        leto
        mnemosyne
        moirai
    end

    subgraph Foundation["Law and capability foundation"]
        aequitas
        eunomia
        melinoe
        themis
    end

    Integrators --> Domains
    Integrators --> Compute
    Domains --> Compute
    Compute --> Foundation
    aequitas --> eunomia
```

### Provider ownership

| Concern | Owner | Boundary |
| --- | --- | --- |
| Physical quantities and dimensional law | `aequitas` | Owns dimensions and linear units over Eunomia scalars, not scalar representations or domain validity. |
| Numeric representations and scalar laws | `eunomia` | Owns datatype vocabulary, not algorithms or storage. |
| Placement and locality law | `themis` | Owns typed placement facts, not allocation or scheduling. |
| Capability proofs | `melinoe` | Owns branded access evidence, not memory management. |
| Allocation and memory policy | `mnemosyne` | Owns host allocation, arenas, heaps, and staging memory. |
| Execution and transport | `moirai` | Owns scheduling, parallelism, async execution, synchronization, and transport. |
| CPU lane-parallel execution | `hermes` | Owns SIMD/SWAR kernels and runtime ISA selection. |
| Host arrays and linear algebra | `leto` | Owns layouts, views, array operations, and CPU linear algebra. |
| Accelerator execution | `hephaestus` | Owns GPU devices, buffers, transfers, pipelines, and provider kernels. |
| Spectral transforms | `apollo` | Owns transform mathematics and plans; accelerator mechanics remain in Hephaestus. |
| Tensors and autodiff | `coeus` | Owns tensor semantics, differentiation, neural-network operations, and optimizers. |
| Geometry and meshes | `gaia` | Owns geometric predicates, topology, and mesh generation. |
| Scientific persistence | `consus` | Owns storage formats, compression, and persistent scientific data exchange. |
| Medical imaging | `ritk` | Owns image formats, processing, registration, and VTK data models. |

The accepted GPU boundary is recorded in
[ADR 0001](docs/adr/0001-gpu-accelerator-substrate.md). The reproducible
provider-pin contract and its evidence limits are recorded in
[ADR 0020](docs/adr/0020-provider-graph-refresh.md). Aequitas ownership and
consumer-boundary integration are recorded in
[ADR 0021](docs/adr/0021-aequitas-quantity-law-foundation.md).

## Naming

Classical names describe bounded contexts rather than implementation variants.

| Repository | Classical reference | Mapping |
| --- | --- | --- |
| `atlas` | Atlas, the Titan who bears the heavens | Coordinates the independently versioned stack. |
| `aequitas` | Aequitas, Roman personification of equity and fair measure | Physical quantities, units, and dimensional law. |
| `apollo` | Apollo, associated with music and ordered harmony | Spectral and numerical transforms. |
| `coeus` | Coeus, Titan associated with intellect and inquiry | Tensor computation and learning systems. |
| `consus` | Consus, Roman god associated with stored grain | Scientific storage and persistence. |
| `eunomia` | Eunomia, goddess of good order | Datatype laws and conversion order. |
| `gaia` | Gaia, personification of Earth | Geometry, topology, and meshes. |
| `helios` | Helios, personification of the Sun | Radiation and imaging simulation. |
| `hephaestus` | Hephaestus, god of the forge | Accelerator devices and kernels. |
| `hermes` | Hermes, swift messenger god | SIMD dispatch and vector execution. |
| `leto` | Leto, mother of Apollo and daughter of Coeus | Shared array substrate between transform and tensor domains. |
| `melinoe` | Melinoe, an underworld goddess associated with phantoms | Zero-sized phantom capability evidence. |
| `mnemosyne` | Mnemosyne, Titaness of memory | Allocation and memory management. |
| `moirai` | The Moirai, who govern the threads of fate | Scheduling and execution of program threads. |
| `themis` | Themis, Titaness of divine law and order | Placement and locality law. |

`CFDrs`, `kwavers`, and `ritk` retain descriptive project names. New
repositories use a classical name only when the mapping clarifies a stable
bounded context.

## Future package roadmap

The following names are architectural candidates, not current submodules,
published crates, or implementation commitments. Names remain provisional until
repository and crate-name availability is checked. No empty repository should
be created from this list: promotion requires a real vertical implementation
extracted from an existing need.

### Promotion gate

A candidate becomes an Atlas package only when all of these conditions hold:

1. At least two packages need the capability, or an existing implementation is
   already in the wrong dependency layer.
2. A source audit proves that no current provider owns the same bounded context.
3. An ADR defines the contract, dependency direction, migration, non-goals, and
   conformance or differential oracle.
4. The first change moves real computation into the new owner, migrates every
   in-scope caller, and deletes the superseded implementation.
5. The package is independently versioned or consumed across repository
   boundaries; otherwise it remains a module or crate in the current owner.
6. `.gitmodules`, this stack table, affected provider documentation, and
   cross-package verification move in the same delivery unit.

### Candidate packages

| Priority | Working name | Classical reference | Proposed bounded context | Current drivers |
| --- | --- | --- | --- | --- |
| P0 | `horae` | The Horae, goddesses of seasons and ordered time | Time-integration contracts, timestep control, subcycling, event clocks, and convergence metadata. It owns no domain equations. | Time-stepping families recur in CFDrs and Kwavers and are required by coupled Helios workflows. |
| P0 | `athena` | Athena, goddess of wisdom and strategy | Operator-based linear and nonlinear solvers, Krylov methods, preconditioning contracts, and convergence reporting. Leto retains arrays, decompositions, and linear-algebra kernels. | Solver and convergence protocols recur across CFDrs, Kwavers, RITK, and Helios. |
| P0 | `harmonia` | Harmonia, goddess of harmony and concord | Multiphysics coupling, state exchange, relaxation, fixed-point convergence, and heterogeneous subcycling. It owns coupling mechanics, not physics models. | Coupling orchestration recurs in CFDrs, Kwavers, and Helios. |
| P1 | `proteus` | Proteus, the shape-changing sea god | Material, phase, mixture, and constitutive-property vocabulary parameterized by Aequitas quantities and Eunomia scalars. | Material-property models recur across flow, acoustics, therapy, and imaging domains. |
| P1 | `tyche` | Tyche, goddess of fortune and chance | Uncertainty quantification, sampling, ensembles, sensitivity, and reproducible stochastic studies. Execution remains in Moirai and persistence in Consus. | Validation and design-space exploration recur across the three integrators. |
| P1 | `asclepius` | Asclepius, god of medicine and healing | Biological-response, tissue-effect, treatment-response, and therapy outcome models. | Helios and Kwavers share treatment and tissue-response concerns; RITK supplies imaging inputs. |
| P2 | `iris` | Iris, messenger goddess associated with the rainbow | Domain-neutral visualization, diagnostic views, and render/plot contracts. File formats remain with RITK or Consus. | Simulation and validation outputs need a common presentation boundary. |
| P2 | `ares` | Ares, god of war | Solid mechanics, deformation, contact, and fluid-structure interaction. | Elastography and coupled CFD can provide the first two consumers. |
| P2 | `hyperion` | Hyperion, Titan associated with heavenly light | Electromagnetic, optical, and radiation-transport operators. | Kwavers and Helios contain adjacent wave and radiation concerns. |
| P2 | `prometheus` | Prometheus, Titan associated with fire and craft | Thermochemistry, reactions, combustion, and reactive transport. | Reactive-flow and thermal-therapy work can establish the shared contract. |

### Dependency order

The recommended extraction order is:

```text
eunomia
└── aequitas
    ├── horae
    ├── athena
    └── proteus
         └── harmonia
              └── CFDrs / helios / kwavers

moirai + consus ── tyche
coeus + aequitas ── asclepius
domain result views ── iris
```

`harmonia` follows the units, time, solver, and material contracts because it
must compose those contracts rather than create competing versions. `ares`,
`hyperion`, and `prometheus` remain domain-level candidates until two concrete
consumers justify extraction.

The following concerns are not package gaps:

- arrays, layouts, views, and host linear algebra belong to `leto`;
- GPU devices, buffers, transfers, and kernels belong to `hephaestus`;
- scheduling, async execution, synchronization, and transport belong to
  `moirai`;
- SIMD and SWAR execution belongs to `hermes`;
- allocation and staging memory belongs to `mnemosyne`;
- geometry and mesh generation belongs to `gaia`;
- scientific storage and checkpoint persistence belongs to `consus`.

## Layout

```text
atlas/
├── docs/
│   └── adr/              # stack-wide architectural decisions
├── repos/
│   ├── CFDrs/
│   ├── apollo/
│   ├── coeus/
│   ├── consus/
│   ├── eunomia/
│   ├── gaia/
│   ├── helios/
│   ├── hephaestus/
│   ├── hermes/
│   ├── kwavers/
│   ├── leto/
│   ├── melinoe/
│   ├── mnemosyne/
│   ├── moirai/
│   ├── ritk/
│   └── themis/
├── scripts/              # cross-package orchestration
├── .gitmodules
└── README.md
```

## Clone

```sh
git clone --recurse-submodules https://github.com/ryancinsight/atlas.git
cd atlas
```

After a non-recursive clone:

```sh
git submodule update --init --recursive
```

## Work with packages

Build or test one package from its repository:

```sh
cd repos/CFDrs
cargo build
cargo nextest run
cargo test --doc
```

Run the same Cargo command across every checked-out package:

```sh
# Windows
pwsh scripts/build-all.ps1
pwsh scripts/build-all.ps1 nextest run
pwsh scripts/build-all.ps1 test --doc
pwsh scripts/build-all.ps1 clippy --all-targets -- -D warnings

# Unix
./scripts/build-all.sh
./scripts/build-all.sh nextest run
./scripts/build-all.sh test --doc
./scripts/build-all.sh clippy --all-targets -- -D warnings
```

Update the checkout to the commits recorded by the parent repository:

```sh
git submodule update --init --recursive
```

Advancing package pins is a reviewed provider-graph change. Fetch and verify
the package's remote default branch, update its gitlink, run the affected
provider and consumer gates, and commit the parent pointer only after the child
revision is published.

## Add a package

A package must pass the [promotion gate](#promotion-gate) before it enters the
meta-repository.

```sh
git submodule add <url> repos/<name>
git submodule update --init --recursive
git commit -m "feat(atlas): Add <name> package"
```
