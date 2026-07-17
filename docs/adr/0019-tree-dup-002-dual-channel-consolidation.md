# ADR 0019 — TREE-DUP-002: Dual channel consolidation (moirai-core)

- Status: **Accepted**
- Date: 2026-07-16
- Drivers: ADR-0018 Phase 4 (deferred); two competing channel implementations in `moirai-core/src/` (`channel/` + `unified_channel/`) with completely disjoint consumer sets; the `channel/` module has 7 consumers, `unified_channel/` has 1 (`moirai-iter`); no file in the workspace imports from both.
- Anchors: `repos/moirai/moirai-core/src/channel/` (SPSC/MPMC/Hybrid/Select + `Channel<T>` trait); `repos/moirai/moirai-core/src/unified_channel/` (UnifiedChannel + sender/receiver/config/stats); `repos/moirai/moirai-iter/src/advanced_patterns.rs` (sole unified_channel consumer); `repos/moirai/moirai-core/src/lib.rs` (re-exports both).
- See also: ADR-0018 §Phase 4 (defines TREE-DUP-002 as a deferred `[major]` item); `AGENTS.md` §consolidation_discipline (duplicate abstraction families merge into one authoritative home).
- Index: docs/adr/INDEX.md#ADR-0019

## Context

`moirai-core/src/` has two channel systems:

- **`channel/`** — SPSC, MPMC, Hybrid channel types plus `Select` multiplexer. All implement the `Channel<T>` trait (`send`, `try_send`, `recv`, `try_recv`, `is_empty`, `is_full`, `capacity`). Consumed by `moirai` runtime, `moirai-transport`, `moirai-core::communication` (pubsub, router), and benchmarks. 7 consumers.

- **`unified_channel/`** — `UnifiedChannel` with `UnifiedSender`/`UnifiedReceiver` endpoint types, `ChannelConfig`, `ChannelStatistics`, `send_batch`/`recv_batch`. No shared trait — each endpoint delegates to `UnifiedChannel` directly. Does not implement `Channel<T>`. Consumed only by `moirai-iter::advanced_patterns` (StreamingIterator, ProducerConsumerPair). 1 consumer.

Both are public re-exports from `moirai-core/src/lib.rs`.

### Consumer survey (completed during ADR-0018 planning)

| Consumer | Uses | Channel type |
|----------|------|-------------|
| `moirai/src/runtime.rs` | `mpmc()`, `spsc()`, `unbounded()` re-exports | `channel::select` |
| `moirai-transport/src/lib.rs` | `MpmcSender`, `MpmcReceiver` type aliases | `channel::mpmc` |
| `moirai-core/communication/pubsub.rs` | `MpmcSender` with `.try_send()` | `channel::mpmc` |
| `moirai-core/communication/router.rs` | `MpmcSender` | `channel::mpmc` |
| Benchmarks & examples | `mpmc()`, `spsc()` | `channel` |
| **`moirai-iter/src/advanced_patterns.rs`** | `UnifiedSender`, `UnifiedReceiver`, `ChannelConfig`, `unified_channel()`, `unified_channel_with_config()` | `unified_channel` |

**No file imports from both modules.** This makes the migration safe: only one consumer file needs updating.

### Gap between the two systems

| Feature | `channel/` | `unified_channel/` |
|---------|-----------|-------------------|
| Trait | `Channel<T>` (7 methods) | None (direct impl) |
| Sender/Receiver endpoints | Per-type (e.g. `MpmcSender`) | `UnifiedSender`/`UnifiedReceiver` |
| Select multiplexer | `Select::try_recv` | None |
| Batching | None | `send_batch`, `recv_batch` |
| Config | None | `ChannelConfig` (capacity, pooling, batching) |
| Statistics | None | `ChannelStatistics` |
| Close detection | Per-channel via `closed: AtomicBool` | Via `UnifiedChannel::close`/`is_closed` |
| Error type | `ChannelError` (Full/Empty/Closed/WouldBlock) | `UnifiedChannelError` (+InvalidConfig) |

### Design approach

Rather than surgically merging the two implementations into one (a complex, high-risk refactor of the lock-free SPSC/MPMC/Hybrid internals), we:

