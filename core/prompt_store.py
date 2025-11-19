# core/prompt_store.py
import functools, logging
from psycopg2.errors import UndefinedTable
from core.vector_client import _run
from core.db_router     import map_project_to_db, set_current_db, get_current_db

@functools.lru_cache(maxsize=8)
def get_prompt(project: str | None) -> str:
    """
    Restituisce il prompt più aggiornato per il progetto richiesto.
    • Mappa 'sushi' → DB ristosushi_it, ecc.
    • ORDER BY updated_at DESC così, se togli il UNIQUE e tieni versioni,
      pescherai sempre la più fresca.
    • Se la tabella non esiste, ritorna "" e il chiamante userà il payload.
    """
    # Normalizza/mappa progetto → DB
    db_name  = map_project_to_db(project)
    # Se il chiamante non ha ancora impostato il DB, fallo tu (safe-reuse).
    if get_current_db() != db_name:
        set_current_db(project)

    sql = """
        SELECT prompt_txt
        FROM   prompt
        WHERE  project = %s
        ORDER  BY created_at DESC
        LIMIT  1;
    """
    try:
        rows = _run(sql, (project or "sushi",))
        return rows[0][0] if rows else ""
    except UndefinedTable:
        logging.warning("Tabella prompt assente in DB %s – fallback al payload", db_name)
        return ""
