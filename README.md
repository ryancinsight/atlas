# atlas

Meta-repository aggregating independent Rust package workspaces that form one
coordinated simulation, numerics, storage, memory, and runtime stack. Each
package is a standalone Git repository, linked here as a Git submodule, and
remains independently clonable and buildable on its own.

## Model

`atlas` is an **orchestration layer**, not a Cargo workspace. A Cargo
workspace cannot contain a member that is itself a workspace, and each
submodule can be its own workspace. `atlas` therefore:

- pins each package to a specific commit via submodules (`repos/<name>`),
- drives cross-package build/test/update from one place (`scripts/`),
- documents how shared crates are consumed together.

### Shared crates

Shared crates are standalone repositories, checked out at the atlas root under
`repos/` alongside the packages that consume them.
A crate shared by multiple packages lives in one repo (single source of truth);
consuming packages depend on it by **Git remote** (tracked branch = latest), so
each package still clones and builds in isolation without vendoring the source.

Local development loop for a shared crate: edit its working copy under
`repos/<crate>`, commit and push to its remote, then in each consuming package
run `cargo update -p <crate>` to pick up the new commit.

## Atlas stack

The submodules are separate repositories, but atlas treats them as a coordinated
stack. Dependency evidence comes from each repository's `Cargo.toml` and local
README.

| Repository | Atlas role | Used by |
| --- | --- | --- |
| `CFDrs` | CFD simulation suite and primary integration consumer. It combines mesh generation, transforms, scientific output, VTK output, allocator selection, and data-parallel execution. | Consumes `gaia`, `apollo`, `consus`, `ritk`, `mnemosyne`, and `moirai`. |
| `gaia` | Watertight CFD mesh generation and geometry kernel. It provides the `gaia` crate, consumed as `cfd-mesh` by CFDrs and directly by RITK. | Consumed by `CFDrs` and `ritk`. Optionally bridges to `cfd-schematics`. |
| `apollo` | Fourier, spectral, number-theoretic, wavelet, and related transform implementations, with CPU, WGPU, validation, and Python crates. | Consumed by `CFDrs` for FFT/NUFFT, by `coeus` for FFT-backed tensor operations, and internally uses `moirai` in selected transform crates. |
| `consus` | Pure-Rust scientific storage formats and I/O: HDF5, Zarr, NetCDF, Parquet, Arrow, FITS, MAT, NWB, HDMF, compression, and Python bindings. | Consumed by `CFDrs` for HDF5 output and by `ritk` for HDF5/core/compression/I/O support. Uses `moirai` for parallel and native transport paths. |
| `ritk` | Medical image processing, registration, codec, and VTK workspace. It owns `ritk-vtk`, the VTK data model and I/O used by CFD output. | Consumed by `CFDrs` through `ritk-vtk`; consumes `gaia`, `moirai`, and `consus`. |
| `coeus` | Strided tensor, operations, autodiff, neural-network, sparse, optimizer, distribution, GPU, CUDA, and Python workspace. | Consumes `mnemosyne` for storage allocation, `moirai` for data-parallel execution, `hermes` for SIMD effects, and `apollo` for FFT. |
| `leto` | Shared N-dimensional strided array, layout, view, slicing, and storage vocabulary for Atlas. It is the planned replacement for direct `ndarray` usage where Apollo and Coeus need a common non-differentiable array substrate. | Intended for `apollo` and `coeus`; uses `mnemosyne` for optional aligned allocation, `moirai` for parallel operations, and `hermes` for SIMD-backed kernels. |
| `hermes` | Numeric and SIMD abstraction workspace: scalar/numeric foundations, SIMD core, intrinsics, register types, macros, examples, and benchmarks. | Consumed by `coeus` as the SIMD-effect single source of truth. |
| `mnemosyne` | User-space allocator and memory-management workspace: core, backend, arena, local, heap, hardened, decay, profiling, C shim, and benchmarks. | Consumed by `CFDrs`, `coeus`, and `moirai`; paired conceptually with `melinoe` capability tokens. |
| `melinoe` | Branded, multi-token phantom capabilities for compile-time data-access and thread-synchronization proofs. | Supports the Mnemosyne memory ecosystem; currently tracked as a standalone foundation crate in atlas. |
| `moirai` | Concurrency, scheduling, async, parallel iteration, transport, metrics, GPU, TLS, HTTP, and Python runtime workspace. | Consumed by `CFDrs`, `coeus`, `ritk`, `consus`, and selected `apollo` crates. |

