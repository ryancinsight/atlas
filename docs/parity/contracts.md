# Capability and evidence protocol

Protocol 1 / program 2026-10-26.2. [Program](README.md).

## Domain and equivalence

An obligation is `(reference release, public API identity, semantic variant,
dtype, device, layout, differentiation mode, execution regime, input domain)`.
The source inventory records identities. `capabilities.json` records family
contracts; the exact per-API relation belongs in `mappings.json`. An empty
mapping set means unmapped, even when a family resembles the API. `candidate`
classification is only a search aid and never closes an obligation.

Every mapping names one canonical provider operation and preserves separate
reference variants. Deduplication requires an equivalence argument over the
whole input domain: result, mutation/aliasing, error category, dtype and shape,
ordering, device placement and gradients. Aliases may share a canonical
operation; reference identities and variant tests remain. NumPy promotion,
JAX weak scalars/X64 policy, PyTorch promotion/defaults and TensorFlow cast rules
are separate contracts. Layout/view/copy and scatter duplicate-index semantics,
complex differentiation, NaN/Inf/signed zero, stable sorting, reduction order,
random stream splitting and compiler graph breaks must never be inferred from
matching spelling. Exact Python signatures are not required for functional
equivalence, but observable capabilities and legal parameter cases are.

The implementation follows the existing generic first-party provider graph.
Rust owns computation; Python bindings expose it. No runtime dependency on
NumPy/JAX/PyTorch/TensorFlow/XLA or a consumer-local duplicate substitutes for
Atlas implementation. External frameworks are isolated test/benchmark oracles.
Import/export of their documented formats is a capability, not permission to
adopt their runtime architecture. See [decisions](decisions.md).

## Required coverage axes

| Axis | Required materialization before an API is mapped |
| --- | --- |
| Dtypes | Exact reference-valid set including signed/unsigned integers, bool, floats (half/bfloat/float8 variants where public), complex; structured/subarray/object/string/bytes/datetime/timedelta/resource/variant/quantized types where reference permits them. Record byte order, alignment, casts, promotion and accumulator type. Unsupported Atlas representations are gaps. |
| Shapes | Scalars/rank zero, zero lengths, rank and dimension limits, broadcasting, dynamic/symbolic shapes, ragged/irregular values, parameter validation and overflow. |
| Layout | Contiguous row/column order, transposed/permuted/noncontiguous/negative/zero strides, broadcast views, aliasing/overlap, sparse formats and duplicate entries, masked/ragged/nested/distributed layouts where legal. A reference-invalid combination needs a cited domain rule, not a test skip. |
| Device | CPU architectures and ISA paths; supported WGPU vendors, CUDA/NVIDIA, ROCm/AMD, Metal/Apple and TPU/custom accelerator obligations exposed by each reference. Device acquisition is explicit. Missing hardware is `unavailable`, not pass. |
| Gradients | No derivative with a domain proof where mathematically inapplicable; otherwise forward/JVP, reverse/VJP, gradients of gradients, jacobian/hessian, batched transforms, complex conventions, nondifferentiable/subgradient points, sparse gradients, custom rules, mutation and rematerialization. |
| Execution | Eager, compiled, traced, vectorized, asynchronous, multithreaded, multi-device, multi-process/multi-node, deterministic mode, cancellation/error propagation and effect ordering as applicable. |
| Interoperability | Ownership/lifetimes, zero-copy vs explicit copy, device synchronization/stream handoff, protocol/ABI/format version, endianness and invalid/untrusted-input errors. |
| Errors | Exact valid and invalid domains, shape/dtype/device errors, overflow/underflow/invalid/divide-by-zero policy, unsupported capabilities, resource failures and typed diagnostic context. |

`reference_valid_combinations` is not a materialized matrix. It records work
remaining. A mapping must enumerate its finite equivalence classes, parameter
domains and invalid cases, with a proof that the classes cover the reference
domain. It may then reuse generic tests across dimensions; it must not assume
the full Cartesian product is meaningful or omit legal combinations.

## Analytical, differential and performance evidence

Analytical tests use algebraic identities plus independent known solutions,
boundary values, adjacent representable numbers/ties, singular/ill-conditioned
cases and negative domains. Identity-only tests cannot prove implementation
(an identity transform would pass a round trip); include nontrivial expected
outputs. Property tests cover multiple dimensions with meaningful shrinking.

