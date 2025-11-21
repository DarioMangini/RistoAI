# core/llm_formatting.py
"""
Utility per uniformare i messaggi in formato compatibile con le API
chat (OpenAI/vLLM) senza dipendenze da percorsi di sistema esterni.
"""
from __future__ import annotations

from typing import Any, Dict, List

_ALLOWED_ROLES = {"system", "user", "assistant", "tool"}


def _normalize_message(msg: Dict[str, Any] | None) -> Dict[str, Any] | None:
    """
    Restituisce un dict con campi minimi `role` e `content`.
    Ruoli non riconosciuti vengono degradati a `user`.
    """
    if not isinstance(msg, dict):
        return None

    role = msg.get("role") or "user"
    content = msg.get("content", "")

    if role not in _ALLOWED_ROLES:
        role = "user"
    if not isinstance(content, str):
        content = str(content)

    normalized: Dict[str, Any] = {"role": role, "content": content}
    if role == "tool" and "name" in msg:
        normalized["name"] = msg["name"]
    return normalized


def format_messages_for_vllm(messages: List[Dict[str, Any]] | None) -> List[Dict[str, Any]]:
    """
    Converte la lista di messaggi in un formato sicuro/privo di riferimenti
    esterni, scartando eventuali elementi vuoti.
    """
    if not messages:
        return []

    out: List[Dict[str, Any]] = []
    for msg in messages:
        norm = _normalize_message(msg)
        if not norm:
            continue
        if norm["role"] == "system" or norm["content"].strip():
            out.append(norm)
    return out
