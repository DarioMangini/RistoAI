# core/vector_table.py
from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence

from psycopg2 import sql as psql

from core.vector_client import get_embedding, _run

ALLOWED_TABLES = {"menu", "recensioni"}

# Colonne reali dalle tabelle (vedi core/models.py)
_ALLOWED_FIELDS: dict[str, set[str]] = {
    "menu": {"id", "name", "type", "ingredients", "description", "price"},
    "recensioni": {"id", "voto", "recensione", "piatti"},
}

_DEFAULT_FIELDS: dict[str, list[str]] = {
    "menu": ["id", "name", "type", "ingredients", "description", "price"],
    "recensioni": ["id", "voto", "recensione", "piatti"],
}

# Se vuoi tenere extra_score_sql, NON accettare SQL arbitrario: allowlist.
_ALLOWED_EXTRA_SCORE_SQL: dict[str, set[str]] = {
    "menu": set(),
    "recensioni": {"(voto / 5.0) * 0.3"},  # come in review_services/vector_db_reviews.py
}


def _parse_fields(table: str, fields: str | Sequence[str] | None) -> list[str]:
    if not fields or fields == "*":
        return list(_DEFAULT_FIELDS[table])

    if isinstance(fields, str):
        cols = [c.strip() for c in fields.split(",") if c.strip()]
    else:
        cols = [str(c).strip() for c in fields if str(c).strip()]

    # blocca qualsiasi cosa non sia una colonna nota
    unknown = set(cols) - _ALLOWED_FIELDS[table]
    if unknown:
        raise ValueError(f"Invalid field(s) for table '{table}': {sorted(unknown)}")

    return cols


def search_table(
    query: str,
    *,
    table: str,
    fields: str | Sequence[str] | None = "*",
    k: int = 5,
    extra_score_sql: str = "",
) -> List[Dict[str, Any]]:
    """
    Cerca corrispondenze semantiche in una tabella Postgres con colonna pgvector.

    - table e columns sono whitelistati (no SQL injection)
    - embedding e k sono parametrici
    - extra_score_sql è allowlistato (evita SQL fragment arbitrari)
    """
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Invalid table: {table}")

    cols = _parse_fields(table, fields)
    fields_sql = psql.SQL(", ").join(psql.Identifier(c) for c in cols)

    # embedding: lo passiamo come stringa vettore e castiamo a ::vector in SQL
    emb = get_embedding(query)
    emb_str = "[" + ",".join(f"{x:.6f}" for x in emb) + "]"

    sim_expr = psql.SQL("(1 - (embedding <=> {emb}::vector))").format(
        emb=psql.Placeholder("emb")
    )

    if extra_score_sql:
        if extra_score_sql not in _ALLOWED_EXTRA_SCORE_SQL.get(table, set()):
            raise ValueError("extra_score_sql not allowed for this table")
        score_expr = psql.SQL("({sim} + ({extra}))").format(
            sim=sim_expr,
            extra=psql.SQL(extra_score_sql),
        )
    else:
        score_expr = sim_expr

    stmt = psql.SQL(
        """
        SELECT {fields},
               {sim}   AS cos_sim,
               {score} AS score
        FROM   {table}
        ORDER  BY score DESC
        LIMIT  {k};
        """
    ).format(
        fields=fields_sql,
        sim=sim_expr,
        score=score_expr,
        table=psql.Identifier(table),
        k=psql.Placeholder("k"),
    )

    logging.debug("[vector_table] search %s query_len=%d k=%d", table, len(query or ""), k)
    return _run(stmt, {"emb": emb_str, "k": k}, dict_cursor=True)
