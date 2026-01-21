# review_services/review_query_api.py
"""
Estrazione query recensioni: modalità LOCAL (vLLM + prompt file) o REMOTE (API).
Interfaccia invariata: extract_review_queries(messages, sessionid) -> Dict[str,Any]
"""

from __future__ import annotations
import os, json, logging, re, pathlib, requests
from typing import List, Dict, Any
from core.llm_formatting import format_messages_for_vllm

MODE = os.getenv("REVIEW_API_MODE", "local").lower()   # 'local' | 'remote'
LLM_URL   = os.getenv("LLM_URL",   "http://localhost:8000/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "google/gemma-3-27b-it")

_DEFAULT_PROMPTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "prompts"
PROMPTS_DIR = pathlib.Path(os.getenv("PROMPTS_DIR", _DEFAULT_PROMPTS_DIR))
REV_PROMPT_BASENAME = os.getenv("REVIEWS_PROMPT_BASENAME", "demo-reviews")

REMOTE_URL  = os.getenv("REVIEWS_REMOTE_URL", "http://localhost:9001/api/reviews")
REMOTE_HEAD = {"Content-Type": "application/json"}
if os.getenv("REMOTE_API_KEY"):
    REMOTE_HEAD["X-Authorization"] = os.getenv("REMOTE_API_KEY")

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.I)

def _load_json_prompt(basename: str, field: str = "prompt", fallback: str = "") -> str:
    candidates = [
        PROMPTS_DIR / basename,
        PROMPTS_DIR / f"{basename}.json",
        PROMPTS_DIR / f"{basename}.txt",
    ]
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as fp:
                raw = fp.read()
            obj = json.loads(raw)
            val = obj.get(field)
            if isinstance(val, str) and val.strip():
                logging.info("[reviews_prompt] Caricato '%s' da %s[%s] (%d chars)",
                             basename, path, field, len(val))
                return val
        except FileNotFoundError:
            continue
        except Exception as e:
            logging.error("[reviews_prompt] Errore parsing %s: %s", path, e)
    logging.warning("[reviews_prompt] Uso fallback per '%s' (non trovato/valido)", basename)
    return fallback or '{"needs_reviews": false, "review_queries": []}'

def _call_llm(msgs: List[Dict[str,str]], json_mode=True, max_tok=384) -> str:
    payload = {
        "model": LLM_MODEL,
        "messages": format_messages_for_vllm(msgs),
        "temperature": 0.0 if json_mode else 0.4,
        "top_p": 1.0 if json_mode else 0.9,
        "max_tokens": max_tok,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    logging.debug("[reviews][LLM] req: %.400s", json.dumps(payload, ensure_ascii=False))
    r = requests.post(LLM_URL, json=payload, timeout=90)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def _json_clean_load(s: str):
    if not isinstance(s, str):
        return s
    clean = _FENCE_RE.sub("", s.strip())
    return json.loads(clean)

def _default_resp() -> Dict[str, Any]:
    return {"needs_reviews": False, "review_queries": []}

def _extract_reviews_remote(messages: List[Dict[str,str]], sessionid: str="") -> Dict[str, Any]:
    payload: Dict[str, Any] = {"chat": messages}
    if sessionid:
        payload["sessionid4dataapi"] = sessionid
    try:
        r = requests.post(REMOTE_URL, headers=REMOTE_HEAD, json=payload, timeout=25)
        r.raise_for_status()
        raw_msg = r.json().get("messages", [])
    except Exception as exc:
        logging.error("[review_query_api][remote] errore %s", exc)
        return _default_resp()
    if not raw_msg or not isinstance(raw_msg[0], str):
        logging.warning("[review_query_api][remote] risposta vuota/inesatta: %s", raw_msg)
        return _default_resp()
    try:
        js = _json_clean_load(raw_msg[0])
        if isinstance(js, dict) and "needs_reviews" in js:
            return js
    except Exception as exc:
        logging.error("[review_query_api][remote] JSON malformato: %s", exc)
    return _default_resp()

def _extract_reviews_local(messages: List[Dict[str,str]], sessionid: str="") -> Dict[str, Any]:
    prompt = _load_json_prompt(REV_PROMPT_BASENAME, field="prompt")
    sys_msg = {"role": "system", "content": prompt}
    msgs = [sys_msg] + (messages or [])
    try:
        out = _call_llm(msgs, json_mode=True, max_tok=512)
        js  = _json_clean_load(out)
        if isinstance(js, dict) and "needs_reviews" in js:
            return js
    except Exception as exc:
        logging.error("[review_query_api][local] errore %s", exc)
    return _default_resp()

def extract_review_queries(messages: List[Dict[str, str]], sessionid: str = "") -> Dict[str, Any]:
    """
    Ritorna: {"needs_reviews": bool, "review_queries": [...]}
    Fallback: se local fallisce/vuota, prova remote.
    """
    if MODE == "local":
        js = _extract_reviews_local(messages, sessionid)
        if js and isinstance(js, dict):
            return js
        logging.warning("[review_query_api] Local vuoto → fallback remoto")
        return _extract_reviews_remote(messages, sessionid)
    else:
        return _extract_reviews_remote(messages, sessionid)
