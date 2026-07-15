# Symmetric Cryptography Database

A structured, version-controlled database for fixed-input/output-size symmetric primitives and their ecosystem metadata.

**Website:** <https://peacker.github.io/symmetric_cryptography_database/>

## Scope

This repository tracks symmetric primitives:

- block ciphers
- tweakable block ciphers
- permutations
- compression functions
- update functions
- stream ciphers
- authenticated encryption with associated data (AEAD)
- hash functions

Each primitive can store:

- year of publication
- references (papers, standards)
- standardization processes/competitions
- target applications (IoT, memory encryption, generic, etc.)
- primitive type
- core characteristics (input/output size, key/tweak size, rounds, operations/components)
- influence links to previous designs (historical/design lineage)

## Repository layout

- `data/`: source-of-truth YAML datasets
- `schema/`: JSON schema for validation
- `scripts/`: validation, SQLite build, and visualization exports
- `build/`: generated artifacts (`db`, static site, CSV and PNG exports)

## Data model strategy

Use human-editable YAML as source of truth, and generate a machine-friendly SQLite database for querying and visualization.

Why this hybrid works:

- easy human curation in PRs
- deterministic generated database artifact
- SQL-friendly for dashboards and analysis
- straightforward export to graph/timeline tools

## Construction taxonomy and relations model

This section documents how constructions and relations are organized, so the reasoning behind
the current shape of `data/primitive_constructions.yaml`, `data/mode_constructions.yaml`, and
the `influences[].relations` vocabulary survives beyond the pull request that introduced it.

### Two-level construction taxonomy

Every construction catalogue (primitive-tier and mode-tier) is exactly **two levels deep**: a
handful of root constructions (e.g. `feistel`, `spn`, `sponge_construction`, `duplex_mode`,
`block_cipher_based`), each with zero or more level-2 leaves that name a specific variant of
that root. A family's `construction_ids` is a list, so it can carry a root tag alone (generic/
unclear case), a root + one specific leaf (typical case), or multiple leaves from *different*
roots at once (an orthogonal facet — see below).

This is enforced structurally, not with a dedicated schema field: constructions reuse the same
`special_case_of` pointer already used by `components.yaml`, and `scripts/validate.py` rejects
any construction whose `special_case_of` parent itself has a `special_case_of` — i.e. a chain
longer than root → leaf is a validation error. When a new variant doesn't fit any existing leaf,
add a new leaf under the appropriate root rather than nesting a leaf under a leaf.

Representative trees (see the YAML files for the authoritative, evolving full list):

- **Feistel** (`feistel`) → `balanced_feistel`, `generalized_feistel` (unspecified-type GFN),
  `type1_generalized_feistel` … `type5_generalized_feistel`, `unbalanced_feistel` and its
  `unbalanced_numeric_feistel` / `source_heavy_unbalanced_feistel` /
  `target_heavy_unbalanced_feistel` refinements, `alternating_feistel_network` /
  `alternating_numeric_feistel`, `nested_feistel_network`, `gufn`.
- **SPN** (`spn`) → two independent facets rather than one flat list of styles:
  - S-box coverage: `full_sbox_layer` (S-box applied to the whole state) vs. `partial_sbox_layer`
    (S-box applied to only some words, e.g. LowMC — smaller hardware area or targeted algebraic
    hardness).
  - Linear-layer type: `bit_permutation_linear_layer` (pure wiring, e.g. PRESENT/GIFT),
    `mds_linear_layer` (true MDS matrix over GF(2^n), e.g. AES/SHARK), `near_mds_arx_linear_layer`
    (lighter matrix or XOR-heavy mixing, e.g. FOX/IDEA NXT/PRINCE/Midori).
  - A family tags at most one leaf per facet, and the two facets combine freely (e.g. AES is
    `full_sbox_layer` + `mds_linear_layer`).
  - `tweakable_spn` is a third, independent facet: it can co-occur with a leaf from each of the
    other two facets and simply marks that the primitive takes a tweak.
- **Sponge** (`sponge_construction`) → `standard_sponge`, plus any absorption/squeeze variant
  literature review turns up as the catalogue grows.
- **Duplex** (`duplex_mode`) → `standard_duplex`, `monkey_duplex` (MonkeyDuplex, reduced-rate
  keyed permutation calls between duplex calls), `dry_sponge_duplex` (DrySponge), `beetle_mode`
  (Beetle, small-state lightweight duplex).
- **Belt-and-mill** (`belt_and_mill_construction`) — no leaves yet: a separate root (not a sponge/
  duplex leaf) for pre-sponge-terminology designs like PANAMA/RadioGatún that use a belt-and-mill
  structure rather than a single permutation state.
- **Block-cipher-based mode** (`block_cipher_based`) → `ctr_mode`, `cbc_mode`, `ofb_mode`,
  `cfb_mode`, `gcm_mode`, and `block_cipher_based_stream` as the residual leaf for anything that
  doesn't cleanly match a named NIST mode.

