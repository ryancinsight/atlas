<a id="atlas-kwavers-python-surface-2026-08-21"></a>
## ATLAS-KWAVERS-PYTHON-SURFACE-2026-08-21 — Complete typed and concurrent PyO3 surface [minor] — in-progress
- **outcome:** the Kwavers Python wheel exposes every registered Rust class/function through one generated typed package surface (`py.typed`+`.pyi`), every long-running binding call releases the GIL, and the facade exports exactly the registered public symbols — proven by a deterministic generator (CI regen-and-diff), a strict typed consumer, and a runtime export-inventory oracle.
- **next: remaining GIL families** — GPU-session, cavitation-monitor, and chirp/sweep paths still hold the GIL and need the same `py.detach` + overlap-oracle treatment as the delivered families.
- **Pending:** post-merge default CI runs at `ca5c9c93` before the Atlas gitlink advances. Architecture Validation fails repo-wide (pre-existing, not required, not this item's regression) — filed as its own item.
- **Non-goals:** no domain logic in Python, no runtime introspection as source of truth, no facade compatibility aliases.