1. **Extend `Channel<T>`** with optional batching, close, and statistics methods (default implementations preserve backward compat for existing impls).
2. **Fold `UnifiedChannel`** into `channel::unified` as a concrete `Channel<T>` implementor, keeping its ring-buffer + overflow-queue internals unchanged.
3. **Merge the error types**: add `InvalidConfig` to `ChannelError`.
4. **Re-export everything** from `channel/`; remove `unified_channel/` module.

This eliminates the dual-path ambiguity while keeping each implementation's internals untouched — the consolidation is at the module and trait boundary, not at the algorithm level.

## Decision

### 1. Extend `Channel<T>` trait (error.rs)

Add to the trait:

```rust
/// Send multiple values in batch. Default: calls send() in a loop.
fn send_batch(&self, values: Vec<T>) -> Result<usize> { ... }

/// Receive up to max_count values in batch. Default: calls recv() in a loop.
fn recv_batch(&self, max_count: usize) -> Vec<T> { ... }

/// Close the channel. Default: no-op (channels that support close override).
fn close(&self) {}

/// Check if closed. Default: false.
fn is_closed(&self) -> bool { false }

/// Current number of buffered items. Default: 0.
fn len(&self) -> usize { 0 }

/// Return statistics if the channel tracks them.
fn stats(&self) -> Option<ChannelStatistics> { None }
```

Add `InvalidConfig` variant to `ChannelError`.

### 2. Fold `unified_channel/` into `channel/unified/`

- Move `unified_channel/core.rs` → `channel/unified/core.rs`
- Move `unified_channel/sender.rs` → `channel/unified/sender.rs`
- Move `unified_channel/receiver.rs` → `channel/unified/receiver.rs`
- Move `unified_channel/config.rs` → `channel/config.rs` (shared type)
- Move `unified_channel/stats.rs` → `channel/stats.rs` (shared type)
- Move `unified_channel/error.rs` → delete (absorb into `channel/error.rs`)
- Move `unified_channel/tests.rs` → `channel/unified/tests.rs`
- Delete `unified_channel/mod.rs` (functionality moves to `channel/unified/mod.rs`)

`UnifiedChannel` implements `Channel<T>` with:
- `send`/`try_send`/`recv`/`try_recv`/`is_empty`/`is_full`/`capacity` — delegates to existing impl
- `send_batch`/`recv_batch` — uses existing batch methods
- `close`/`is_closed` — uses existing close flag
- `len` — delegates to existing `len()` (ring + overflow count)
- `stats` — returns `ChannelStatistics`

`UnifiedSender`/`UnifiedReceiver` remain as public endpoint types, re-exported from `channel`.

### 3. Merge error types

`ChannelError` gains `InvalidConfig` variant. The unified channel's `try_send` signature (which returns the message on failure) is preserved as an inherent method on `UnifiedChannel`; the `Channel<T>` trait's `try_send` keeps its simpler `Result<()>` signature.

### 4. Module re-exports

`channel/mod.rs` re-exports:
```rust
pub mod config;    // ChannelConfig (from unified_channel/config.rs)
pub mod stats;     // ChannelStatistics (from unified_channel/stats.rs)
pub mod unified;   // UnifiedChannel, UnifiedSender, UnifiedReceiver, unified_channel()

// Existing exports unchanged
pub use error::{Channel, ChannelError, Result};
pub use hybrid::{HybridChannel, HybridReceiver, HybridSender};
pub use mpmc::{MpmcChannel, MpmcReceiver, MpmcSender};
pub use select::{mpmc, spsc, unbounded, Select};
pub use spsc::{SpscChannel, SpscReceiver, SpscSender};
pub use config::ChannelConfig;
pub use stats::ChannelStatistics;
pub use unified::{UnifiedChannel, UnifiedReceiver, UnifiedSender};
```

### 5. Migrate `moirai-iter`

`advanced_patterns.rs` changes:
- Import from `moirai_core::channel::{UnifiedSender, UnifiedReceiver, ChannelConfig, unified_channel, unified_channel_with_config}` instead of `moirai_core::unified_channel::*`
- All other usage remains identical (same type names, same constructors)

### 6. Update `lib.rs`

