# NGCC 2026 cryptographic hash competition — Round 1 reference implementations

Reference (non-optimized) implementations for the 35 candidates accepted into Round 1 of the
Institute of Commercial Cryptography Standards (ICCS/NICCS) "next-generation cryptographic hash
algorithm" competition, announced 2026-09-20. Each subdirectory is the `Reference_Implementation`
folder taken verbatim from that candidate's official submission package published at
<https://www.niccs.org.cn/niccs/Round1Submissions4/pc/list.html>; optimized/SIMD implementations,
test-vector files, and benchmarking harnesses from the same packages are not mirrored here.

This is source code, not curated data — the structured facts about each design (construction,
round function, instances, influences) live in `data/primitive_families.yaml` and
`data/mode_families.yaml`, cited back to these files via each family's `reference_ids`. See
`data/references.yaml` for the corresponding NICCS candidate-page citations
(`niccs_2026_<slug>`), and `references/` for locally archived copies of each candidate's
specification PDF.

Each submission's own license/IP declaration is included in its official package's
`Intellectual property` folder (not mirrored here); consult the original ZIP, linked from the
corresponding `niccs_2026_<slug>` reference entry, for licensing terms before reusing any of this
code.
