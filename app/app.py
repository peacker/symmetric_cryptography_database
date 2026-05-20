"""
Interactive dashboard for the Symmetric Primitives Database.

Run with:
    streamlit run app/app.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "build" / "symmetric_primitives.db"

st.set_page_config(
    page_title="Symmetric Primitives Database",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        st.error(
            "Database not found. Run `make build-db` first.",
            icon="🚫",
        )
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
            p.year,
            p.primitive_type,
            p.fixed_input_bits,
            p.fixed_output_bits,
            GROUP_CONCAT(DISTINCT t.target) AS targets,
            GROUP_CONCAT(DISTINCT s.name)   AS standards,
            GROUP_CONCAT(DISTINCT pr.name)  AS processes
        FROM primitives p
        LEFT JOIN primitive_targets t     ON t.primitive_id  = p.id
        LEFT JOIN primitive_standards ps  ON ps.primitive_id = p.id
        LEFT JOIN standards s             ON s.id            = ps.standard_id
        LEFT JOIN primitive_processes pp  ON pp.primitive_id = p.id
        LEFT JOIN processes pr            ON pr.id           = pp.process_id
        GROUP BY p.id
        ORDER BY p.year, p.name
        """,
        conn,
    )


@st.cache_data
def load_influences() -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql_query(
        """
        SELECT source_primitive_id, target_primitive_id, relation, note
        FROM primitive_influences
        ORDER BY source_primitive_id
        """,
        conn,
    )


@st.cache_data
def load_publications() -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql_query(
        """
        SELECT pub.id, pub.kind, pub.title, pub.year, pub.venue, pub.url,
               GROUP_CONCAT(p.name, ', ') AS primitives
        FROM publications pub
        LEFT JOIN primitive_publications pp ON pp.publication_id = pub.id
        LEFT JOIN primitives p              ON p.id              = pp.primitive_id
        GROUP BY pub.id
        ORDER BY pub.year DESC
        """,
        conn,
    )


# ── Sidebar navigation ────────────────────────────────────────────────────────

st.sidebar.title("Symmetric Primitives DB")
page = st.sidebar.radio(
    "View",
    ["Timeline", "Influence Graph", "Size Analysis", "Primitives Browser", "References"],
)

primitives = load_primitives()
influences = load_influences()

# ── Sidebar global filters ────────────────────────────────────────────────────

with st.sidebar.expander("Filters", expanded=True):
    all_types = sorted(primitives["primitive_type"].dropna().unique())
    selected_types = st.multiselect("Primitive type", all_types, default=all_types)

    year_min = int(primitives["year"].min())
    year_max = int(primitives["year"].max())
    year_range = st.slider("Year range", year_min, year_max, (year_min, year_max))

df = primitives[
    primitives["primitive_type"].isin(selected_types)
    & primitives["year"].between(*year_range)
]

# ── Pages ─────────────────────────────────────────────────────────────────────

if page == "Timeline":
    st.header("Primitive Timeline")
    st.caption("Each point is one primitive, coloured by type. Hover for details.")

    fig = px.strip(
        df,
        x="year",
        y="primitive_type",
        color="primitive_type",
        hover_name="name",
        hover_data={
            "year": True,
            "primitive_type": False,
            "fixed_input_bits": True,
            "fixed_output_bits": True,
            "targets": True,
            "standards": True,
        },
        labels={
            "year": "Year",
            "primitive_type": "Type",
            "fixed_input_bits": "Input (bits)",
            "fixed_output_bits": "Output (bits)",
            "targets": "Applications",
            "standards": "Standards",
        },
        height=420,
    )
    fig.update_traces(marker_size=14, jitter=0)
    fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

