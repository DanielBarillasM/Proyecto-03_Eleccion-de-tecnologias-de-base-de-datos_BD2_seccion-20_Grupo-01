import json
from pathlib import Path

from app.config import PROJECT_ROOT, load_settings
from app.models import Connector, Piece, PuzzleGraph
from app.neo4j import Neo4jPuzzleRepository

DATA_FILE = PROJECT_ROOT / "data" / "default_puzzles.json"


def load_puzzle(puzzle: dict) -> PuzzleGraph:
    pieces = {p["id"]: Piece(id=p["id"], label=p["label"], puzzle_id=puzzle["id"]) for p in puzzle["pieces"]}
    connectors = {c["id"]: Connector(id=c["id"], label=c["label"], type=c["type"], piece_id=c["piece_id"]) for c in puzzle["connectors"]}
    return PuzzleGraph(
        id=puzzle["id"],
        name=puzzle["name"],
        description=puzzle["description"],
        pieces=pieces,
        connectors=connectors,
        connections=[tuple(cn) for cn in puzzle["connections"]],
    )


def main() -> None:
    settings = load_settings()
    repo = Neo4jPuzzleRepository(settings.neo4j_uri, settings.neo4j_username, settings.neo4j_password, settings.neo4j_database)

    if not repo.ping():
        print("Could not connect to Neo4j — check your .env settings.")
        return

    puzzles = json.loads(DATA_FILE.read_text())["puzzles"]
    for puzzle in puzzles:
        graph = load_puzzle(puzzle)
        repo.seed(graph)
        print(f"  seeded: {graph.name} ({len(graph.pieces)} pieces, {len(graph.connections)} connections)")

    repo.close()
    print("Done.")


if __name__ == "__main__":
    main()
