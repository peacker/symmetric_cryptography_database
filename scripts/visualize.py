#!/usr/bin/env python3
"""
visualize.py — generate charts from build/viz CSV exports.

Usage (after make build-db export-viz):
    python scripts/visualize.py

Outputs PNG files into build/viz/:
    - timeline.png          primitives by year, coloured by type
    - influence_graph.png   directed influence network
    - size_scatter.png      input vs output size coloured by type
"""

from __future__ import annotations

from pathlib import Path

import csv

ROOT = Path(__file__).resolve().parents[1]
VIZ_DIR = ROOT / "build" / "viz"


def load_csv(name: str) -> list[dict]:
    path = VIZ_DIR / name
    if not path.exists():
        raise SystemExit(f"Missing {path}. Run 'make build-db export-viz' first.")
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def chart_timeline(rows: list[dict]) -> None:
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        print("matplotlib not installed; skipping timeline chart.")
        return

    types = sorted({r["primitive_type"] for r in rows})
    colour_map = {t: f"C{i}" for i, t in enumerate(types)}

    years = [int(r["year"]) for r in rows]
    names = [r["name"] for r in rows]
    colours = [colour_map[r["primitive_type"]] for r in rows]

    fig, ax = plt.subplots(figsize=(max(10, len(rows) * 0.9), 5))
    ax.scatter(years, [0] * len(rows), c=colours, s=120, zorder=3)
    for x, name, c in zip(years, names, colours):
        ax.annotate(name, (x, 0), textcoords="offset points",
                    xytext=(0, 12), ha="center", fontsize=8, rotation=45, color=c)
    ax.set_yticks([])
    ax.set_xlabel("Year")
    ax.set_title("Symmetric Primitives Timeline")
    patches = [mpatches.Patch(color=colour_map[t], label=t) for t in types]
    ax.legend(handles=patches, fontsize=8)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    out = VIZ_DIR / "timeline.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved {out}")


def chart_influence_graph(edges: list[dict]) -> None:
    try:
        import matplotlib.pyplot as plt
        import networkx as nx
    except ImportError:
        print("matplotlib/networkx not installed; skipping influence graph.")
        return

    G = nx.DiGraph()
    for e in edges:
        relations = e.get("relations_json") or ""
        relation_label = e.get("relation") or relations
        G.add_edge(e["source_family_id"], e["target_family_id"],
                   label=relation_label)

    if not G.nodes:
        print("No influence edges found; skipping graph.")
        return

    fig, ax = plt.subplots(figsize=(10, 7))
    pos = nx.spring_layout(G, seed=42)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=1800, node_color="steelblue", alpha=0.85)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=8, font_color="white")
    nx.draw_networkx_edges(G, pos, ax=ax, arrows=True,
                           arrowstyle="-|>", arrowsize=20, edge_color="grey")
    edge_labels = nx.get_edge_attributes(G, "label")
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax, font_size=7)
    ax.set_title("Primitive Influence Graph")
    ax.axis("off")
    out = VIZ_DIR / "influence_graph.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved {out}")


def chart_size_scatter(rows: list[dict]) -> None:
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        print("matplotlib not installed; skipping size scatter.")
        return

    types = sorted({r["primitive_type"] for r in rows})
    colour_map = {t: f"C{i}" for i, t in enumerate(types)}

    fig, ax = plt.subplots(figsize=(8, 6))
    for r in rows:
        ax.scatter(int(r["block_size_bits"]), int(r["output_size_bits"]),
                   c=colour_map[r["primitive_type"]], s=100, zorder=3)
        ax.annotate(r["name"], (int(r["block_size_bits"]), int(r["output_size_bits"])),
                    textcoords="offset points", xytext=(5, 3), fontsize=8)

    ax.set_xlabel("Block size (bits)")
    ax.set_ylabel("Output size (bits)")
    ax.set_title("Primitive Input vs Output Size")
    patches = [mpatches.Patch(color=colour_map[t], label=t) for t in types]
    ax.legend(handles=patches, fontsize=8)
    ax.grid(linestyle="--", alpha=0.4)
    out = VIZ_DIR / "size_scatter.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved {out}")


def main() -> None:
    primitives = load_csv("timeline_primitives.csv")
    edges = load_csv("influence_edges.csv")

    chart_timeline(primitives)
    chart_influence_graph(edges)
    chart_size_scatter(primitives)


if __name__ == "__main__":
    main()