- Remove `pub mod unified_channel;` and the associated `pub use unified_channel::{...}` 
- `channel` module re-exports now include `ChannelConfig`, `ChannelStatistics`, `UnifiedChannel`, `UnifiedReceiver`, `UnifiedSender`, `unified_channel`, `unified_channel_with_config`

### Rejected alternatives

**Deep merge into one implementation**: Merging the lock-free SPSC/MPMC ring-buffer internals with UnifiedChannel's overflow queue would require rewriting both and risk introducing correctness defects. The two implementations serve different performance profiles (SPSC/MPMC: zero-copy lock-free for hot paths; UnifiedChannel: ring + overflow for adaptive backpressure). Keeping separate implementations under one trait is the canonical seam pattern.

**Delete unified_channel outright**: `moirai-iter` depends on `send_batch`/`recv_batch` which existing channel types do not support. Adding batching trait methods and keeping the implementation is less work than porting `moirai-iter` to use SPSC/MPMC with manual batch loops.

**Make UnifiedChannel the only implementation**: Would require reimplementing `Select` integration and the lock-free fast paths that SPSC/MPMC provide. The `channel/` types have 7 consumers; `unified_channel/` has 1. The direction is toward extending the existing trait, not replacing its implementations.

## Consequences

### Positive

1. Single module tree for all channel types: `moirai_core::channel`.
2. All channel types implement `Channel<T>`, enabling polymorphic usage.
3. `ChannelConfig` and `ChannelStatistics` are available to all consumers.
4. `send_batch`/`recv_batch` available on any `Channel<T>` (with default fallback).
5. Zero behavior change for `channel/` consumers (existing types unchanged).
6. Only one consumer file (`moirai-iter`) needs updating.

### Negative

1. `ChannelError::InvalidConfig` is a breaking enum change (any consumer exhaustively matching on `ChannelError` must handle the new variant). No external consumers match exhaustively — all use `?` or `.is_err()` — so this is a `[major]` by strict SemVer only.
2. `Channel<T>` trait gains new methods (breaking for external trait implementors). No external implementors exist; all impls are inside `moirai-core`.
3. The `unified_channel` public module is deleted (breaking for direct importers beyond `moirai-iter`). No workspace crate imports from `unified_channel` except `moirai-iter`.
4. `ChannelConfig` previously under `moirai_core::unified_channel::ChannelConfig` moves to `moirai_core::channel::ChannelConfig`.

### Risks

1. **Inadvertent feature divergence**: `Channel<T>` default method bodies could silently degrade if a channel type gains native batching/close but the default (which uses the loop form) remains. Mitigation: each override is explicit, and the unified channel's `send_batch`/`recv_batch` use its native fast path. No other channel type is expected to override batching.

2. **Re-export collision in `lib.rs`**: Both `channel::unified::unified_channel` and `channel::select::unbounded` are free functions — no name conflict. The `unified_channel` / `unified_channel_with_config` constructors are re-exported from `channel` module.

## Verification plan

1. `cargo check -p moirai-core` clean (no new warnings).
2. `cargo nextest run -p moirai-core` 100% pass (all existing channel tests + unified channel tests).
3. `cargo check -p moirai-iter` clean (migrated imports compile).
4. `cargo nextest run -p moirai-iter` 100% pass.
5. `cargo check -p moirai` clean (consumer re-exports unchanged).
6. `cargo check -p moirai-transport` clean (type aliases unchanged).
7. `grep -r "moirai_core::unified_channel" repos/moirai/` returns zero matches (no stale imports).
8. `ls repos/moirai/moirai-core/src/unified_channel/` does not exist (module deleted).
9. `cargo clippy -p moirai-core --all-targets --all-features -- -D warnings` clean.

## Sequencing

1. Extend `Channel<T>` trait with batching/close/stats methods and `InvalidConfig` error variant.
2. Move unified_channel into channel/unified, implement `Channel<T>`.
3. Move `ChannelConfig` to `channel/config.rs`, `ChannelStatistics` to `channel/stats.rs`.
4. Update `channel/mod.rs` re-exports.
5. Update `lib.rs` to consolidate re-exports through `channel` only.
6. Migrate `moirai-iter` to new import paths.
7. Delete `unified_channel/` module directory.
8. Run verification plan.
