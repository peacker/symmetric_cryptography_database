"""
Interactive dashboard for the Symmetric Primitives Database.

Run with:
    streamlit run app/app.py
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "build" / "symmetric_primitives.db"
TWEAKEY_EXPR_RE = re.compile(r"^([1-9][0-9]*)\s*-\s*key_size_bits$")

st.set_page_config(
    page_title="Symmetric Primitives Database",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        st.error("Database not found. Run `make build-db` first.")
        st.stop()
    return sqlite3.connect(DB_PATH, check_same_thread=False)


@st.cache_data
def load_primitives() -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql_query(
        """
        SELECT
            p.id,
            p.name,
            f.year,
            f.id   AS family_id,
            f.name AS family_name,
            pt.name AS primitive_type,
            p.characteristics_json,
            p.fixed_input_bits,
            p.fixed_output_bits,
            GROUP_CONCAT(DISTINCT r.id)      AS round_ids,
            GROUP_CONCAT(DISTINCT r.name)    AS rounds,
            GROUP_CONCAT(DISTINCT r.round_hash) AS round_hashes,
            GROUP_CONCAT(DISTINCT t.target)  AS targets,
            GROUP_CONCAT(DISTINCT pub.title) AS standards,
            GROUP_CONCAT(DISTINCT pr.name)   AS processes
        FROM primitives p
        JOIN families f ON f.id = p.family_id
        JOIN primitive_types pt ON pt.id = p.primitive_type
        LEFT JOIN family_rounds fr        ON fr.family_id = f.id
        LEFT JOIN rounds r                ON r.id = fr.round_id
        LEFT JOIN family_targets t       ON t.family_id    = f.id
        LEFT JOIN primitive_standards ps ON ps.primitive_id = p.id
        LEFT JOIN publications pub        ON pub.id = ps.standard_id
        LEFT JOIN family_processes fp    ON fp.family_id = f.id
        LEFT JOIN processes pr           ON pr.id = fp.process_id
        GROUP BY p.id
        ORDER BY f.year, p.name
        """,
        conn,
    )


def split_grouped_values(value: object) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, float) and pd.isna(value):
        return set()
    text = str(value).strip()
    if not text:
        return set()
    return {v.strip() for v in text.split(",") if v.strip()}


def format_size_value(label: str, value: object) -> str | None:
    if isinstance(value, int) and value > 0:
        return f"{label}[{value}]"
    if isinstance(value, str):
        expr = value.strip()
        expr_match = TWEAKEY_EXPR_RE.match(expr)
        if expr_match:
            total_bits = expr_match.group(1)
            return f"{label}[{total_bits}-key_size_bits]"
    return None


def format_range_value(label: str, min_value: object, max_value: object) -> str | None:
    if not isinstance(min_value, int) or min_value <= 0:
        return None
    if not isinstance(max_value, int) or max_value <= 0:
        return None
    if min_value == max_value:
        return f"{label}[{min_value}]"
    return f"{label}[{min_value}-{max_value}]"


def format_inputs_bits(characteristics_json: object, fixed_input_bits: object) -> str:
    parts: list[str] = []
    seen_labels: set[str] = set()

    if fixed_input_bits is not None and not (isinstance(fixed_input_bits, float) and pd.isna(fixed_input_bits)):
        parts.append(f"message[{int(fixed_input_bits)}]")
        seen_labels.add("message")

    if characteristics_json is None:
        return ", ".join(parts)
    if isinstance(characteristics_json, float) and pd.isna(characteristics_json):
        return ", ".join(parts)

    try:
        characteristics = json.loads(str(characteristics_json))
    except (json.JSONDecodeError, TypeError):
        return ", ".join(parts)

    extra_inputs = [
        ("fixed_input_bits", "message"),
        ("key_size_bits", "key"),
        ("tweak_size_bits", "tweak"),
        ("tweakey_size_bits", "tweakey"),
        ("iv_size_bits", "iv"),
        ("nonce_size_bits", "nonce"),
    ]
    for field, label in extra_inputs:
        range_rendered = format_range_value(
            label,
            characteristics.get(f"{field}_min"),
            characteristics.get(f"{field}_max"),
        )
        if range_rendered and label not in seen_labels:
            parts.append(range_rendered)
            seen_labels.add(label)
            continue

        value = characteristics.get(field)
        rendered = format_size_value(label, value)
        if rendered and label not in seen_labels:
            parts.append(rendered)
            seen_labels.add(label)

    return ", ".join(parts)


@st.cache_data
def load_families() -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql_query(
        """
        SELECT
            f.id,
            f.name,
            f.year,
            CASE WHEN COUNT(DISTINCT p.primitive_type) = 1
                 THEN MAX(pt.name)
                 ELSE 'Mixed'
            END AS primitive_type,
            GROUP_CONCAT(DISTINCT pt.name) AS constituent_types,
            f.notes,
            COUNT(DISTINCT p.id) AS instance_count,
            GROUP_CONCAT(DISTINCT p.name)    AS instances,
            GROUP_CONCAT(DISTINCT r.name)    AS rounds,
            GROUP_CONCAT(DISTINCT t.target)  AS targets,
            GROUP_CONCAT(DISTINCT c.name)    AS constructions,
            GROUP_CONCAT(DISTINCT pub.title) AS standards,
            GROUP_CONCAT(DISTINCT pr.name)   AS processes
        FROM families f
        LEFT JOIN primitives p      ON p.family_id  = f.id
        LEFT JOIN primitive_types pt ON pt.id = p.primitive_type
        LEFT JOIN family_rounds fr  ON fr.family_id = f.id
        LEFT JOIN rounds r          ON r.id = fr.round_id
        LEFT JOIN family_targets t  ON t.family_id  = f.id
        LEFT JOIN family_constructions fc ON fc.family_id = f.id
        LEFT JOIN constructions c        ON c.id = fc.construction_id
        LEFT JOIN family_standards fs ON fs.family_id = f.id
        LEFT JOIN publications pub    ON pub.id = fs.standard_id
        LEFT JOIN family_processes fp ON fp.family_id = f.id
        LEFT JOIN processes pr        ON pr.id = fp.process_id
        GROUP BY f.id
        ORDER BY f.year, f.name
        """,
        conn,
    )


@st.cache_data
def load_influences() -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql_query(
        """
        SELECT fi.source_family_id, sf.name AS source_name,
               fi.target_family_id, tf.name AS target_name,
               fi.relation, fi.note,
             CASE WHEN COUNT(DISTINCT sp.primitive_type) = 1
                  THEN MAX(pts.name)
                  ELSE 'Mixed'
             END AS source_type,
               sf.year AS source_year,
               tf.year AS target_year
        FROM family_influences fi
        JOIN families sf ON sf.id = fi.source_family_id
        JOIN families tf ON tf.id = fi.target_family_id
         LEFT JOIN primitives sp ON sp.family_id = sf.id
         LEFT JOIN primitive_types pts ON pts.id = sp.primitive_type
         GROUP BY fi.source_family_id, fi.target_family_id, fi.relation, fi.note, sf.name, tf.name, sf.year, tf.year
        ORDER BY fi.source_family_id
        """,
        conn,
    )


@st.cache_data
def load_publications() -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql_query(
        """
        SELECT pub.id, pub.kind, pub.title, pub.year, pub.venue, pub.url,
               pub.organization, pub.status,
               GROUP_CONCAT(DISTINCT COALESCE(f.name, fs_f.name)) AS families
        FROM publications pub
        LEFT JOIN family_publications fp ON fp.publication_id = pub.id
        LEFT JOIN families f             ON f.id = fp.family_id
        LEFT JOIN family_standards fs    ON fs.standard_id = pub.id
        LEFT JOIN families fs_f          ON fs_f.id = fs.family_id
        GROUP BY pub.id
        ORDER BY pub.year DESC
        """,
        conn,
    )


@st.cache_data
def load_rounds() -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql_query(
        """
        SELECT r.id, r.name, r.kind, r.round_hash, r.notes,
               COUNT(DISTINCT f.id) AS family_count,
               COUNT(DISTINCT p.id) AS primitive_count,
               GROUP_CONCAT(DISTINCT f.name) AS families,
               GROUP_CONCAT(DISTINCT p.name) AS primitives
        FROM rounds r
        LEFT JOIN family_rounds fr ON fr.round_id = r.id
        LEFT JOIN families f ON f.id = fr.family_id
        LEFT JOIN primitives p ON p.family_id = f.id
        GROUP BY r.id
        ORDER BY r.name
        """,
        conn,
    )


# ── Sidebar navigation ────────────────────────────────────────────────────────

st.sidebar.title("Symmetric Primitives DB")
page = st.sidebar.radio(
    "View",
    ["Timeline", "Influence Graph", "Size Analysis",
    "Primitives Browser", "Families", "Rounds", "References"],
)

primitives = load_primitives()
families   = load_families()
influences = load_influences()
rounds_df  = load_rounds()

# ── Sidebar global filters ────────────────────────────────────────────────────

with st.sidebar.expander("Filters", expanded=True):
    all_types = sorted(primitives["primitive_type"].dropna().unique())
    selected_types = st.multiselect("Primitive type", all_types, default=all_types)

    all_rounds = sorted({
        round_name
        for grouped in primitives["rounds"]
        for round_name in split_grouped_values(grouped)
    })
    selected_rounds = st.multiselect("Round template", all_rounds, default=all_rounds)

    year_min = int(primitives["year"].min())
    year_max = int(primitives["year"].max())
    year_range = st.slider("Year range", year_min, year_max, (year_min, year_max))

df = primitives[
    primitives["primitive_type"].isin(selected_types)
    & primitives["year"].between(*year_range)
].copy()
df["inputs_bits"] = df.apply(
    lambda row: format_inputs_bits(row.get("characteristics_json"), row.get("fixed_input_bits")),
    axis=1,
)

if selected_rounds:
    selected_rounds_set = set(selected_rounds)
    df = df[df["rounds"].apply(lambda v: bool(split_grouped_values(v) & selected_rounds_set))]
else:
    df = df.iloc[0:0]

def _family_matches_types(row: pd.Series, selected: set) -> bool:
    """Return True if any of the family's constituent types is in selected."""
    types = set(str(row["constituent_types"]).split(",")) if row["constituent_types"] else {row["primitive_type"]}
    return bool(types & selected)

