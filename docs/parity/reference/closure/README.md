# Source closure and semantic definition slice

Program 2026-10-26.3. [Frozen index](index.json). These are versioned source
audits, candidate relations and partial semantic specifications. The four
original inventory files remain byte-identical. No source table, alias, test
specification or inherited name establishes implemented/runtime parity.

| Scope | Finite result | Remaining obligation |
| --- | --- | --- |
| NumPy 2.5.4 | Every original 65 gap payload retained and dispositioned: 44 empty explicit selections, eight `no-members`, five no-default expansion, two literal-export expansions and six source/owner qualifications. Add 23 source-bound export candidates. | 4,335 inherited/stub/native member and 133 ufunc/alias records remain source candidates; public/generated/ABI/prose scope is not exhausted. |
| JAX 0.12.0.1 | All 119 gap payloads retained: 90 false-positive member-expansion gaps resolved; five requested class-member sets have resolved source bindings; 24 cases remain partial. | The five sets still need rendered-member selection review; `Compiled.__call__` has no docstring and several attributes retain selection questions. All 22 resolved identities are **source-requested candidates**, not proven rendered APIs. 544 namespace spellings absent from the base inventory remain candidates; tables overlap. |
| PyTorch 2.14.1 | `2.14` header is intentional release configuration; 408 documentation blobs and 2,585 native schemas match the patch baseline. Retain 1,020 docstring bindings and 75 typed alias relations. | Five patch commits change real numerical/device behavior. Published build provenance, 27 absent bindings, 58 conditional generated names, native/generated C++ headers and broader companion scope remain open. Equal schemas never prove equal values. |
| TensorFlow 2.21.0 / Keras 3.15.1 | Retain 1,210 declaration-view groups and 6,030 spelling-only pairs, including 188 differing signatures. Retain 252 missing source-export endpoints and 11,207 Keras member candidates, including 9,389 inherited. | Public/build inclusion, runtime generation, external inheritance, 14 Keras saving importability cases, legacy companions and live-documentation reconciliation remain unresolved. None of these relation kinds authorizes semantic merging. |

Counts above describe different, overlapping source sets. Do not add them to
produce a capability denominator. The live report separates admitted candidate
identities from retained source-candidate tables. Unsupported, deprecated,
experimental and legacy candidates are not silently excluded.

Capture-manifest fields preserve their audit-stage wording.
This index and the conservative canonical supplements govern integration:
in particular, JAX's raw `review-ready-additions` label is not accepted as proof
of rendered/public selection. [NumPy's official 2.5.0 mirror](numpy/mirror-provenance.json)
is supplemental. Source comparison finds changed stubs, initializers and
generator/native inputs; its inventory cannot be relabelled 2.5.4.

The source work produces 36 partial constructor workflow mappings covering 58
declaration views. NumPy `size` adds one partial mapping; its native count product
has an explicit `npy_intp` compiler/ABI definedness question. Only NumPy `ndim`
and `shape` are source-specified after independent compositional review. Their
native dtype/layout independence applies to actual built-in getter execution;
overridden subtype getters and opaque outputs retain separate identity/AD and
error behavior. Exact coercion/protocol composition remains a prerequisite.
Every implementation, test, external, performance and release state remains
unknown/unrun/unreleased. Source analytical checks are not differential runs.

NumPy special lookup behavior is specified by execution phase, not exception
category: type-object lookup failure is consumed where the reference does so;
subsequent invocation, metadata and coercion phases retain their own rules.
The [policy decision](../../decisions.md#dec-010--leto) adds no callbacks,
failures or exception-lifetime changes and grants no provider architecture
approval. Low-level dispatch is an acyclic Leto capability before constructors
and metadata; buffer/DLPack interchange remains a separate later contract.

Reproduce bounded source audits in an external cache, without framework imports:

```sh
python3 scripts/parity/closure/reproduce.py numpy
python3 scripts/parity/closure/reproduce.py jax
python3 scripts/parity/closure/reproduce.py torch
python3 scripts/parity/closure/reproduce.py tf
```

The default is cached/offline. `--fetch` permits missing exact-revision source
downloads; `--work` selects an isolated output/cache directory and JAX additionally
accepts `--source-cache`. Original source bytes remain outside Git; source
paths, commit identities, Git blob IDs and SHA-256 are retained here. Source
tree inputs must match the exact frozen tree identity, including existing and
legacy caches. NumPy's metadata witness producer reruns its source assertions;
seeding a captured witness JSON never counts as reproducing those assertions.
Regenerated semantic/source tables match the captured bytes on the verified cache. Capture
manifests also record research-script hashes; code-format/portability changes
can change those generator hashes without changing source facts. Normal CI
checks frozen artifacts, identities, gap accounting and relation distinctions;
cached source checks remain separately scoped evidence. No reference runtime
installation, compiler build, device test or deployment runs in this slice.
