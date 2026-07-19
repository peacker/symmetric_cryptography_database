# Glossary

Precise definitions for every category, taxonomy, and vocabulary term used across this
database and the website built from it: tiers, types, constructions, components, rounds,
target applications, standardization processes, and the curated relations vocabulary.

**This file is a curated, organized *read* of definitions that live as data.** Every
construction, component, and type already carries its own `notes` field in the YAML source
(`data/primitive_constructions.yaml`, `data/mode_constructions.yaml`, `data/components.yaml`,
`data/primitive_types.yaml`, `data/mode_types.yaml`), each with a citation or worked example
where one exists. That YAML is the single source of truth; this file exists to make it
readable in one place without hunting across five files. **If you add or edit a definition,
edit the YAML `notes` field first, then update this file to match** — do not let the two
drift apart.

## Table of contents

- [Tiers: primitive vs. mode](#tiers-primitive-vs-mode)
- [Family vs. instance](#family-vs-instance)
- [Types](#types)
- [Constructions](#constructions)
- [Components](#components)
- [Rounds and the network model](#rounds-and-the-network-model)
- [Target applications](#target-applications)
- [Standardization processes](#standardization-processes)
- [Relations (influence vocabulary)](#relations-influence-vocabulary)

## Tiers: primitive vs. mode

Every family in this database is either a **primitive** (`data/primitive_families.yaml`) or a
**mode** (`data/mode_families.yaml`). This is the most fundamental split in the data model,
mirrored throughout the site (separate filter panels, separate construction/type catalogues,
a dedicated toggle on the Timelines and Genealogy tabs):

- **Primitive — fixed-length, not directly usable on its own.** A permutation, block cipher,
  tweakable block cipher, compression function, or update function: something that transforms
  a *fixed*-size input to a *fixed*-size output (or state), with no standalone notion of
  "encrypt this arbitrary-length message" or "hash this file." Keccak-*f*, AES, and Salsa20's
  core update function are primitives.
- **Mode — variable-length, directly usable as an algorithm.** An AEAD scheme, hash function,
  XOF, MAC, KDF, PBKDF, PRNG, key wrap, or stream cipher: something a caller can hand an
  arbitrary-length input to (or ask for arbitrary-length output from) and get a complete,
  usable cryptographic result. AES-GCM, SHA-3, and Argon2 are modes.

A mode is typically *built on top of* one or more primitives — AES-GCM wraps the AES block
cipher in GCM; SHA3-256 wraps the Keccak-*f* permutation in a sponge — and that relationship
is recorded as a `used_by` influence edge from the mode to the primitive it wraps (see
[Relations](#relations-influence-vocabulary)). Primitive and mode families share one id
space, so an influence edge can freely cross tiers in either direction, but **construction
ids cannot**: the primitive-tier and mode-tier construction catalogues
(`data/primitive_constructions.yaml` / `data/mode_constructions.yaml`) are separate lists, and
`scripts/validate.py` rejects a family that references a construction id from the wrong tier's
catalogue. This has bitten real entries twice in this database's history — BLAKE2 and NORX
were both once modeled only as a single mode-tier family, which meant their underlying ARX/
Boolean-operator permutation had structurally nowhere to be tagged, since that construction
leaf only exists in the primitive-tier catalogue. Both were fixed by splitting into a
primitive-tier permutation/compression-function entry plus a mode-tier entry linked by
`used_by`, mirroring how Ascon (`ascon` + `ascon_aead`/`ascon_hash`/`ascon_xof`) and BLAKE
(`blake` + `blake_hash`) were already modeled. **If a family's underlying permutation/round
function needs a construction tag but the family itself is mode-tier, it needs this same
split**, not an exception to the tier rule.

## Family vs. instance

Within either tier, a **family** is the design as published (SIMON, AES, Ascon) — it carries
the construction tags, components, round definition, references, and influence edges. An
**instance** is one concrete parameterization of that family with fixed sizes (SIMON-64/128,
AES-128, Ascon-128a) — it carries the actual block/key/state/output sizes and round count. A
family always has at least one instance; most families with multiple published size/security
variants (SPECK's many block/key-size combinations, BLAKE2b vs. BLAKE2s) list one instance per
variant rather than forcing an artificial "default" choice.

An **innovative idea** (`innovative_ideas` on a family) records a specific novel technique the
family introduced (e.g. BLAKE2's parameter-block initialization), separately from the
family's influence edges, which record what it took *from* earlier designs rather than what it
contributed itself.

## Types

Every family has exactly one **type**, drawn from a dedicated catalogue — `primitive_types`
for primitive-tier families, `mode_types` for mode-tier families — rather than a bare schema
enum, specifically so each type carries its own citable definition (`data/primitive_types.yaml`,
`data/mode_types.yaml`).

**Primitive types:**

| Type | Definition |
|---|---|
| Block Cipher | A keyed, invertible transform on fixed-size blocks: `E_k` is a permutation of `{0,1}^n` for each key `k`, with a corresponding `D_k = E_k^-1`. |
| Tweakable Block Cipher | A block cipher with a second, public "tweak" input: `E_k(T, x)` is a permutation of `{0,1}^n` for each `(k, T)` pair (Liskov, Rivest, Wagner, CRYPTO 2002). One key cheaply yields many independent permutations without rekeying. |
| Permutation | An unkeyed (or public-parameter-keyed) fixed-size invertible transform used as a building block for a mode, not as a standalone algorithm — e.g. Keccak-*f*, Ascon-*p*. The surrounding mode supplies the key/security, not the permutation alone. |
| Compression Function | A fixed-input, fixed-output transform combining a chaining value with a message block, `h: {0,1}^n x {0,1}^b -> {0,1}^n`, iterated by a hash mode to process arbitrary-length input. |
| Update Function | A fixed-size state-to-state transform named and specified separately from the variable-length algorithm built on top of it — e.g. Salsa20's core update function, turned into a keystream generator by a mode-tier expansion function. |

**Mode types:**

| Type | Definition |
|---|---|
| Stream Cipher | Generates a keystream from a key/nonce and combines it with plaintext (usually by XOR), one bit/byte/word at a time rather than in fixed blocks. |
| AEAD | Authenticated Encryption with Associated Data: confidentiality plus an integrity/authenticity tag in one algorithm, additionally binding unencrypted associated data into that tag (Rogaway, CCS 2002). |
| Hash Function | Variable-length input, fixed-length output, unkeyed, one-way (pre-image/second-preimage/collision resistant); built by iterating a compression function or permutation. |
| XOF (Extendable-Output Function) | Hash-like, but the output length is a caller-chosen parameter rather than fixed (SHAKE128/256, BLAKE3's XOF mode). |
| PBKDF | A key derivation function deliberately made slow and/or memory-hard for deriving a key from a low-entropy password, resisting offline brute-force (PBKDF2, bcrypt, scrypt, Argon2). |
| Encryption Mode (confidentiality-only) | A block-cipher mode providing confidentiality alone with no built-in integrity mechanism (CBC, CFB, OFB) — contrast AEAD. |
| MAC | A keyed function producing a fixed-size tag over a variable-length message for integrity/authenticity verification (HMAC, CBC-MAC, Poly1305, GHASH). |
| PRNG / DRBG | A keyed/seeded algorithm producing output computationally indistinguishable from random, specified as a general-purpose randomness source rather than for encrypting a specific message. |
| KDF | Derives cryptographic keys from initial keying material plus context, without a PBKDF's deliberate cracking-resistance cost (HKDF). |
| Key Wrap | A mode specifically for encrypting/authenticating key material for storage or transport, sometimes deterministic by design (NIST SP 800-38F). |

## Constructions

Every construction catalogue (primitive-tier and mode-tier, in separate files per the tier
rule above) is exactly **two levels deep**: a handful of **root** constructions, each with
zero or more **leaf** constructions naming a specific variant. A family's `construction_ids`
is a list, so it can carry a root alone (generic case), a root + one specific leaf (typical
case), or leaves from multiple *different* roots at once — an orthogonal facet, not a
contradiction (see the SPN facets and the Boolean-Operator Network / Bitslice-Friendly SPN
intersection below). Full methodology for why the taxonomy is shaped this way lives in
[README.md § Construction taxonomy and relations model](README.md#construction-taxonomy-and-relations-model);
this section is the per-term dictionary.

### Primitive-tier roots

**Feistel (`feistel`)** — a structure that updates one half of the state using a round
function of the other half, then swaps the halves' roles.

| Leaf | Definition |
|---|---|
| Balanced (Classical) Feistel | The textbook two-equal-branch Feistel network (DES). |
| Algebraic (Native-Field) Feistel | A Feistel network whose branches are native field elements (GF(p) or GF(2^n)) rather than bit strings, typical of arithmetization-oriented designs. |
| Generalized Feistel Network (GFN) | More than two sub-blocks, unspecified sub-type. |
| Type-1 / Type-2 / Type-3 / Type-4 / Type-5 GFN | The named GFN sub-block permutation patterns from the generalized-Feistel literature (differing in how many branches are updated per round and how the cyclic shift between rounds is arranged). |
| Unbalanced Feistel | Sub-blocks of unequal size, unspecified direction. |
| Unbalanced Numeric / Source-Heavy / Target-Heavy Feistel | Specific unbalanced-Feistel refinements by which side is larger and by how the round function's input/output sizes relate. |
| Alternating Feistel Network / Alternating Numeric Feistel | Successive rounds alternate which sub-block serves as the round-function input vs. the updated side. |
| Nested (Recursive) Feistel Network | A Feistel network whose round function is itself built from a smaller Feistel network. |
| Generalized Unbalanced Feistel Network (GUFN) | Combines GFN's multi-branch structure with unbalanced Feistel's branch-size asymmetry (MacGuffin). |

**SPN (`spn`)** — a round structure combining non-linear substitution layers with permutation
or linear diffusion layers. Two independent facets apply on top of the bare root, and a family
tags at most one leaf per facet (the facets combine freely, e.g. AES is Full-State S-box +
MDS Linear Layer):

| Facet | Leaves |
|---|---|
| S-box coverage | **Full-State S-box Layer** (S-box applied to the whole state) vs. **Partial S-box Layer** (only some words, e.g. LowMC) vs. **Alternating Full/Partial S-box Layer**. |
| Linear-layer type | **Bit-Permutation Linear Layer** (pure wiring, e.g. PRESENT/GIFT) vs. **MDS Matrix Linear Layer** (true MDS matrix over GF(2^n), e.g. AES/SHARK) vs. **Near-MDS / ARX-like Linear Layer** (lighter/XOR-heavy mixing, e.g. FOX/IDEA NXT). |

Two further, independent SPN facets:

- **Tweakable SPN** — an SPN with explicit tweak influence in round processing (BipBip, SCARF).
- **Bitslice-Friendly SPN** — an SPN whose small nonlinear layer is defined directly as a
  small Boolean circuit (a handful of AND/OR/XOR/NOT gates) rather than a table lookup —
  Keccak's chi step, Ascon's/Xoodoo's S-boxes, Gimli's T-function. **Not** for designs whose
  S-box merely *admits* a bitslice implementation via a large derived circuit (AES's
  tower-field S-box needs ~100+ gates and does not qualify). This is the leaf that
  legitimately intersects with the Boolean-Operator Network root below: the same few-gate
  circuit can be — and for Keccak/Ascon/Xoodoo/Gimli, is — tagged from both the S-box-shape
  angle (here) and the operation-level angle (Boolean-Operator Network), because a cipher can
  in principle be *designed* starting from either framing even though these four happen to be
  describable both ways at once.
- **Self-Reciprocal SPN** — an SPN whose overall structure is an involution, or made one via a
  "reflection" construction mirroring rounds around a central layer so decryption reuses the
  encryption circuit (PRINCE/MANTIS/PRINCEv2's reflection-cipher family; 3-Way's
  near-involutive round structure).

**ARX Network (`arx_permutation_network`)** — a round-based structure built primarily from
modular addition, XOR, and fixed or data-dependent rotations. This is the family the user's
"pure ARX" question was about: **ARX = Add + Rotate + XOR**, and this root is deliberately
broad (it covers designs using *any* mix of those three), while its leaves narrow down exactly
which combination:

| Leaf | Definition |
|---|---|
| Fixed-Rotation ARX | Rotation amounts are fixed at design time (Salsa20, ChaCha, Speck). |
| Data-Dependent Rotation ARX | Rotation amount is itself a function of the data (RC5, RC6) — the "pure ARX" reading some literature reserves for genuinely data-dependent designs, as opposed to fixed-rotation ones. |
| XOR Key Injection / Modular-Addition Key Injection | Whether the round key is mixed in via XOR or via modular addition. |
| Constant-Free ARX | No per-round constants at all (BLAKE3, BLAKE2). |
| ARX with Round Constants | Per-round constants are present (BLAKE, Threefish). |
| ARX-based SPN | The Long Trail Strategy: a large, cryptographically strong ARX-box alternated with a linear diffusion layer, with provable differential/linear trail bounds — introduced and named by the SPARX design paper (Dinu, Perrin, Udovenko, Velichkov, Großschädl, Biryukov, ASIACRYPT 2016). |

**Boolean-Operator Network (`boolean_operator_network`)** — a round-based structure whose
nonlinearity and diffusion are built entirely from elementary bitwise Boolean operations
(AND/NAND, OR/NOR, XOR, NOT) combined with fixed/data-dependent rotations, plain shifts, or
bit permutations — no modular addition (that would make it ARX instead) and no table-lookup
S-box whose circuit isn't itself just a handful of these gates. This root replaced a narrower
"AND-RX" category that didn't fit several of its own members: Keccak/Ascon/Xoodoo's chi step
also uses NOT, Gimli's T-function also uses OR, and NORX's G function uses a fixed *shift*
(not a rotation) in place of ChaCha's modular addition.

| Leaf | Definition |
|---|---|
| Pure AND-RX (`pure_and_rx`) | The strict subset: AND is the *only* nonlinear operation, combined with XOR and fixed rotations only — no OR, no NOT beyond incidental linear use, no plain shifts. Simon's and Simeck's round functions are the canonical members. |

Any cipher *could* in principle be designed as a Boolean-operator network (or an ARX network,
or an SPN) — these are descriptions of what a given design's authors actually chose to build
from, not an inherent property forced by the algorithm's function. A handful of families
(Keccak, Ascon, Xoodoo, Gimli) are legitimately tagged with both Boolean-Operator Network
*and* Bitslice-Friendly SPN because their few-gate nonlinear circuit really is describable
both ways; that overlap is intentional, not a modeling inconsistency.

**Other primitive-tier roots**, each a single-level category (no leaves currently defined,
either because too few designs use the exact architecture to warrant splitting, or because no
family in this database is tagged with the leaf-worthy variant yet):

| Root | Definition |
|---|---|
| Lai–Massey Scheme (`lay_massey`) | A two-branch structure where the same mixing function perturbs both halves symmetrically (IDEA). |
| Even–Mansour Construction (`even_mansour`) | A key-alternating construction built around one or more public permutations with key addition before and after each call. |
| Davies–Meyer Construction (`davies_meyer`) | A compression function derived from a block cipher by XORing the block-cipher output with the input chaining value. |
| Matyas–Meyer–Oseas Construction (`matyas_meyer_oseas`) | Closely related to Davies-Meyer, with a different assignment of message and chaining-value roles to the block cipher's key/plaintext inputs. |
| Stream State-Update Generator (`stream_state_update_generator`) | A keystream design based on repeated state updates and output extraction, typically with separate key-scheduling and generation phases. |
| LFSR/NLFSR Register Network (`lfsr_nlfsr_register_network`) | A bit-oriented structure driven by linear/nonlinear feedback-shift-register state transitions and Boolean mixing. |
| Key-Dependent Table Network (`key_dependent_table_network`) | Round behavior driven by key-derived tables or key-dependent substitution/permutation components. |
| Heterogeneous Round Network (`heterogeneous_round_network`) | A block cipher combining distinct round phases and multiple transformation styles within one design. |
| Generalized Triangular Dynamical System / GTDS (`generalized_triangular_dynamical_system`) | A round function over GF(p) combining a triangular system of univariate polynomial permutations with Feistel-like branch feedback (Roy & Steiner; Arion). |

A cluster of classical LFSR/FCSR/NLFSR stream-cipher generator patterns is also cataloged for
completeness even though most currently have **no family tagged with them yet** in this
database (they exist so a future addition — e.g. SNOW, A5/1, the Alternating Step Generator —
has a ready-made, correctly-defined home): Coupled Counter System, Filtered FCSR, Filtered
LFSR, Filtered LFSR with Decimation (whose two real children, **Shrinking Generator** and
**Self-Shrinking Generator**, are already populated), Irregular Clock Register Pair, LFSR over
Extension Field with Memory, NLFSR Combiner, NLFSR/LFSR Filter, NLFSR with Nonlinear Filter,
Table-Driven PRF, and Table-Update Stream. One exception with a real member: **T-Function**
(VMPC) — a design built around a Klimov–Shamir triangular function, where output bit *i*
depends only on input bits `0..i`, guaranteeing invertibility by construction regardless of
which arithmetic/logical operations are combined. Full definitions for all of these are in
`data/primitive_constructions.yaml`.

### Mode-tier roots

| Root | Definition |
|---|---|
| Merkle–Damgård Construction (`merkle_damgard`) | Iterated hashing: a fixed-input compression function applied to successive message blocks while carrying a chaining value, with length-encoding strengthening padding. |
| Sponge Construction (`sponge_construction`) → **Standard Sponge** | Absorbs input into part of a fixed-size state (the rate, alongside an untouched capacity) interleaved with permutation calls, then squeezes output the same way; unkeyed/unidirectional by default. |
| Duplex Mode (`duplex_mode`) → Standard Duplex, MonkeyDuplex, DrySponge, Beetle Mode, Parallel Duplex Construction | Interleaves absorb and squeeze in a single call per operation, enabling stateful keyed processing (AEAD). MonkeyDuplex runs a reduced round count for repeated data-processing calls; DrySponge separates fault-hardening concerns from cryptographic-strength concerns; Beetle replaces direct rate-XOR output with a shuffle-then-XOR step; the Parallel Duplex Construction (NORX) splits payload processing across parallel lanes. |
| Belt-and-Mill Construction (`belt_and_mill_construction`) | Pre-sponge-terminology construction: a small nonlinear "mill" state updated each round, coupled to a much larger linear-feedback "belt" (PANAMA, RadioGatún — the direct architectural precursors to the Keccak sponge). |
| Binary Tree Hash (`binary_tree_hash`) | Splits input into independent leaf blocks combined via a binary tree of the same compression function (BLAKE3), enabling independent, parallel subtree hashing unlike sequential/state-based iteration. |
| Block-Cipher-Based Mode (`block_cipher_based`) → CTR, CBC, OFB, CFB, GCM, Block-Cipher-Based Stream Cipher (Other) | A mode whose mechanism is built by invoking a block cipher as a black box. The "(Other)" leaf is a residual for bespoke stream/keystream generators that reuse a block cipher's internal components without the generic black-box CTR/OFB pattern. |
| Iterated Hash-Based KDF (`iterated_hash_kdf`) | Password/key derivation built by repeatedly invoking a hash function, directly or as the compression step of a memory-hard scratchpad-filling loop (PBKDF2, Argon2, Catena, Lyra2, yescrypt). |
| Modular Squaring KDF (`modular_squaring_kdf`) | Sequential-cost password hashing via repeated `x -> x^2 mod N` for an RSA-style composite modulus (Makwa). |
| HMAC (`hmac_construction`) | A hash-based MAC combining a hash function with inner and outer key padding (RFC 2104). |
| Encrypt-then-MAC Composition (`encrypt_then_mac`) | A generic AEAD composition: encrypt with one primitive, authenticate the result with a separately-keyed MAC/universal hash. |
| Native Keystream Generator (`native_keystream_generator`) | A stream cipher whose keystream comes directly from its own state-update generator, with no separable underlying block cipher wrapped by a generic mode. |
| Filter Permutator (`filter_permutator`) | A Goldreich-PRG-style construction with no register/state update: each output bit reorders secret key bits with a fresh public random permutation, then evaluates a fixed Boolean filter on a subset of them (FLIP, FiLIP — designed to keep FHE noise growth additive rather than multiplicative). |

Deliberately **not** modeled as constructions: `permutation_based_hash` /
`permutation_based_stream` / `memory_hard_sponge` do not exist as ids (a permutation-driven
hash or stream cipher is tagged with whichever real sponge/duplex leaf its mechanism actually
uses; "memory-hard" is a `target_applications`/`notes` fact, not a structural one), and
bcrypt/scrypt-style designs are ordinary families linked to their real predecessor via an
influence edge rather than a construction tag. See
[README.md](README.md#construction-taxonomy-and-relations-model) for the full reasoning.

## Components

`data/components.yaml` catalogues the individual operations a round is built from
(`characteristics.components` on a family, `component_flow` on a round), grouped into eight
categories:

- **Logical** — `and`, `or`, `xor`, `not`: the elementary bitwise gates. AND and OR are the two
  available nonlinear gates over GF(2) (related by De Morgan's law); XOR and NOT are linear/
  affine and supply no nonlinearity on their own, only mixing and symmetry-breaking. Also in
  this category: `absg_decimation` (LILI-128/DECIM's irregular-decimation rule), `boolean_combiner`
  (Achterbahn-style: one function combining one tap from each of several registers),
  `boolean_filter` (Grain-style: one function reading several taps of one register), and
  `compression_function` (a reference to an externally-defined hash compression function used
  as a component, e.g. Argon2's memory-filling permutation being built around BLAKE2b's).
- **Register** — `lfsr` (linear feedback shift register — maximum-length when the feedback
  polynomial is primitive), `nlfsr` (nonlinear feedback, higher algebraic complexity — Grain,
  Trivium), `fcsr` (feedback with carry over the 2-adics, resisting Berlekamp-Massey-style
  algebraic attacks — F-FCSR), `shift_register` (generic, feedback rule unspecified).
- **Substitution** — `sbox` (a non-linear lookup table, tabulated or algebraic, e.g. AES's
  inverse-in-GF(2^8)-plus-affine-map), `inversion_sbox` (the specific `x -> x^-1` map without
  AES's extra affine layer — Jarvis, Vision, SFINKS), `power_map_sbox` (the arithmetization-oriented
  monomial map `x -> x^d` over a large field — MiMC, Rescue, Poseidon), `lookup_table` (a
  larger, sometimes key/state-dependent table — RC4-family designs, WAKE, SEAL),
  `nonlinear_filter` (a nonlinear function reading several state positions of a general
  register/array — WG, Dragon, CryptMT3).
- **Permutation** — `word_permutation` (fixed word rearrangement, e.g. AES's ShiftRows),
  `bit_permutation` (fixed bit rearrangement, e.g. PRESENT's P-layer), `bit_reversal` (the
  specific reversal permutation), `permutation` (generic reference when no more specific type
  applies), `permutation_vector` (a keyed/public pseudorandom permutation drawn fresh per
  output bit — FLIP/FiLIP's Filter Permutator mechanism).
- **Linear layer** — `field_matrix_mul` / `binary_matrix_mul` (matrix multiplication over
  GF(2^n) / GF(2), giving MDS diffusion when the matrix is MDS — AES's MixColumns is the
  binary/field case), `prime_field_matrix_mul` / `cauchy_matrix` (the analogous large-prime-field
  case for arithmetization-oriented designs), `mix_columns` (AES's specific MDS matrix, tagged
  directly when reused verbatim elsewhere — LEX, Cube Cipher), `linear_filter` (a linear
  function reading several state positions, distinct from a nonlinear `boolean_filter` — F-FCSR),
  `linear_transform` (a generic named linear diffusion step that isn't more specifically a
  matrix multiplication or fixed wiring — 3-Way's theta, Kuznyechik's/ZUC's linear layers).
- **Shift/rotation** — `rotation_fixed` / `rotation_variable` (cyclic rotation by a constant /
  data-dependent amount — the "R" in ARX), `shift_fixed` / `shift_variable` (zero-filling
  logical shift, constant / data-dependent amount).
- **Arithmetic** — `add_mod` (modular addition — the "A" in ARX), `sub_mod`, `mul_mod` (IDEA's
  multiplication mod 2^16+1), `counter` (an incrementing register — Rabbit's counter system,
  Leviathan's whitening counter), `t_function` (a Klimov-Shamir triangular function,
  guaranteeing bijectivity by construction — VMPC).
- **Constant** — `constant`: injection of fixed design-time values (round constants, IV/domain
  constants, e.g. Salsa20's "expand 32-byte k") to prevent slide attacks and distinguish
  otherwise-identical rounds.

`special_case_of` links a narrower component to a broader one the same way constructions do
(e.g. `bit_permutation` is a `special_case_of` `word_permutation`; `binary_matrix_mul` is a
`special_case_of` `field_matrix_mul`), so the same two-level parent/child reading applies.

## Rounds and the network model

`data/rounds.yaml` defines the actual step-by-step shape of a family's round, referenced from
a family via `round_ids`. Each round entry has:

- **`kind`** — one of `full_round`, `half_round`, `quarterround`, `step`, or `other`: how much
  of the overall network one round entry represents (a ChaCha quarterround updates 4 of 16
  words; a full_round updates the whole state once).
- **`spec.component_flow`** — the ordered sequence of component ids (from the catalogue above)
  that make up one execution of the round, e.g. Simon's round is
  `rotation_fixed -> and -> xor -> constant`.
- **`spec.state_model`** — the shape of the state the round operates on (bit width, word
  layout, or a small set of supported sizes across a family's instances).
- **`spec.constant_injection`** — how round constants enter (e.g. `z_sequence` for SIMON's
  LFSR-derived constant sequence), when the round uses a `constant` component.

Two families sharing an identical `component_flow` (ignoring parameters) or an identical
`round_hash` (including parameters) is a **queryable fact**, exposed in the Custom Query
Builder tab, rather than a hand-curated relation — see
[README.md § Curated relations vocabulary](README.md#curated-relations-vocabulary) for why
literal component/round/state sharing was deliberately removed from the influence-edge
vocabulary in favor of being retrievable by query.

## Target applications

`target_applications` is a free-text list, not a fixed enum (deliberately — new applications
keep appearing faster than a controlled vocabulary could track them), but the ~57 distinct
values currently in use cluster into a few recognizable groups:

| Group | Values |
|---|---|
| Constrained/embedded hardware | `constrained_hardware`, `embedded`, `iot`, `lightweight`, `lightweight_aead`, `microcontrollers`, `resource_constrained_devices`, `rfid`, `bitslice`, `circuit_depth_constrained`, `ultra_low_latency` |
| General platform | `generic`, `general_purpose`, `software`, `hardware`, `mobile`, `real_time` |
| Cryptographic function/use-case | `aead`, `authenticated_encryption`, `encryption`, `digital_signatures`, `message_authentication`, `keyed_hashing`, `hash`, `key_derivation`, `password_hashing`, `random_number_generation`, `stream_cipher`, `checksums` |
| Networking/protocol context | `tls`, `gsm`, `mobile_networks`, `wireless`, `telecommunications`, `network`, `messaging`, `broadcast` |
| Specialized computation settings | `fhe`, `mpc`, `zero_knowledge`, `side_channel_resistant`, `proof_of_work` |
| Storage/lookup structures | `storage`, `memory_encryption`, `content_addressable_storage`, `data_lookup`, `hash_tables`, `hash_table_dos_protection` |
| Sector/domain | `banking`, `government`, `export_control` |
| Historical/meta | `historical`, `legacy`, `research`, `cryptanalysis`, `backdoor_research`, `short_messages` |

## Standardization processes

`data/processes.yaml` catalogues the 12 standardization bodies/competitions a family can
participate in (AES, NESSIE, CRYPTREC, eSTREAM, SHA-3, CAESAR, the Password Hashing
Competition, the CACR national competition, NIST Lightweight Crypto, NIST SHA-1/SHA-2
standardization, the EU RIPE project, and the Ukrainian national competition), each with a
`start_year`/`end_year`, organizer, and URL. A process is broken into **stages**, each carrying
a `kind`:

| Stage kind | Meaning |
|---|---|
| `phase` | A numbered phase of a multi-round competition (eSTREAM Phase 1/2/3). |
| `round` | A numbered elimination round (SHA-3/AES/NIST-LWC Round 1/2/3). |
| `list` | An unordered inclusion list rather than a ranked elimination stage. |
| `category` | A named track distinguishing candidates by target profile (e.g. hardware vs. software). |
| `portfolio` | The final selected set (eSTREAM's software/hardware portfolios). |
| `outcome` | A terminal result stage (winner, standardized). |
| `other` | Anything not fitting the above. |

A family's `process_participations` records which stage ids it reached and an overall
**status**: `candidate` (submitted and still under evaluation, or eliminated without a more
specific outcome), `finalist`, `winner`, `recommended`, `candidate_recommended`, `monitored`
(cryptanalysis flagged, not eliminated), `special_recognition`, `portfolio` (selected for a
competition's final portfolio without an outright "winner" framing, as in eSTREAM), or
`submitted` (entered but with no further tracked outcome).

## Relations (influence vocabulary)

`influences[].relations` records genuine, citation-backed design lineage between families —
eight tags: `inspired_by`, `related_to`, `variant_of`, `improvement_of`, `generalization_of`,
`specializes`, `used_by`, `standardization_of`. The bar for adding one, what's deliberately
excluded (benchmark comparisons, "positioned against" framing, shared abstract paradigms like
"both ARX" with no concretely reused mechanism), and why two categories of relation
(literal component/round/state sharing, and construction-leaf sharing) were replaced by
queryable/derived facts instead of hand-curated tags, are documented in full in
[README.md § Construction taxonomy and relations model](README.md#construction-taxonomy-and-relations-model) —
not repeated here to avoid the two documents drifting out of sync.
