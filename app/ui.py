from __future__ import annotations

import re

import streamlit as st

from app.config import load_settings
from app.models import Connector, Piece, PuzzleGraph, SolveResult
from app.neo4j import Neo4jPuzzleRepository
from app.solver import PuzzleSolver

_settings = load_settings()
_repo = Neo4jPuzzleRepository(
    _settings.neo4j_uri,
    _settings.neo4j_username,
    _settings.neo4j_password,
    _settings.neo4j_database,
)
_solver = PuzzleSolver()

_STEP_STYLE = {
    "start":   "background:#ede9fe;border-left:3px solid #7c3aed",
    "placed":  "background:#dcfce7;border-left:3px solid #16a34a",
    "missing": "background:#fee2e2;border-left:3px solid #dc2626",
}


def _save_puzzle(puzzle: dict) -> None:
    pieces = {p["id"]: Piece(id=p["id"], label=p["label"], puzzle_id=puzzle["id"]) for p in puzzle["pieces"]}
    connectors = {c["id"]: Connector(id=c["id"], label=c["label"], type=c["type"], piece_id=c["piece_id"]) for c in puzzle["connectors"]}
    graph = PuzzleGraph(
        id=puzzle["id"],
        name=puzzle["name"],
        description=puzzle["description"],
        pieces=pieces,
        connectors=connectors,
        connections=[tuple(cn) for cn in puzzle["connections"]],
    )
    _repo.seed(graph)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")


def _next_piece_id(pieces: list) -> str:
    return f"P{len(pieces) + 1:02d}"


# ── solve tab ─────────────────────────────────────────────────────────────────

def _solve_tab(ss: dict) -> None:
    ss.setdefault("extra_missing", set())
    ss.setdefault("result", None)

    all_puzzles = _repo.list_puzzles()
    if not all_puzzles:
        st.warning("No puzzles yet. Create one in the **Create Puzzle** tab.")
        return

    puzzle_map = {p.id: p.name for p in all_puzzles}
    left, right = st.columns([1, 2])

    with left:
        puzzle_id = st.selectbox("Puzzle", list(puzzle_map.keys()), format_func=lambda k: puzzle_map[k])

        if ss.get("_last_puzzle") != puzzle_id:
            ss["extra_missing"] = set()
            ss["result"] = None
            ss["_last_puzzle"] = puzzle_id

        graph: PuzzleGraph = _repo.get(puzzle_id)
        piece_map = {pid: p.label for pid, p in graph.pieces.items()}

        start_id = st.selectbox("Start piece", list(piece_map.keys()), format_func=lambda k: piece_map[k])

        ms_selected = st.multiselect(
            "Missing pieces",
            [pid for pid in piece_map if pid != start_id],
            format_func=lambda k: piece_map[k],
            placeholder="None",
        )
        missing = set(ms_selected) | ss["extra_missing"]

        c1, c2 = st.columns(2)
        if c1.button("Solve", type="primary", use_container_width=True):
            ss["result"] = _solver.solve(graph, start_id, missing)
        if c2.button("Clear", use_container_width=True):
            ss["extra_missing"] = set()
            ss["result"] = None
            st.rerun()

        if ss["result"]:
            r: SolveResult = ss["result"]
            st.divider()
            placed = len(r.placed_piece_ids)
            total = len(graph.pieces)
            st.write(f"{'✅ Complete' if r.is_complete else '⚠️ Partial'} — {placed}/{total} placed")

    with right:
        if not ss["result"]:
            st.write("Press **Solve** to generate instructions.")
        else:
            html_parts = []
            placed_pieces = {}
            for step in ss["result"].steps:
                style = _STEP_STYLE.get(step.status, "background:#f1f5f9;border-left:3px solid #94a3b8")
                html_parts.append(
                    f'<div style="{style};padding:5px 10px;border-radius:5px;'
                    f'font-size:0.87rem;margin-bottom:4px">'
                    f'<b>{step.step_number}.</b> {step.instruction}</div>'
                )
                if step.status == "placed" and step.piece_id in graph.pieces:
                    placed_pieces[step.piece_id] = graph.pieces[step.piece_id].label

            st.markdown("\n".join(html_parts), unsafe_allow_html=True)

            if placed_pieces:
                st.divider()
                pick_col, btn_col = st.columns([3, 1], vertical_alignment="bottom")
                picked = pick_col.selectbox(
                    "Don't have a piece?",
                    options=list(placed_pieces.keys()),
                    format_func=lambda k: placed_pieces[k],
                )
                if btn_col.button("❌ Mark missing", type="primary"):
                    ss["extra_missing"].add(picked)
                    ss["result"] = _solver.solve(graph, start_id, set(ms_selected) | ss["extra_missing"])
                    st.rerun()