Some things that look like constructions are deliberately **not** modeled as one:

- `permutation_based_hash` / `permutation_based_stream` / `memory_hard_sponge` do not exist as
  construction ids. A permutation-driven hash or stream cipher is tagged with whichever real
  sponge/duplex root + leaf its actual mechanism uses; "memory-hard" or "PBKDF"-ness is a
  functional property recorded in `target_applications` / `notes`, not a structural one.
- bcrypt/scrypt-style designs are not a construction at all — they are ordinary families (see
  `bcrypt`/`scrypt` in `data/mode_families.yaml`) linked to their real structural predecessor via
  an `influences` edge (e.g. bcrypt → Blowfish is `variant_of`; scrypt → Salsa20 is `used_by`).

### Curated relations vocabulary

`influences[].relations` is intentionally short — eight tags, each requiring a citation-backed
`note`: `inspired_by`, `related_to`, `variant_of`, `improvement_of`, `generalization_of`,
`specializes` (the inverse of `generalization_of` — "this design is a narrower/more specific case
of the source's", deliberately *not* named `special_case_of` since that name is already the
construction/component parent-pointer field above and means something unrelated), `used_by`
(a mode built directly on the primitive/mode it wraps), and `standardization_of` (see the
`[authority]` family-naming convention in Contributing below).

