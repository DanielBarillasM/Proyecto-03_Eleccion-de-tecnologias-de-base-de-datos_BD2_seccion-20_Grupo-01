from __future__ import annotations

from typing import List

from app.models import Connector, Piece, PuzzleGraph

try:
    from neo4j import GraphDatabase
except Exception:
    GraphDatabase = None


# Node IDs stored in Neo4j are globally namespaced: "{puzzle_id}__{local_id}"
# so pieces/connectors from different puzzles never collide.
# The domain model always uses the local (short) IDs.

def _g(puzzle_id: str, local_id: str) -> str:
    """Local → global Neo4j node ID."""
    return f"{puzzle_id}__{local_id}"


def _l(puzzle_id: str, global_id: str) -> str:
    """Global Neo4j node ID → local domain ID."""
    prefix = f"{puzzle_id}__"
    return global_id[len(prefix):] if global_id.startswith(prefix) else global_id


class Neo4jPuzzleRepository:
    """
    Graph schema
    ─────────────────────────────────────────────────────
    (:Puzzle   {id})                          — unique by id (puzzle slug)
    (:Piece    {id, local_id, label, puzzle_id})
               id = "{puzzle_id}__{local_id}"  — globally unique
    (:Connector{id, local_id, label, type, piece_local_id, puzzle_id})
               id = "{puzzle_id}__{local_id}"  — globally unique

    (:Puzzle)-[:CONTAINS]->(:Piece)
    (:Piece)-[:HAS_CONNECTOR]->(:Connector)
    (:Connector)-[:CONNECTS_WITH]->(:Connector)   (both directions stored)

    Constraints
    ─────────────────────────────────────────────────────
    Puzzle.id        UNIQUE
    Piece.id         UNIQUE
    Connector.id     UNIQUE
    """

    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        if GraphDatabase is None:
            raise RuntimeError("Install the neo4j package: pip install neo4j")
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self.database = database

    def close(self) -> None:
        self.driver.close()

    def ping(self) -> bool:
        try:
            with self.driver.session(database=self.database) as s:
                s.run("RETURN 1").single()
            return True
        except Exception:
            return False

    def ensure_constraints(self) -> None:
        queries = [
            "CREATE CONSTRAINT puzzle_id_unique IF NOT EXISTS FOR (n:Puzzle)    REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT piece_id_unique   IF NOT EXISTS FOR (n:Piece)     REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT conn_id_unique    IF NOT EXISTS FOR (n:Connector) REQUIRE n.id IS UNIQUE",
        ]
        with self.driver.session(database=self.database) as s:
            for q in queries:
                s.run(q)

    # ── write ─────────────────────────────────────────────────────────────────

    def seed(self, graph: PuzzleGraph) -> None:
        self.ensure_constraints()
        pid = graph.id
        with self.driver.session(database=self.database) as s:
            # Remove old data for this puzzle
            s.run(
                "MATCH (puz:Puzzle {id:$pid})-[:CONTAINS]->(pc:Piece)-[:HAS_CONNECTOR]->(c:Connector) "
                "DETACH DELETE pc, c",
                pid=pid,
            )
            s.run("MERGE (puz:Puzzle {id:$pid}) SET puz.name=$name, puz.description=$desc",
                  pid=pid, name=graph.name, desc=graph.description)

            for piece in graph.pieces.values():
                s.run(
                    "MATCH (puz:Puzzle {id:$pid}) "
                    "MERGE (pc:Piece {id:$gid}) "
                    "SET pc.local_id=$lid, pc.label=$label, pc.puzzle_id=$pid, pc.available=$available "
                    "MERGE (puz)-[:CONTAINS]->(pc)",
                    pid=pid, gid=_g(pid, piece.id), lid=piece.id, label=piece.label,
                    available=piece.available,
                )

            for conn in graph.connectors.values():
                s.run(
                    "MATCH (pc:Piece {id:$piece_gid}) "
                    "MERGE (c:Connector {id:$gid}) "
                    "SET c.local_id=$lid, c.label=$label, c.type=$type, "
                    "    c.piece_local_id=$plid, c.puzzle_id=$pid "
                    "MERGE (pc)-[:HAS_CONNECTOR]->(c)",
                    pid=pid,
                    gid=_g(pid, conn.id),
                    lid=conn.id,
                    label=conn.label,
                    type=conn.type,
                    plid=conn.piece_id,
                    piece_gid=_g(pid, conn.piece_id),
                )

            for a, b in graph.connections:
                s.run(
                    "MATCH (ca:Connector {id:$ga}), (cb:Connector {id:$gb}) "
                    "MERGE (ca)-[:CONNECTS_WITH]->(cb) "
                    "MERGE (cb)-[:CONNECTS_WITH]->(ca)",
                    ga=_g(pid, a), gb=_g(pid, b),
                )

    def set_piece_availability(self, puzzle_id: str, piece_id: str, available: bool) -> None:
        with self.driver.session(database=self.database) as s:
            s.run(
                "MATCH (pc:Piece {id:$gid}) SET pc.available = $available",
                gid=_g(puzzle_id, piece_id), available=available,
            )

    # ── read ──────────────────────────────────────────────────────────────────

    def list_puzzles(self) -> List[PuzzleGraph]:
        with self.driver.session(database=self.database) as s:
            rows = s.run("MATCH (p:Puzzle) RETURN p.id AS id, p.name AS name, p.description AS desc ORDER BY p.name")
            return [self._load(r["id"], r["name"] or "", r["desc"] or "") for r in rows]

    def get(self, puzzle_id: str) -> PuzzleGraph:
        with self.driver.session(database=self.database) as s:
            row = s.run("MATCH (p:Puzzle {id:$id}) RETURN p.name AS name, p.description AS desc", id=puzzle_id).single()
            if row is None:
                raise KeyError(f"Puzzle not found in Neo4j: {puzzle_id}")
            return self._load(puzzle_id, row["name"] or "", row["desc"] or "")

    def _load(self, puzzle_id: str, name: str, description: str) -> PuzzleGraph:
        with self.driver.session(database=self.database) as s:
            piece_rows = s.run(
                "MATCH (:Puzzle {id:$pid})-[:CONTAINS]->(pc:Piece) RETURN pc ORDER BY pc.local_id",
                pid=puzzle_id,
            )
            pieces = {
                r["pc"]["local_id"]: Piece(
                    id=r["pc"]["local_id"],
                    label=r["pc"]["label"],
                    puzzle_id=puzzle_id,
                    available=r["pc"].get("available", True),
                )
                for r in piece_rows
            }

            conn_rows = s.run(
                "MATCH (:Puzzle {id:$pid})-[:CONTAINS]->(:Piece)-[:HAS_CONNECTOR]->(c:Connector) "
                "RETURN c ORDER BY c.local_id",
                pid=puzzle_id,
            )
            connectors = {
                r["c"]["local_id"]: Connector(
                    id=r["c"]["local_id"],
                    label=r["c"]["label"],
                    type=r["c"]["type"],
                    piece_id=r["c"]["piece_local_id"],
                )
                for r in conn_rows
            }

            # Only fetch each pair once (a.local_id < b.local_id)
            rel_rows = s.run(
                "MATCH (:Puzzle {id:$pid})-[:CONTAINS]->(:Piece)-[:HAS_CONNECTOR]->(ca:Connector)"
                "-[:CONNECTS_WITH]->(cb:Connector) "
                "WHERE ca.puzzle_id = $pid AND cb.puzzle_id = $pid AND ca.local_id < cb.local_id "
                "RETURN ca.local_id AS a, cb.local_id AS b",
                pid=puzzle_id,
            )
            connections = [(r["a"], r["b"]) for r in rel_rows]

        return PuzzleGraph(
            id=puzzle_id,
            name=name,
            description=description,
            pieces=pieces,
            connectors=connectors,
            connections=connections,
        )