timeline_df = families[
    families.apply(_family_matches_types, axis=1, selected=set(selected_types))
    & families["year"].between(*year_range)
].copy()

if selected_rounds:
    selected_rounds_set = set(selected_rounds)
    timeline_df = timeline_df[
        timeline_df["rounds"].apply(
            lambda v: bool(split_grouped_values(v) & selected_rounds_set)
        )
    ]
else:
    timeline_df = timeline_df.iloc[0:0]

# ── Pages ─────────────────────────────────────────────────────────────────────

if page == "Timeline":
    st.header("Primitive Family Timeline")
    st.caption(
        "Each point is one **family**. Labels are shown next to points, and "
        "hover details include all known instances in that family."
    )

    timeline_view = timeline_df.sort_values(["year", "name"]).copy()
    timeline_view["year_rank"] = timeline_view.groupby("year").cumcount()
    timeline_view["year_label"] = timeline_view["year"].astype(str)

    fig = px.scatter(
        timeline_view,
        x="year",
        y="year_rank",
        color="primitive_type",
        symbol="primitive_type",
        text="name",
        hover_name="name",
        hover_data={
            "year": True,
            "primitive_type": False,
            "instance_count": True,
            "instances": True,
            "targets": True,
            "standards": True,
            "year_rank": False,
        },
        labels={
            "year": "Year",
            "primitive_type": "Type",
            "instance_count": "Instances",
            "instances": "Instance names",
            "targets": "Applications",
            "standards": "Standards",
        },
        height=560,
    )
    fig.update_traces(textposition="top center", marker_size=12, textfont_size=10)
    fig.update_yaxes(showticklabels=False, title_text="")
    fig.update_xaxes(
        tickmode="linear",
        dtick=1,
        tickangle=90,
    )
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, width="stretch")