### Naming Conventions

Several repositories use names from classical mythology to represent their functional domains:

| Repository | Mythological Entity | Domain Mapping |
| --- | --- | --- |
| `gaia` | **Gaia** (Personification of Earth) | Geometry kernels and watertight mesh generation. |
| `apollo` | **Apollo** (God of music and harmony) | Fourier, spectral, and numerical transforms. |
| `consus` | **Consus** (Roman god of storage and grain silos) | Scientific storage formats, I/O serialization, and file transport. |
| `coeus` | **Coeus** (Titan of intellect and inquiry) | Strided tensors, neural networks, autodiff, and optimization. |
| `leto` | **Leto** (Titaness, daughter of Coeus and mother of Apollo) | Shared strided-array substrate between Coeus tensor/autodiff systems and Apollo spectral transforms. |
| `hermes` | **Hermes** (Messenger god of speed) | Low-level SIMD, register types, and vector abstractions. |
| `mnemosyne` | **Mnemosyne** (Titaness of memory) | User-space memory allocation and arena management. |
| `melinoe` | **Melinoe** (Chthonic goddess of phantoms) | Phantom capability tokens for compile-time safety and synchronization proofs. |
| `moirai` | **Moirai** (The Fates, spinners of the threads of life) | Concurrency, async task scheduling, and runtime orchestration. |

### Dependency flow

Current manifest-level dependency flow:

```text
CFDrs
├── gaia       # CFD mesh generation
├── apollo     # FFT and NUFFT transforms
├── consus     # HDF5/scientific output
├── ritk       # VTK output through ritk-vtk
├── mnemosyne  # optional global allocator feature
└── moirai     # parallel execution

coeus
├── apollo     # FFT-backed tensor operations
├── leto       # planned shared array/layout substrate
├── hermes     # SIMD abstraction
├── mnemosyne  # tensor storage allocation
└── moirai     # data-parallel execution

leto
├── mnemosyne  # optional aligned storage backend
├── moirai     # parallel elementwise/reduction scheduling
└── hermes     # SIMD operation backend

ritk
├── gaia       # mesh/geometry integration
├── consus     # HDF5 and scientific I/O support
└── moirai     # data-parallel execution

consus
└── moirai     # parallelism and native transport support

apollo
├── leto       # planned ndarray replacement for array/view surfaces
└── moirai     # selected transform crates with parallel execution
```

Repositories still depend on each other through Git remotes, not by path from
the atlas root. The checked-out copies under `repos/` provide synchronized local
editing, review, and cross-package verification.

## Layout

```
atlas/
├── repos/
│   ├── apollo/           # Fourier transform planning and execution workspace
│   ├── CFDrs/            # computational fluid dynamics simulation workspace
│   ├── coeus/            # strided tensor library workspace
│   ├── consus/           # scientific storage-format workspace
│   ├── gaia/             # watertight CFD mesh-generation workspace
│   ├── hermes/           # SIMD abstraction workspace
│   ├── leto/             # shared N-dimensional strided array workspace
│   ├── melinoe/          # branded phantom-capability foundation crate
│   ├── mnemosyne/        # user-space memory allocator workspace
│   ├── moirai/           # concurrency library workspace
│   └── ritk/             # medical image processing and registration workspace
├── scripts/              # cross-package orchestration
├── .gitmodules
└── README.md
```

`.gitmodules` is the authoritative source for submodule remotes and tracked
branches.

## Clone

Submodules are nested, so clone recursively:

```sh
git clone --recurse-submodules https://github.com/<owner>/atlas.git
# or, after a plain clone:
git submodule update --init --recursive
```

## Working with packages

```sh
# Build / test a single package (it is a self-contained workspace)
cargo build  --manifest-path repos/CFDrs/Cargo.toml
cargo test   --manifest-path repos/CFDrs/Cargo.toml

# Build every package
pwsh scripts/build-all.ps1     # Windows: cargo build
./scripts/build-all.sh         # Unix: cargo build

# Test every package
pwsh scripts/build-all.ps1 test
./scripts/build-all.sh test

# Run another Cargo subcommand across every package
pwsh scripts/build-all.ps1 clippy --all-targets --all-features -- -D warnings
./scripts/build-all.sh clippy --all-targets --all-features -- -D warnings

# Pull the latest commit of every submodule
git submodule update --remote --recursive
```

## Adding a package

```sh
git submodule add <url> repos/<name>
git submodule update --init --recursive
git commit -m "atlas: add <name> package"
```
