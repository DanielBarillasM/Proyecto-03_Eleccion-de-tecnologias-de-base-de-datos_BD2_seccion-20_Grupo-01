from __future__ import annotations

from collections import deque
from typing import Iterable, List, Optional, Set

from app.models import AssemblyStep, PuzzleGraph, SolveResult


class PuzzleSolver:
    def solve(
        self,
        graph: PuzzleGraph,
        start_piece_id: str,
        missing_piece_ids: Optional[Iterable[str]] = None,
    ) -> SolveResult:
        if start_piece_id not in graph.pieces:
            raise ValueError(f"Piece {start_piece_id!r} not found in puzzle.")

        missing: Set[str] = set(missing_piece_ids or [])
        if start_piece_id in missing:
            raise ValueError(f"Start piece {start_piece_id!r} is marked missing.")

        neighbor = graph.connector_neighbors()
        # connector_id -> piece_id (reverse lookup)
        conn_piece = {cid: c.piece_id for cid, c in graph.connectors.items()}

        visited: Set[str] = set()
        placed: List[str] = []
        steps: List[AssemblyStep] = []
        step_no = 1

        start = graph.pieces[start_piece_id]
        steps.append(AssemblyStep(
            step_number=step_no,
            instruction=f"Place piece {start.label} as the starting piece.",
            piece_id=start_piece_id,
            status="start",
        ))
        step_no += 1
        visited.add(start_piece_id)
        placed.append(start_piece_id)

        queue: deque[str] = deque([start_piece_id])
        reported_missing: Set[str] = set()

        while queue:
            current_id = queue.popleft()
            current = graph.pieces[current_id]

            for conn in graph.piece_connectors(current_id):
                partner_id = neighbor.get(conn.id)
                if partner_id is None:
                    continue
                next_piece_id = conn_piece.get(partner_id)
                if next_piece_id is None or next_piece_id == current_id:
                    continue

                partner_conn = graph.connectors[partner_id]
                next_piece = graph.pieces.get(next_piece_id)
                if next_piece is None:
                    continue

                if next_piece_id in missing:
                    if next_piece_id not in reported_missing:
                        reported_missing.add(next_piece_id)
                        steps.append(AssemblyStep(
                            step_number=step_no,
                            instruction=(
                                f"[MISSING] Piece {next_piece.label} should connect "
                                f"its {partner_conn.type} '{partner_conn.label}' to "
                                f"{conn.type} '{conn.label}' of piece {current.label}, "
                                f"but it is missing."
                            ),
                            piece_id=next_piece_id,
                            status="missing",
                        ))
                        step_no += 1
                    continue

                if next_piece_id in visited:
                    continue

                visited.add(next_piece_id)
                placed.append(next_piece_id)
                steps.append(AssemblyStep(
                    step_number=step_no,
                    instruction=(
                        f"Take piece {next_piece.label}, connect its "
                        f"{partner_conn.type} '{partner_conn.label}' to "
                        f"{conn.type} '{conn.label}' of piece {current.label}."
                    ),
                    piece_id=next_piece_id,
                    status="placed",
                ))
                step_no += 1
                queue.append(next_piece_id)

        # Unreachable available pieces (disconnected from start due to missing pieces)
        for pid in graph.pieces:
            if pid not in visited and pid not in missing:
                piece = graph.pieces[pid]
                steps.append(AssemblyStep(
                    step_number=step_no,
                    instruction=(
                        f"Piece {piece.label} is available but unreachable from the "
                        f"starting piece (blocked by a missing piece or disconnected)."
                    ),
                    piece_id=pid,
                    status="missing",
                ))
                step_no += 1

        return SolveResult(
            puzzle_id=graph.id,
            start_piece_id=start_piece_id,
            steps=steps,
            placed_piece_ids=placed,
            missing_piece_ids=sorted(missing),
        )
