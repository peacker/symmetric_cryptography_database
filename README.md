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
5. Keep existing IDs stable. Add new IDs for new entities rather than renaming published IDs.
6. Run the same checks used by CI:

   ```bash
   make test
   make build-site
   ```

7. Open a pull request that explains the change and its sources. Keep unrelated changes in separate pull requests when practical.

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