elif page == "Influence Graph":
    st.header("Design Influence Network")

    if influences.empty:
        st.info("No influence edges in the database yet.")
    else:
        try:
            from pyvis.network import Network  # type: ignore
            import streamlit.components.v1 as components

            net = Network(height="560px", width="100%", directed=True,
                          bgcolor="#0e1117", font_color="white")
            net.set_options("""
            {
              "physics": {
                "barnesHut": { "gravitationalConstant": -8000, "springLength": 180 }
              },
              "edges": {
                "arrows": { "to": { "enabled": true } },
                "color": { "color": "#888" },
                "font": { "size": 11, "color": "#ccc" }
              },
              "nodes": {
                "shape": "dot",
                "size": 20,
                "font": { "size": 14 }
              }
            }
            """)

            RELATION_COLOURS = {
                "special_case_of":   "#ef553b",
                "improvement_of":    "#636efa",
                "inspired_by":       "#00cc96",
                "variant_of":        "#ab63fa",
                "generalization_of": "#ffa15a",
                "related_to":        "#19d3f3",
            }

            all_nodes = set(influences["source_primitive_id"]) | set(
                influences["target_primitive_id"]
            )
            for node in all_nodes:
                row = primitives[primitives["id"] == node]
                label = row["name"].iloc[0] if not row.empty else node
                title = (
                    f"{label}<br>Year: {row['year'].iloc[0]}<br>"
                    f"Type: {row['primitive_type'].iloc[0]}"
                    if not row.empty
                    else node
                )
                net.add_node(node, label=label, title=title)

            for _, edge in influences.iterrows():
                colour = RELATION_COLOURS.get(edge["relation"], "#888")
                net.add_edge(
                    edge["source_primitive_id"],
                    edge["target_primitive_id"],
                    label=edge["relation"].replace("_", " "),
                    color=colour,
                    title=edge["note"],
                )

            html_path = ROOT / "build" / "influence_graph.html"
            html_path.parent.mkdir(parents=True, exist_ok=True)
            net.save_graph(str(html_path))
            components.html(html_path.read_text(encoding="utf-8"), height=580)

            with st.expander("Edge table"):
                st.dataframe(influences, use_container_width=True)

        except ImportError:
            st.warning(
                "pyvis is not installed. Run `make setup` then restart the app."
            )
            st.dataframe(influences, use_container_width=True)

elif page == "Size Analysis":
    st.header("Input vs Output Size")
    st.caption(
        "Bubble size is proportional to the output size. "
        "Hover a point for full details."
    )

    fig = px.scatter(
        df,
        x="fixed_input_bits",
        y="fixed_output_bits",
        color="primitive_type",
        size="fixed_output_bits",
        hover_name="name",
        hover_data={
            "year": True,
            "targets": True,
            "standards": True,
            "fixed_input_bits": True,
            "fixed_output_bits": True,
        },
        labels={
            "fixed_input_bits": "Input size (bits)",
            "fixed_output_bits": "Output size (bits)",
            "primitive_type": "Type",
        },
        text="name",
        height=500,
    )
    fig.update_traces(textposition="top center", marker_sizemin=12)
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig, use_container_width=True)

elif page == "Primitives Browser":
    st.header("Primitives Browser")

    cols = st.columns([3, 1])
    search = cols[0].text_input("Search by name", placeholder="e.g. AES, GIFT…")
    sort_col = cols[1].selectbox("Sort by", ["year", "name", "fixed_input_bits"])

    view = df.copy()
    if search:
        view = view[view["name"].str.contains(search, case=False, na=False)]
    view = view.sort_values(sort_col)

    st.caption(f"{len(view)} primitives shown")
    st.dataframe(
        view[
            ["name", "year", "primitive_type", "fixed_input_bits",
             "fixed_output_bits", "targets", "standards", "processes"]
        ].rename(columns={
            "fixed_input_bits": "input (bits)",
            "fixed_output_bits": "output (bits)",
            "primitive_type": "type",
        }),
        use_container_width=True,
        hide_index=True,
    )

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
            if row.get("venue"):
                st.write(f"**Venue:** {row['venue']}")
            if row.get("primitives"):
                st.write(f"**Used by:** {row['primitives']}")
            if row.get("url"):
                st.markdown(f"[Link]({row['url']})")
