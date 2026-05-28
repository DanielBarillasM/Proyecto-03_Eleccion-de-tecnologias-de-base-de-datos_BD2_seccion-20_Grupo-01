from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Piece:
    id: str
    label: str
    puzzle_id: str
    available: bool = True


@dataclass(frozen=True)
class Connector:
    id: str        # globally unique, e.g. "P01_A"
    label: str     # tape label visible on the physical piece, e.g. "A"
    type: str      # "tab" or "hole"
    piece_id: str


@dataclass
class PuzzleGraph:
    id: str
    name: str
    description: str
    pieces: Dict[str, Piece]            # piece_id -> Piece
    connectors: Dict[str, Connector]    # connector_id -> Connector
    connections: List[Tuple[str, str]]  # pairs of connector_ids that fit together

    def piece_connectors(self, piece_id: str) -> List[Connector]:
        return [c for c in self.connectors.values() if c.piece_id == piece_id]

    def connector_neighbors(self) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for a, b in self.connections:
            result[a] = b
            result[b] = a
        return result


@dataclass(frozen=True)
class AssemblyStep:
    step_number: int
    instruction: str
    piece_id: Optional[str] = None
    status: str = "placed"  # "start", "placed", "missing"


@dataclass
class SolveResult:
    puzzle_id: str
    start_piece_id: str
    steps: List[AssemblyStep]
    placed_piece_ids: List[str]
    missing_piece_ids: List[str]

    @property
    def is_complete(self) -> bool:
        return not self.missing_piece_ids