# ── create tab ────────────────────────────────────────────────────────────────

def _empty_draft() -> dict:
    return {"name": "", "description": "", "pieces": [], "connections": []}


def _conn_map(d: dict) -> dict[str, str]:
    m: dict[str, str] = {}
    for ca, cb in d["connections"]:
        m[ca] = cb
        m[cb] = ca
    return m


def _create_tab(ss: dict) -> None:
    ss.setdefault("draft", _empty_draft())
    ss.setdefault("open_piece", None)
    ss.setdefault("open_conn",  None)
    d = ss["draft"]

    # constrain width — create content sits in left 60%, right side is breathing room
    col, _ = st.columns([3, 2])

    with col:
        d["name"]        = st.text_input("Puzzle name", value=d["name"], placeholder="e.g. My Dinosaur")
        d["description"] = st.text_input("Description", value=d["description"], placeholder="Material, theme, notes…")

        st.markdown("---")
        st.markdown("**Pieces**")

        cm = _conn_map(d)
        all_labels = {
            c["id"]: f"{p['label']} · {c['label']} ({c['type']})"
            for p in d["pieces"] for c in p["connectors"]
        }

        for piece in d["pieces"]:
            is_open = ss["open_piece"] == piece["id"]
            n = len(piece["connectors"])
            conn_word = "connector" if n == 1 else "connectors"

            with st.container(border=True):
                h1, h2, h3 = st.columns([6, 1, 1], vertical_alignment="center")
                h1.markdown(f"<span style='font-size:1.05rem'><b>{piece['id']}</b> &nbsp; {piece['label']}</span> &nbsp; <span style='color:#888;font-size:0.85rem'>{n} {conn_word}</span>", unsafe_allow_html=True)
                if h2.button("▼" if is_open else "▶", key=f"tog_p_{piece['id']}", use_container_width=True):
                    ss["open_piece"] = None if is_open else piece["id"]
                    ss["open_conn"]  = None
                    st.rerun()
                if h3.button("🗑", key=f"del_p_{piece['id']}", use_container_width=True):
                    pids = {c["id"] for c in piece["connectors"]}
                    d["connections"] = [cn for cn in d["connections"] if not pids.intersection(cn)]
                    d["pieces"] = [p for p in d["pieces"] if p["id"] != piece["id"]]
                    if ss["open_piece"] == piece["id"]:
                        ss["open_piece"] = None
                    st.rerun()

                if is_open:
                    st.divider()
                    if not piece["connectors"]:
                        st.caption("No connectors yet.")

                    for i, conn in enumerate(piece["connectors"]):
                        conn_open = ss["open_conn"] == conn["id"]
                        partner   = cm.get(conn["id"])
                        link_text = f"↔ {all_labels.get(partner, partner)}" if partner else "unlinked"
                        link_color = "#16a34a" if partner else "#94a3b8"

                        with st.container(border=True):
                            cr1, cr2, cr3 = st.columns([5, 1, 1], vertical_alignment="center")
                            cr1.markdown(
                                f"<span style='font-size:1rem'><b>{conn['label']}</b> &nbsp; <code>{conn['type']}</code></span> &nbsp; "
                                f"<span style='color:{link_color};font-size:0.85rem'>{link_text}</span>",
                                unsafe_allow_html=True,
                            )
                            if cr2.button("▼" if conn_open else "▶", key=f"tog_c_{conn['id']}", use_container_width=True):
                                ss["open_conn"] = None if conn_open else conn["id"]
                                st.rerun()
                            if cr3.button("🗑", key=f"del_c_{conn['id']}", use_container_width=True):
                                d["connections"] = [cn for cn in d["connections"] if conn["id"] not in cn]
                                piece["connectors"].pop(i)
                                if ss["open_conn"] == conn["id"]:
                                    ss["open_conn"] = None
                                st.rerun()

                            if conn_open:
                                if partner:
                                    la, lb = st.columns([4, 1])
                                    la.success(f"↔ {all_labels.get(partner, partner)}")
                                    if lb.button("Unlink", key=f"unlink_{conn['id']}"):
                                        d["connections"] = [cn for cn in d["connections"] if conn["id"] not in cn]
                                        st.rerun()
                                else:
                                    other = [p for p in d["pieces"] if p["id"] != piece["id"] and p["connectors"]]
                                    if not other:
                                        st.caption("Add connectors to other pieces first.")
                                    else:
                                        popts = {p["id"]: p["label"] for p in other}
                                        la, lb = st.columns(2)
                                        to_pid  = la.selectbox("Piece", list(popts.keys()), format_func=lambda k: popts[k], key=f"tp_{conn['id']}")
                                        to_p    = next(p for p in d["pieces"] if p["id"] == to_pid)
                                        copts   = {c["id"]: f"{c['label']} ({c['type']})" for c in to_p["connectors"]}
                                        to_conn = lb.selectbox("Connector", list(copts.keys()), format_func=lambda k: copts[k], key=f"tc_{conn['id']}")
                                        if st.button("Link", key=f"link_{conn['id']}", type="primary"):
                                            if not any(set(cn) == {conn["id"], to_conn} for cn in d["connections"]):
                                                d["connections"].append([conn["id"], to_conn])
                                                st.rerun()

                    st.markdown("")
                    na, nb, nc = st.columns([3, 2, 2])
                    new_cl = na.text_input("Connector label", placeholder="A", key=f"ncl_{piece['id']}", label_visibility="collapsed")
                    new_ct = nb.selectbox("Type", ["tab", "hole"], key=f"nct_{piece['id']}", label_visibility="collapsed")
                    if nc.button("＋ Connector", key=f"addconn_{piece['id']}"):
                        if new_cl.strip():
                            cid = f"{piece['id']}_{new_cl.strip()}"
                            if any(c["id"] == cid for c in piece["connectors"]):
                                st.warning(f"'{new_cl.strip()}' already exists.")
                            else:
                                piece["connectors"].append({"id": cid, "label": new_cl.strip(), "type": new_ct, "piece_id": piece["id"]})
                                st.rerun()

        # add piece
        st.caption("Label pieces with a number so they're easy to identify physically — e.g. **1 - Cabeza**, **2 - Cuello**.")
        with st.form("add_piece", clear_on_submit=True):
            fc1, fc2 = st.columns([3, 1])
            new_label = fc1.text_input("New piece", placeholder="e.g. 1 - Cabeza", label_visibility="collapsed")
            if fc2.form_submit_button("＋ Add piece", use_container_width=True):
                if new_label.strip():
                    d["pieces"].append({"id": _next_piece_id(d["pieces"]), "label": new_label.strip(), "connectors": []})
                    st.rerun()

        st.markdown("---")
        can_save = bool(d["name"].strip() and d["pieces"])
        if st.button("💾 Save puzzle", type="primary", disabled=not can_save, use_container_width=True):
            puzzle_json = {
                "id": _slug(d["name"]),
                "name": d["name"].strip(),
                "description": d["description"].strip(),
                "pieces": [{"id": p["id"], "label": p["label"]} for p in d["pieces"]],
                "connectors": [
                    {"id": c["id"], "label": c["label"], "type": c["type"], "piece_id": c["piece_id"]}
                    for p in d["pieces"] for c in p["connectors"]
                ],
                "connections": d["connections"],
            }
            _save_puzzle(puzzle_json)
            st.success(f"✅ '{d['name']}' saved!")
            ss["draft"] = _empty_draft()
            ss["open_piece"] = None
            ss["open_conn"]  = None
            st.rerun()
        if not can_save:
            st.caption("Need a name and at least one piece to save.")


# ── main ──────────────────────────────────────────────────────────────────────

def run_app() -> None:
    st.set_page_config(page_title="Puzzle Solver", layout="wide")
    st.title("Puzzle Solver")

    ss = st.session_state
    tab_solve, tab_create = st.tabs(["Solve", "Create Puzzle"])

    with tab_solve:
        _solve_tab(ss)

    with tab_create:
        _create_tab(ss)