Differential cases pin oracle package/wheel hashes, release, Python/toolchain,
input corpus/hash, seeds, dtype/device/layout, algorithm flags and execution
mode. Both systems execute the same represented inputs. Exact integer, shape,
index, error-domain and serialization invariants require exact agreement.
Floating bounds derive from conditioning, algorithm and precision (ULP or
forward/backward error with derivation), not tuned epsilon. Randomness requires
either bitstream/sequence equivalence where promised or independently justified
distributional tests plus reproducibility contracts; similar histograms alone
do not establish stream parity. Different reference semantics get separate
variants and expectations; majority vote is not an oracle.

Performance is qualified only after correctness on the same revision/config.
Record matched algorithm, shapes, all dtypes/layouts/devices, warmup/JIT/compile
time, steady-state and end-to-end transfer/synchronization costs, threading,
memory/allocations, statistical uncertainty, power and hardware/driver versions.
Use counterbalanced repeated measurements and a predeclared regression budget
justified by analysis. No universal speedup target is fabricated. Each workload
receives its numeric target and justification before qualification. Baseline
and candidate source hashes, command and raw artifact digest are mandatory.

## Independent states and evidence

Each mapping/coverage record has these independent fields:

| Field | Values and promotion requirement |
| --- | --- |
| `mapping` | `unmapped`, `specified`; specified requires complete semantic variants and coverage classes |
| `implementation` | `unknown`, `absent`, `partial`, `implemented`; implemented requires source symbol/path, exact owner revision and review |
| `tested` | `unrun`, `failed`, `passed`, `unavailable`; passed requires analytical/property/negative/integration results, zero skips and all required classes executed |
| `external` | `unrun`, `failed`, `passed`, `unavailable`; passed requires pinned differential results for each mapped comparator variant |
| `performance` | `unrun`, `failed`, `qualified`, `unavailable`; qualified requires predeclared targets and matched baseline measurements |
| `release` | `unreleased`, `released`; released requires registry receipt, artifact digest and clean fresh-consumer resolution |

Source-audit observations in `provider-evidence.json` are historical, scoped
facts. They do not automatically promote a mapping. A checklist checkmark,
test name, local compilation, another revision's run or job summary whose
cases skip does not establish passed evidence. Test availability and passing
are distinct. Explicit domain-inapplicability requires a cited mathematical
or reference-domain proof; lack of implementation/hardware never qualifies.

`evidence.json` stores records with `id`, `stage`, `owner`, `revision` (40 hex),
`capability`, `mapping_ids`, `command`, `result`, `skipped`, `executed`,
`artifact` (durable HTTPS URL), `sha256`, `environment`, `coverage` and
`review`. All stage promotions cite evidence ids. `executed` is positive,
`skipped` is zero, result is success, and owner/revision must match the mapping.
Performance also records target/baseline and measured comparison; release
also records registry and fresh-consumer artifacts. Evidence is immutable;
corrections append superseding records. Every rebase/integration invalidates
qualification until applicable gates are rerun on the resulting exact head.

The qualification ledger accepts successful promotion records only. Failed,
skipped and unavailable run observations remain in source/run audits and the
independent status fields; none can be cited as successful promotion evidence.

Repository exits have a separate `repository-evidence.json` ledger. Every
record binds a repository's selected exact candidate to its required executed
gate set, commands, environments, artifact digests and independent review.
Changing `status` to `qualified` without that record fails validation. Safety
applicability records cite the reviewed domain proof for any mathematically
inapplicable fuzz/Miri/Loom gate; unavailable execution cannot become such a
proof. Atlas's own final-head exits and final program/release reviews arrive as
external post-commit evidence so the candidate cannot contain a self-referential
Git hash. The CLI requires an external `--review-evidence` JSON naming
`candidate_revision` and carrying `definition_review`, `release_review` (for
release) and applicable `repository_evidence` records. Reviews use the schema
above. Its `qualify` mode also requires a clean candidate and verifies every
consumed program/reference/ledger/tool input against the committed Git blob,
including ignored alternate roots. Normal Git clean-filter normalization is
respected; narrow LF attributes preserve raw inventory SHA-256 across hosts.
Structural validation checks supplied evidence; independent review must still
verify that remote artifacts and claimed numerical proofs establish the result.

## Definition of done

A capability is done only when every reference identity assigned to it has
complete semantic mappings, every required coverage class passes all applicable
stages, provider and consumer revisions are coherent, documentation and bindings
agree, independent review has no unresolved findings, and package release plus
fresh-consumer verification succeeds. A family label cannot close API rows.
The definition milestone additionally requires independently checked extraction
of the entire documented surface and reconciliation of external namespaces,
guides, extension APIs and version mismatches. Unknown extraction gaps block
that milestone. Full 1.0 additionally requires all open scope decisions resolved
without quietly removing requested capabilities, all cross-repo gates and
required human/CI approvals. No version bump substitutes for this evidence.