The bar for adding a curated edge is unchanged from the existing methodology in
[Contributing](#contributing): a concretely reused/adapted component, explicit "based on"/
"derived from"/"generalizes" language about the design itself, or literal same-team continuation —
never a shared abstract paradigm, benchmark comparison, or "positioned against" framing alone.

Two categories of relation were deliberately removed from this vocabulary because they are
*derivable*, not curated facts, and hand-tagging them invites drift:

- **Literal component/round/state sharing** (formerly `same_sbox`, `same_mix_column`,
  `same_round_function`, `same_state_layout`, and their `similar_*`/`same_round_constants`/
  `same_key_schedule` counterparts) is **not tracked as a relation at all** — it is retrieved with
  a database query instead, as long as components, rounds, and state shape are tracked as
  properties of the primitive. Concretely: `family_components` links every family to the
  component ids it uses; `rounds.round_hash` (exact match, whole round spec including params),
  `rounds.component_flow_signature` (component-id sequence only, ignoring params — a coarser
  match), and `rounds.state_model_json` (raw state-shape JSON) let two families be compared
  structurally. The Custom Query Builder tab exposes all of these as columns
  (`family.component_ids`, `family.component_names`, `family.round_hashes`,
  `family.round_component_flow_signatures`, `family.round_state_models`) plus dedicated
  "Component id/name contains" and "Round component-flow signature contains" filters, so "which
  families share this S-box / this round structure" is answered by filtering or sorting, not by
  a maintained tag that can silently go stale as components.yaml evolves.
- **Construction-leaf sharing** (e.g. "both Type-2 GFN") *is* surfaced, but as a **derived
  relation**, computed at build time rather than hand-curated: for every level-2 construction
  leaf, `scripts/common.py:compute_construction_sharing_edges` chronologically chains every
  family tagged with that leaf (each family links only to its nearest earlier neighbor sharing
  the leaf, not a fully-connected graph, to avoid an O(n²) blowup on popular leaves like
  `balanced_feistel`), directional older → newer. These live in their own SQLite table,
  `construction_sharing_edges` — kept separate from `family_influences` so a computed fact is
  never mistaken for an authored, citation-backed one. On the Genealogy tab these edges are
  folded into the same graph as curated influences, tagged with a synthetic `shares_construction`
  relation, and are independently toggleable via their own "Derived: shares a specific
  construction type" filter group, alongside the curated relation groups.

## Quick start

1. Create a virtual environment and install dependencies.
2. Validate the datasets.
3. Build the SQLite database and static site.

```bash
make setup && make all
```

On Apple Silicon, `make setup` deliberately prefers the native Python from
`/opt/homebrew` (when installed), then Apple's `/usr/bin/python3`. It also
recreates a copied Intel virtual environment automatically; Python virtual
environments are machine-specific and should not be migrated between Macs.
To select another native Python explicitly, run
`make setup BOOTSTRAP_PYTHON=/path/to/python3`.

Or step by step:

```bash
make setup        # creates .venv and installs requirements.txt
make validate     # checks all YAML files against their schemas
make build-db     # generates build/symmetric_primitives.db from YAML
make export-viz   # generates CSVs and PNGs in build/viz/
make build-site   # generates the static site in build/site/
```

The static site is generated in `build/site/`.

### Static site preview

```bash
make serve
```

Then open http://localhost:8000/ in your browser.

## GitHub Pages auto-deploy

This repository is configured to publish a static dashboard to GitHub Pages whenever changes are pushed to `main` or `master`. The public repository currently uses `main` as its default branch.

- workflow: `.github/workflows/pages.yml`
- build command: `make build-site`
- published artifact directory: `build/site/`

One-time GitHub setup:

1. Go to repository settings.
2. Open **Pages**.
3. Set source to **GitHub Actions**.

After that, every push to `main` or `master` will validate the data, build the site, and deploy the result. The published site is available at <https://peacker.github.io/symmetric_cryptography_database/>.

## Contributing

Contributions that improve the coverage, accuracy, provenance, schemas, tooling, or website are welcome.

1. Fork the repository and create a focused branch from `main`.
2. Run `make setup` to create the virtual environment and install dependencies.
3. Edit the source YAML in `data/` and update the matching schema in `schema/` when the data model changes.
4. Cite a reliable primary source in `data/references.yaml` for factual claims. Add influence links only when the relationship is explicitly supported by a source.

   An influence edge (`influences[].source_family_id`) records genuine design lineage, not
   general co-occurrence in a paper. Only add one when the source states a concretely reused
   or adapted component (S-box, key schedule, round function, permutation, whitening
   construction, round constants, etc.), explicit "based on"/"derived from"/"inspired by"/
   "generalizes"/"extends" language about the design itself, or literal same-team continuation
   of an earlier design. Do **not** record an influence, even if the source discusses it at
   length, for:
   - a pure performance/benchmark comparison ("we compare cycle count to X", "X is a
     reference point", "faster than X");
   - "positioned against"/"contrasted with"/"designed to avoid a weakness of X" framing where
     nothing is adopted;
   - shared target application or use case ("also lightweight", "also NIST LWC round 1");
   - a shared abstract paradigm with no concretely borrowed mechanism (e.g. "both ARX", "both
     Feistel", "both sponge-based") — this applies even when the source self-categorizes this
     way. For sponge/duplex designs specifically: if only the abstract Absorb/Squeeze paradigm
     is borrowed (not a concrete permutation), add `sponge_construction` to the family's
     `construction_ids` instead of inventing an influence edge to whichever cipher popularized
     sponges;
   - a related-work listing that merely enumerates several earlier designs sharing a generic
     technique, without singling one out as the actual adopted basis;
   - anything the source states was developed independently.

   When a real predecessor has no family entry yet, add it properly (family, round, primitive,
   and reference entries) rather than pointing the influence at an approximate or unrelated id,
   or dropping a well-documented lineage claim. When unsure, omit the edge — a missed influence
   is far cheaper to add later than a fabricated one is to catch.
5. Keep existing IDs stable. Add new IDs for new entities rather than renaming published IDs.
6. When a later document standardizes an existing design, preserve the original family
   and add a separate `<name> [authority]` family (for example `LEA [ISO]`) whose only
   provenance is the standard. Link it to the original with `standardization_of` and
   attach the standardized primitive profiles to that family. This creates a separate,
   bold standardization milestone without retroactively marking the original publication
   as a standard.
7. Run the same checks used by CI:

   ```bash
   make test
   make build-site
   ```

8. Open a pull request that explains the change and its sources. Keep unrelated changes in separate pull requests when practical.

Generated files under `build/` are ignored and should not be committed. Before submitting, confirm that validation and the process-alignment test pass and that the generated site opens correctly.

## Makefile targets

| Target | Description |
|--------|-------------|
| `make setup` | Create `.venv` and install `requirements.txt` |
| `make validate` | Validate all YAML datasets against schemas |
| `make build-db` | Build SQLite database from YAML |
| `make export-viz` | Export CSV and PNG visualization files to `build/viz/` |
| `make visualize` | Regenerate charts from existing CSV exports |
| `make build-site` | Build static site to `build/site/` (runs build-db + export-viz first) |
| `make serve` | Build site and serve it at http://localhost:8000/ |
| `make all` | Run validate + build-db + export-viz + visualize + build-site |
| `make clean` | Delete the `build/` directory |

## Governance and maintenance

Recommended process:

1. One primitive change per pull request when possible.
2. Require `make validate` and `make build-db` in CI.
3. Enforce stable IDs (never rename IDs, only deprecate).
4. Track provenance in `references.yaml` for every factual claim.
5. Add explicit influence links only when a credible citation exists.

### Suggested review checklist

- Is each new primitive mapped to at least one publication?
- Are sizes/round counts explicit and unit-consistent?
- Is the primitive type selected from the allowed enum?
- Are influence claims backed by notes/citations?
- Does `make validate` pass?

## Visualization ideas

Generated CSV files in `build/viz/` can feed:

- timeline plot: primitives by publication year and type
- sankey/flow plot: process -> primitive -> standard
- network graph: influence edges between primitives
- bubble chart: block size vs key size colored by type

## Next-stage extension

When you move to variable-size modes, add a `mode` entity and a relation table `mode_uses_primitive`, while keeping primitive records independent.

## Similar projects

`cryptospecs` was a collection of specifications and implementations of block ciphers, stream ciphers, hash functions, and a few asymmetric ciphers. Its original [Google Code website](https://code.google.com/archive/p/cryptospecs/) is archived, and the project remains available in the [cryptospecs GitHub repository](https://github.com/stamparm/cryptospecs/tree/master).
