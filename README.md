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

Shared crates are themselves standalone repositories consumed as submodules
wherever they are needed — the pattern `CFDrs` already uses for `gaia` and
`apollo`. A crate shared by multiple packages lives in one repo and is added as
a nested submodule in each consuming package, so there is a single source of
truth and each package still builds in isolation.

## Layout

```
atlas/
├── repos/
│   └── CFDrs/            # submodule -> github.com/ryancinsight/CFDrs
│       └── crates/
│           ├── gaia/     # nested submodule -> github.com/ryancinsight/gaia
│           └── apollo/   # nested submodule -> github.com/ryancinsight/apollo
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