elif page == "Influence Graph":
    st.header("Family Influence Network")
    st.caption("Nodes are **families**; edges capture design lineage. Edge colour = relation type.")

    if influences.empty:
        st.info("No influence edges in the database yet.")
    else:
        try:
            from pyvis.network import Network  # type: ignore
            import streamlit.components.v1 as components

            RELATION_COLOURS = {
                "special_case_of":   "#ef553b",
                "improvement_of":    "#636efa",
                "inspired_by":       "#00cc96",
                "variant_of":        "#ab63fa",
                "generalization_of": "#ffa15a",
                "related_to":        "#19d3f3",
            }
            TYPE_COLOURS = {
                "Block Cipher": "#4c78a8",
                "Tweakable Block Cipher": "#72b7b2",
                "Permutation": "#f58518",
                "Compression Function": "#e45756",
                "Update Function": "#54a24b",
                "block_cipher": "#4c78a8",
                "tweakable_block_cipher": "#72b7b2",
                "permutation": "#f58518",
                "compression_function": "#e45756",
                "update_function": "#54a24b",
            }

            net = Network(height="560px", width="100%", directed=True,
                          bgcolor="#0e1117", font_color="white")
            net.set_options("""
            {
              "physics": {
                "barnesHut": { "gravitationalConstant": -8000, "springLength": 200 }
              },
              "edges": {
                "arrows": { "to": { "enabled": true } },
                "color": { "color": "#888" },
                "font": { "size": 11, "color": "#ccc" }
              },
              "nodes": {
                "shape": "dot",
                "size": 22,
                "font": { "size": 14 }
              }
            }
            """)

            # Add all family nodes
            for _, row in families.iterrows():
                title = (
                    f"<b>{row['name']}</b><br>"
                    f"Year: {row['year']}<br>"
                    f"Type: {row['primitive_type']}<br>"
                    f"Instances: {row['instances'] or '—'}"
                )
                node_colour = TYPE_COLOURS.get(row["primitive_type"], "#888")
                net.add_node(row["id"], label=row["name"],
                             title=title, color=node_colour)

            for _, edge in influences.iterrows():
                colour = RELATION_COLOURS.get(edge["relation"], "#888")
                net.add_edge(
                    edge["source_family_id"],
                    edge["target_family_id"],
                    label=edge["relation"].replace("_", " "),
                    color=colour,
                    title=edge["note"],
                )

            html_path = ROOT / "build" / "influence_graph.html"
            html_path.parent.mkdir(parents=True, exist_ok=True)
            net.save_graph(str(html_path))
            components.html(html_path.read_text(encoding="utf-8"), height=580)

            # Colour legend
            cols = st.columns(len(RELATION_COLOURS))
            for col, (rel, colour) in zip(cols, RELATION_COLOURS.items()):
                col.markdown(
                    f'<span style="color:{colour}">■</span> {rel.replace("_", " ")}',
                    unsafe_allow_html=True,
                )

            with st.expander("Edge table"):
                st.dataframe(
                    influences[["source_name", "target_name", "relation", "note"]],
                    width="stretch",
                )

        except ImportError:
            st.warning("pyvis is not installed. Run `make setup` then restart the app.")
            st.dataframe(influences, width="stretch")

