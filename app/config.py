from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str
    neo4j_database: str


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")
    return Settings(
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_username=os.getenv("NEO4J_USERNAME", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "password"),
        neo4j_database=os.getenv("NEO4J_DATABASE", "neo4j"),
    )
