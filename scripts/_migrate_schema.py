#!/usr/bin/env python3
"""One-off migration: split families.yaml/primitives.yaml/modes.yaml/constructions.yaml/
primitive_types.yaml into the new primitive_* / mode_* schema.

Run once from repo root: python scripts/_migrate_schema.py
Safe to delete after the migration has been committed.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

# ---------------------------------------------------------------------------
# Classification tables
# ---------------------------------------------------------------------------

# primitive_type ids (from the OLD primitive_types.yaml / primitives.yaml) that
# represent fixed-length primitives with no direct standalone cryptographic use.
FIXED_PRIMITIVE_TYPES = {
    "permutation",
    "block_cipher",
    "tweakable_block_cipher",
    "compression_function",
    "update_function",
}

# Everything else in the old primitive_types.yaml is actually a variable-length,
# directly-usable mode. Renamed to match the vocabulary the user asked for.
MODE_TYPE_RENAME = {
    "hash_function": "hash",
    "extendable_output_function": "xof",
    "aead": "aead",
    "pbkdf": "pbkdf",
    "stream_cipher": "stream_cipher",
}

# A handful of instances were previously tagged stream_cipher because they were
# retrofitted as siblings of their own AEAD mode, but they are actually fixed
# "core" state-update functions with no standalone use. Reclassify them (which
# moves their whole family from mode-tier to primitive-tier).
INSTANCE_TYPE_OVERRIDE = {
    "bleep64_core": "update_function",
    "clae_core": "update_function",
    "fountain_core": "update_function",
    "quartet_core": "update_function",
}

# modes.yaml's mode_type -> new unified mode_types id
OLD_MODE_TYPE_RENAME = {
    "AEAD": "aead",
    "ENC": "enc",
    "MAC": "mac",
    "PBKDF": "pbkdf",
    "PRNG": "prng",
}

# Additional mode_types the user wants catalogued even with zero current instances.
EXTRA_EMPTY_MODE_TYPES = ["kdf", "keywrap"]

MODE_TYPE_CATALOG = {
    "aead": "Authenticated Encryption with Associated Data (AEAD)",
    "hash": "Hash Function",
    "xof": "Extendable-Output Function (XOF)",
    "pbkdf": "Password-Based Key Derivation Function (PBKDF / Memory-Hard Function)",
    "stream_cipher": "Stream Cipher",
    "enc": "Encryption Mode (confidentiality-only)",
    "mac": "Message Authentication Code (MAC)",
    "prng": "Pseudorandom Number Generator (PRNG/DRBG)",
    "kdf": "Key Derivation Function (KDF)",
    "keywrap": "Key Wrap",
}

PRIMITIVE_TYPE_CATALOG_NOTES = {
    "permutation": None,
    "block_cipher": None,
    "tweakable_block_cipher": None,
    "compression_function": None,
    "update_function": None,
}

# construction_ids classification: "primitive" (fixed) vs "mode" (variable)
CONSTRUCTION_TIER = {
    "spn": "primitive",
    "aligned_spn": "primitive",
    "bit_based_spn": "primitive",
    "feistel": "primitive",
    "generalized_feistel": "primitive",
    "lay_massey": "primitive",
    "even_mansour": "primitive",
    "davies_meyer": "primitive",
    "matyas_meyer_oseas": "primitive",
    "arx_permutation_network": "primitive",
    "stream_state_update_generator": "primitive",
    "lfsr_nlfsr_register_network": "primitive",
    "key_dependent_table_network": "primitive",
    "heterogeneous_round_network": "primitive",
    "tweakable_spn": "primitive",
    "sponge_permutation": "primitive",
    "filtered_fcsr": "primitive",
    "filtered_lfsr": "primitive",
    "filtered_lfsr_with_decimation": "primitive",
    "shrinking_generator": "primitive",
    "self_shrinking_generator": "primitive",
    "gufn": "primitive",
    "irregular_clock_register_pair": "primitive",
    "lfsr_over_extension_field_with_memory": "primitive",
    "nlfsr_combiner": "primitive",
    "nlfsr_lfsr_filter": "primitive",
    "self_reciprocal_spn": "primitive",
    "t_function": "primitive",
    "table_update_stream": "primitive",
    "nlfsr_filtered": "primitive",
    "table_driven_prf": "primitive",
    "coupled_counter_system": "primitive",
    # variable / mode
    "merkle_damgard": "mode",
    "duplex_mode": "mode",
    "permutation_based_hash": "mode",
    "permutation_based_stream": "mode",
    "sponge_construction": "mode",
    "block_cipher_based_stream": "mode",
    "memory_hard_sponge": "mode",
    "iterated_hash_kdf": "mode",
    "bcrypt_variant": "mode",
    "scrypt_variant": "mode",
    "modular_squaring_kdf": "mode",
}

# Families whose compression-function-level construction_ids incorrectly said
# "merkle_damgard" (that's the iteration/mode-level tag). Fix at the primitive
# level; the mode-level (*_hash) sibling gets merkle_damgard instead.
PRIMITIVE_CONSTRUCTION_FIXUP = {
    "md4": ["davies_meyer"],
    "md5": ["davies_meyer"],
    "haval": ["davies_meyer"],
}
# *_hash sibling families (mode tier) that should carry merkle_damgard as their
# iteration construction, replacing whatever fixed-tier tag they inherited.
MODE_HASH_FAMILIES_USE_MERKLE_DAMGARD = {
    "md4_hash", "md5_hash", "sha0_hash", "sha1_hash", "sha2_hash",
    "ripemd_hash", "tiger_hash", "whirlpool_hash", "haval_hash",
    "blake_hash", "groestl_hash",
}

# New mode_construction catalog entries needed for the legacy modes.yaml families,
# plus one generic catch-all for native (non-block-cipher-based) stream ciphers
# whose internal generator construction is now a primitive-tier tag.
NEW_MODE_CONSTRUCTIONS = [
    {"id": "gcm", "name": "Galois/Counter Mode (GCM)",
     "notes": "A block-cipher AEAD mode combining CTR-mode encryption with a GHASH "
              "polynomial-evaluation MAC over GF(2^128)."},
    {"id": "cbc_construction", "name": "Cipher Block Chaining (CBC)",
     "notes": "A block-cipher confidentiality mode where each plaintext block is XORed "
              "with the previous ciphertext block before encryption."},
    {"id": "hmac_construction", "name": "HMAC",
     "notes": "A hash-based MAC construction combining a hash function with inner and "
              "outer key padding (RFC 2104)."},
    {"id": "encrypt_then_mac", "name": "Encrypt-then-MAC Composition",
     "notes": "A generic AEAD composition that encrypts the plaintext with one primitive "
              "and authenticates the result with a separately-keyed MAC/universal hash."},
    {"id": "native_keystream_generator", "name": "Native Keystream Generator",
     "notes": "A stream cipher whose keystream is produced directly by its own internal "
              "state-update generator, with no separable underlying block cipher wrapped "
              "by a generic mode of operation."},
]

# Heuristic fallback: when a mode family's construction_ids became empty purely
# because its only tag(s) were the primitive-tier "sponge_permutation" (i.e. it
# is a sponge/duplex construction over some permutation), retag it with the
# matching mode-tier construction based on instance type. Native stream ciphers
# with no sponge ancestry get the generic native_keystream_generator tag.
SPONGE_DESCENDANT_MODE_CONSTRUCTION = {
    "aead": "duplex_mode",
    "hash": "permutation_based_hash",
    "xof": "sponge_construction",
    "stream_cipher": "permutation_based_stream",
}
# modes.yaml id -> assigned mode_construction id(s)
LEGACY_MODE_CONSTRUCTION_IDS = {
    "bmgl": ["block_cipher_based_stream"],
    "gcm": ["gcm"],
    "chacha20_poly1305": ["encrypt_then_mac"],
    "cbc": ["cbc_construction"],
    "ctr": ["block_cipher_based_stream"],
    "hmac_sha256": ["hmac_construction"],
    "pbkdf2": ["iterated_hash_kdf"],
}
# A couple of pre-existing families mix a fixed-length "core" primitive with its
# own directly-usable stream-cipher mode (the same bug class fixed everywhere
# else in this database, just not previously caught since "update_function" vs
# "stream_cipher" wasn't a distinction that existed before this refactor).
MANUAL_FAMILY_SPLITS = {
    "chacha": {
        "mode_family_id": "chacha_stream",
        "mode_family_name": "ChaCha",
        "mode_instance_ids": {"chacha20"},
        "construction_id": "native_keystream_generator",
        "influence_note": "ChaCha20 is the stream-cipher mode built directly on the ChaCha20 Block Function, "
                           "reusing its round function and state layout unchanged.",
    },
    "kasumi": {
        "mode_family_id": "kasumi_stream",
        "mode_family_name": "A5/3 / A5/4",
        "mode_instance_ids": {"a5_3_gsm", "a5_4_gsm"},
        "construction_id": "block_cipher_based_stream",
        "influence_note": "A5/3 and A5/4 are GSM/UMTS keystream-generator modes built directly on the "
                           "unmodified KASUMI block cipher.",
    },
}

# modes.yaml id -> (new family id, new family display name) rename for the ones
# that were named after the generic construction rather than the specific pairing.
LEGACY_MODE_FAMILY_RENAME = {
    "gcm": ("aes_gcm", "AES-GCM"),
    "cbc": ("aes_cbc", "AES-CBC"),
    "ctr": ("aes_ctr", "AES-CTR"),
}
# Fix pre-existing data bugs: these two legacy modes.yaml entries pointed at
# rijndael_128_128 (copy-paste artifact) when they are actually hash-based.
LEGACY_UNDERLYING_PRIMITIVE_FIXUP = {
    "hmac_sha256": ["sha256_v1"],
    "pbkdf2": ["sha256_v1"],
}


def load_yaml(name: str) -> dict:
    with (DATA_DIR / name).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    families_doc = load_yaml("families.yaml")
    primitives_doc = load_yaml("primitives.yaml")
    modes_doc = load_yaml("modes.yaml")
    constructions_doc = load_yaml("constructions.yaml")
    primitive_types_doc = load_yaml("primitive_types.yaml")

    old_type_ids = {t["id"] for t in primitive_types_doc["primitive_types"]}
    assert old_type_ids == FIXED_PRIMITIVE_TYPES | set(MODE_TYPE_RENAME), (
        f"primitive_types.yaml ids changed since classification was written: {old_type_ids}"
    )

    old_construction_ids = {c["id"] for c in constructions_doc["constructions"]}
    unclassified = old_construction_ids - set(CONSTRUCTION_TIER)
    assert not unclassified, f"Unclassified construction ids: {sorted(unclassified)}"
    extra = set(CONSTRUCTION_TIER) - old_construction_ids
    assert not extra, f"CONSTRUCTION_TIER has stale ids not in constructions.yaml: {sorted(extra)}"

    # ---- group primitives.yaml rows by family_id ------------------------------
    instances_by_family: dict[str, list[dict]] = {}
    for prim in primitives_doc["primitives"]:
        instances_by_family.setdefault(prim["family_id"], []).append(prim)

    def instance_type(prim: dict) -> str:
        return INSTANCE_TYPE_OVERRIDE.get(prim["id"], prim["primitive_type"])

    def to_instance(prim: dict, is_mode: bool) -> dict:
        out = {"id": prim["id"], "name": prim["name"]}
        t = instance_type(prim)
        out["type"] = MODE_TYPE_RENAME.get(t, t) if is_mode else t
        if prim.get("reference_ids"):
            out["reference_ids"] = prim["reference_ids"]
        out["characteristics"] = prim["characteristics"]
        if prim.get("notes"):
            out["notes"] = prim["notes"]
        return out

    def split_construction_ids(cids: list[str], want_tier: str) -> list[str]:
        return [c for c in cids if CONSTRUCTION_TIER[c] == want_tier]

    primitive_families: list[dict] = []
    mode_families: list[dict] = []
    skipped_empty = []
    synthetic_mode_families: list[dict] = []

    for fam in families_doc["families"]:
        fid = fam["id"]
        insts = instances_by_family.get(fid, [])
        if not insts:
            skipped_empty.append(fid)
            continue

        if fid in MANUAL_FAMILY_SPLITS:
            split = MANUAL_FAMILY_SPLITS[fid]
            mode_insts = [p for p in insts if p["id"] in split["mode_instance_ids"]]
            insts = [p for p in insts if p["id"] not in split["mode_instance_ids"]]
            synth = {
                "id": split["mode_family_id"],
                "name": split["mode_family_name"],
                "construction_ids": [split["construction_id"]],
                "target_applications": fam.get("target_applications", []),
                "reference_ids": sorted({r for p in mode_insts for r in p.get("reference_ids", [])}),
                "process_participations": [],
                "influences": [{
                    "source_family_id": fid,
                    "relations": ["same_round_function", "same_state_layout"],
                    "note": split["influence_note"],
                }],
                "notes": f"See {split['mode_family_id']} for instances; built directly on {fid}.",
                "_insts": mode_insts,
            }
            synthetic_mode_families.append(synth)

        types_present = {instance_type(p) for p in insts}
        fixed_present = types_present & FIXED_PRIMITIVE_TYPES
        mode_present = types_present - FIXED_PRIMITIVE_TYPES
        assert not (fixed_present and mode_present), (
            f"Family '{fid}' still mixes fixed and mode instance types: {types_present}"
        )
        is_mode = bool(mode_present)

        new_fam = dict(fam)  # shallow copy, field order preserved from source
        cids = fam.get("construction_ids", [])
        if fid in PRIMITIVE_CONSTRUCTION_FIXUP and not is_mode:
            cids = PRIMITIVE_CONSTRUCTION_FIXUP[fid]
        want_tier = "mode" if is_mode else "primitive"
        kept_cids = split_construction_ids(cids, want_tier)
        if is_mode and fid in MODE_HASH_FAMILIES_USE_MERKLE_DAMGARD:
            kept_cids = ["merkle_damgard"]
        if is_mode and not kept_cids:
            had_sponge_ancestry = "sponge_permutation" in cids
            only_type = next(iter(types_present)) if len(types_present) == 1 else None
            mapped = MODE_TYPE_RENAME.get(only_type, only_type)
            if had_sponge_ancestry and mapped in SPONGE_DESCENDANT_MODE_CONSTRUCTION:
                kept_cids = [SPONGE_DESCENDANT_MODE_CONSTRUCTION[mapped]]
            elif mapped == "stream_cipher":
                kept_cids = ["native_keystream_generator"]
        new_fam["construction_ids"] = kept_cids
        new_fam["instances"] = [to_instance(p, is_mode) for p in insts]

        if is_mode:
            mode_families.append(new_fam)
        else:
            primitive_families.append(new_fam)

    for synth in synthetic_mode_families:
        insts = synth.pop("_insts")
        synth["instances"] = [to_instance(p, is_mode=True) for p in insts]
        mode_families.append(synth)

    print(f"families with zero instances (dropped): {skipped_empty}")
    print(f"primitive_families: {len(primitive_families)}, mode_families: {len(mode_families)}")

    # ---- fold legacy modes.yaml entries into mode_families --------------------
    for mode in modes_doc["modes"]:
        old_id = mode["id"]
        new_id, new_name = LEGACY_MODE_FAMILY_RENAME.get(old_id, (old_id, mode["name"]))
        fam = {
            "id": new_id,
            "name": new_name,
            "construction_ids": LEGACY_MODE_CONSTRUCTION_IDS.get(old_id, []),
            "target_applications": mode.get("target_applications", []),
            "reference_ids": mode.get("reference_ids", []),
            "process_participations": [],
            "influences": [],
            "notes": mode.get("notes", "").strip() if mode.get("notes") else "",
        }
        if mode.get("authors"):
            fam["authors"] = mode["authors"]
        if mode.get("year"):
            fam["year"] = mode["year"]
        underlying = LEGACY_UNDERLYING_PRIMITIVE_FIXUP.get(old_id, mode.get("underlying_primitive_ids", []))
        fam["underlying_primitive_ids"] = underlying
        instance_type_id = OLD_MODE_TYPE_RENAME[mode["mode_type"]]
        fam["instances"] = [{
            "id": f"{old_id}_v1",
            "name": mode["name"],
            "type": instance_type_id,
            "reference_ids": mode.get("reference_ids", []),
            "characteristics": mode.get("characteristics", {}),
        }]
        mode_families.append(fam)

    print(f"mode_families after folding modes.yaml: {len(mode_families)}")

    # ---- write primitive_types.yaml / mode_types.yaml --------------------------
    new_primitive_types = {
        "version": 1,
        "primitive_types": [
            t for t in primitive_types_doc["primitive_types"] if t["id"] in FIXED_PRIMITIVE_TYPES
        ],
    }
    mode_types_list = []
    seen_mode_type_ids = set()
    for t in primitive_types_doc["primitive_types"]:
        if t["id"] in MODE_TYPE_RENAME:
            new_id = MODE_TYPE_RENAME[t["id"]]
            entry = dict(t)
            entry["id"] = new_id
            entry["name"] = MODE_TYPE_CATALOG.get(new_id, entry["name"])
            mode_types_list.append(entry)
            seen_mode_type_ids.add(new_id)
    for extra_id in ["enc", "mac", "prng", "kdf", "keywrap"]:
        if extra_id not in seen_mode_type_ids:
            mode_types_list.append({"id": extra_id, "name": MODE_TYPE_CATALOG[extra_id]})
            seen_mode_type_ids.add(extra_id)
    new_mode_types = {"version": 1, "mode_types": mode_types_list}

    # ---- write primitive_constructions.yaml / mode_constructions.yaml ---------
    new_primitive_constructions = {
        "version": 1,
        "primitive_constructions": [
            c for c in constructions_doc["constructions"] if CONSTRUCTION_TIER[c["id"]] == "primitive"
        ],
    }
    mode_constructions_list = [
        c for c in constructions_doc["constructions"] if CONSTRUCTION_TIER[c["id"]] == "mode"
    ]
    existing_mode_construction_ids = {c["id"] for c in mode_constructions_list}
    for c in NEW_MODE_CONSTRUCTIONS:
        if c["id"] not in existing_mode_construction_ids:
            mode_constructions_list.append(c)
    new_mode_constructions = {"version": 1, "mode_constructions": mode_constructions_list}

    # ---- write everything out --------------------------------------------------
    def dump(obj: dict, name: str) -> None:
        path = DATA_DIR / name
        with path.open("w", encoding="utf-8") as f:
            yaml.dump(obj, f, sort_keys=False, allow_unicode=True, width=120)
        print(f"wrote {path} ({path.stat().st_size} bytes)")

    dump({"version": 1, "primitive_families": primitive_families}, "primitive_families.yaml")
    dump({"version": 1, "mode_families": mode_families}, "mode_families.yaml")
    dump(new_primitive_types, "primitive_types.yaml")
    dump(new_mode_types, "mode_types.yaml")
    dump(new_primitive_constructions, "primitive_constructions.yaml")
    dump(new_mode_constructions, "mode_constructions.yaml")


if __name__ == "__main__":
    main()