elif page == "Size Analysis":
    st.header("Input vs Output Size")
    st.caption(
        "Aggregated view: one marker per (type, input bits, output bits). "
        "Marker size shows how many instances share that size pair."
    )

    size_view = (
        df.groupby(["primitive_type", "fixed_input_bits", "fixed_output_bits"], dropna=False)
        .agg(
            instance_count=("id", "count"),
            family_count=("family_id", "nunique"),
            families=("family_name", lambda s: ", ".join(sorted(set(s.dropna()))[:8])),
        )
        .reset_index()
    )

    fig = px.scatter(
        size_view,
        x="fixed_input_bits",
        y="fixed_output_bits",
        size="instance_count",
        color="primitive_type",
        facet_col="primitive_type",
        facet_col_wrap=2,
        text="instance_count",
        hover_data={
            "fixed_input_bits": True,
            "fixed_output_bits": True,
            "instance_count": True,
            "family_count": True,
            "families": True,
        },
        labels={
            "fixed_input_bits": "Input size (bits)",
            "fixed_output_bits": "Output size (bits)",
            "instance_count": "Instances",
            "family_count": "Families",
            "primitive_type": "Type",
        },
        height=700,
    )
    fig.update_traces(textposition="top center", marker_sizemin=14)
    fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, width="stretch")

    with st.expander("Aggregated size table"):
        st.dataframe(
            size_view.sort_values(["primitive_type", "fixed_input_bits", "fixed_output_bits"]),
            width="stretch",
            hide_index=True,
        )

