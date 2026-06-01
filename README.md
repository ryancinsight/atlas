# atlas

Meta-repository aggregating independent simulation packages and the crates they
share. Each package is a standalone Git repository, linked here as a Git
submodule, and remains independently clonable and buildable on its own.

## Model

`atlas` is an **orchestration layer**, not a single Cargo workspace. A Cargo
workspace cannot contain a member that is itself a workspace, and each
submodule (e.g. `CFDrs`) is its own workspace. `atlas` therefore:

- pins each package to a specific commit via submodules (`repos/<name>`),
- drives cross-package build/test/update from one place (`scripts/`),
- documents how shared crates are consumed.

### Shared crates

Shared crates are themselves standalone repositories, checked out at the atlas
root under `repos/` alongside the packages that consume them (`gaia`, `apollo`).
A crate shared by multiple packages lives in one repo (single source of truth);
consuming packages depend on it by **Git remote** (default branch = latest), so
each package still clones and builds in isolation without vendoring the source.

Local development loop for a shared crate: edit its working copy under
`repos/<crate>`, commit and push to its remote, then in each consuming package
run `cargo update -p <crate>` to pick up the new commit.

## Layout

```
atlas/
├── repos/
│   ├── CFDrs/            # submodule -> github.com/ryancinsight/CFDrs
│   │                     #   depends on gaia + apollo via Git remote
│   ├── gaia/             # submodule -> github.com/ryancinsight/gaia   (shared)
│   ├── apollo/           # submodule -> github.com/ryancinsight/apollo (shared)
│   ├── consus/           # submodule -> github.com/ryancinsight/consus (shared: storage formats)
│   ├── ritk/             # submodule -> github.com/ryancinsight/ritk   (shared: VTK + imaging)
│   ├── mnemosyne/        # submodule -> github.com/ryancinsight/Mnemosyne (shared: global allocator)
│   └── moirai/           # submodule -> github.com/ryancinsight/Moirai    (shared: concurrency runtime)
├── scripts/              # cross-package orchestration
├── .gitmodules
└── README.md
```

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

# Build / test every package
pwsh scripts/build-all.ps1     # Windows
./scripts/build-all.sh         # Unix

# Pull the latest commit of every submodule
git submodule update --remote --recursive
```

## Adding a package

```sh
git submodule add <url> repos/<name>
git submodule update --init --recursive
git commit -m "atlas: add <name> package"
```