elif page == "Primitives Browser":
    st.header("Instances Browser")

    cols = st.columns([3, 1])
    search   = cols[0].text_input("Search by name", placeholder="e.g. AES, GIFT…")
    sort_col = cols[1].selectbox("Sort by", ["year", "name", "fixed_input_bits"])

    view = df.copy()
    if search:
        view = view[view["name"].str.contains(search, case=False, na=False)]
    view = view.sort_values(sort_col)

    st.caption(f"{len(view)} instances shown")
    st.dataframe(
        view[["name", "family_name", "year", "primitive_type",
              "inputs_bits", "fixed_output_bits", "rounds",
              "targets", "standards", "processes"]]
        .rename(columns={
            "family_name": "family",
            "primitive_type": "type",
            "inputs_bits": "inputs[bits]",
            "fixed_output_bits": "output (bits)",
            "rounds": "round templates",
        }),
        width="stretch",
        hide_index=True,
    )

elif page == "Families":
    st.header("Families Browser")

    fam_types = sorted(families["primitive_type"].dropna().unique())
    sel_types = st.multiselect("Filter by type", fam_types, default=fam_types)
    fam_view  = families[families["primitive_type"].isin(sel_types)].sort_values("year")

    for _, row in fam_view.iterrows():
        with st.expander(f"**{row['name']}** ({row['year']}) — {row['primitive_type']}"):
            cols = st.columns(3)
            cols[0].metric("Instances", row["instance_count"])
            cols[1].write(f"**Applications:** {row['targets'] or '—'}")
            cols[2].write(f"**Standards:** {row['standards'] or '—'}")
            if row.get("constructions"):
                st.write(f"**Constructions:** {row['constructions']}")
            if row.get("instances"):
                st.write(f"**Instance names:** {row['instances']}")
            if row.get("notes"):
                st.info(row["notes"])

elif page == "Rounds":
    st.header("Rounds Catalogue")
    st.caption("Round templates and where they are reused across families and instances.")

    kinds = sorted(rounds_df["kind"].dropna().unique())
    selected_kinds = st.multiselect("Filter by kind", kinds, default=kinds)
    search = st.text_input("Search rounds", placeholder="e.g. quarterround, AES…")

    view = rounds_df[rounds_df["kind"].isin(selected_kinds)].copy()
    if search:
        view = view[
            view["name"].str.contains(search, case=False, na=False)
            | view["id"].str.contains(search, case=False, na=False)
        ]

    st.caption(f"{len(view)} round templates shown")
    st.dataframe(
        view[["id", "name", "kind", "family_count", "primitive_count", "round_hash"]],
        width="stretch",
        hide_index=True,
    )

    for _, row in view.iterrows():
        with st.expander(f"**{row['name']}** ({row['kind']})"):
            st.write(f"**Round id:** {row['id']}")
            st.write(f"**Hash:** {row['round_hash']}")
            st.write(f"**Families:** {row.get('families') or '—'}")
            st.write(f"**Primitives:** {row.get('primitives') or '—'}")
            if row.get("notes"):
                st.info(row["notes"])

elif page == "References":
    st.header("Publications & Standards")
    pubs = load_publications()

    kind_filter = st.multiselect(
        "Kind",
        sorted(pubs["kind"].unique()),
        default=list(pubs["kind"].unique()),
    )
    view = pubs[pubs["kind"].isin(kind_filter)].copy()

    for _, row in view.iterrows():
        with st.expander(f"{row['year']} — {row['title']}"):
            st.write(f"**Kind:** {row['kind']}")
            if row.get("organization"):
                st.write(f"**Organization:** {row['organization']}  |  **Status:** {row.get('status') or '—'}")
            if row.get("venue"):
                st.write(f"**Venue:** {row['venue']}")
            if row.get("families"):
                st.write(f"**Families:** {row['families']}")
            if row.get("url"):
                st.markdown(f"[Link]({row['url']})")
