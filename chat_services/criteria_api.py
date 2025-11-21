# services/criteria_api.py
"""
Estrazione criteri: modalità LOCAL (vLLM + prompt file) o REMOTE (API).
Interfaccia invariata: extract_criteria(messages, sessionid) -> List[dict]
"""

from __future__ import annotations
import os, json, logging, re, pathlib, requests
from typing import List, Dict, Any
from core.llm_formatting import format_messages_for_vllm

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────
MODE = os.getenv("CRITERIA_API_MODE", "local").lower()   # 'local' | 'remote'
LLM_URL   = os.getenv("LLM_URL",   "http://localhost:8000/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "google/gemma-3-27b-it")

_DEFAULT_PROMPTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "prompts"
PROMPTS_DIR = pathlib.Path(os.getenv("PROMPTS_DIR", _DEFAULT_PROMPTS_DIR))
CRIT_PROMPT_BASENAME = os.getenv("CRITERIA_PROMPT_BASENAME", "demo-criteria")

REMOTE_URL  = os.getenv("CRITERIA_REMOTE_URL", "http://localhost:9001/api/criteria")
REMOTE_HEAD = {"Content-Type": "application/json"}
if os.getenv("REMOTE_API_KEY"):
    REMOTE_HEAD["X-Authorization"] = os.getenv("REMOTE_API_KEY")


# ─────────────────────────────────────────────────────────────
# Prompt loader (JSON -> campo "prompt")
# ─────────────────────────────────────────────────────────────
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
                logging.info("[criteria_prompt] Caricato '%s' da %s[%s] (%d chars)",
                             basename, path, field, len(val))
                return val
        except FileNotFoundError:
            continue
        except Exception as e:
            logging.error("[criteria_prompt] Errore parsing %s: %s", path, e)
    logging.warning("[criteria_prompt] Uso fallback per '%s' (non trovato/valido)", basename)
    return fallback or '{"note":"fallback"}'


# ─────────────────────────────────────────────────────────────
# vLLM wrapper
# ─────────────────────────────────────────────────────────────
def _call_llm(msgs: List[Dict[str,str]], json_mode=True, max_tok=512) -> str:
    payload = {
        "model": LLM_MODEL,
        "messages": format_messages_for_vllm(msgs),
        "temperature": 0.0 if json_mode else 0.4,
        "top_p": 0.1 if json_mode else 0.9,
        "max_tokens": max_tok,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    logging.debug("[criteria][LLM] req: %.400s", json.dumps(payload, ensure_ascii=False))
    r = requests.post(LLM_URL, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.I)

def _json_clean_load(s: str):
    if not isinstance(s, str):
        return s
    clean = _FENCE_RE.sub("", s.strip())
    return json.loads(clean)

def _ensure_list(obj) -> List[Dict[str, Any]]:
    """Accetta list|dict|string JSON e restituisce sempre List[dict]."""
    if obj is None:
        return []
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        return [obj]
    if isinstance(obj, str):
        try:
            return _ensure_list(_json_clean_load(obj))
        except Exception:
            return []
    return []


# ─────────────────────────────────────────────────────────────
# Implementazioni
# ─────────────────────────────────────────────────────────────
def _extract_criteria_remote(messages: List[Dict[str,str]], sessionid: str="") -> List[Dict[str,Any]]:
    payload: Dict[str, Any] = {"chat": messages}
    if sessionid:
        payload["sessionid4dataapi"] = sessionid
    try:
        r = requests.post(REMOTE_URL, headers=REMOTE_HEAD, json=payload, timeout=25)
        r.raise_for_status()
        raw = r.json().get("messages", [])
    except Exception as exc:
        logging.error("[criteria_api][remote] errore %s", exc)
        return []
    out: List[Dict[str,Any]] = []
    for msg in raw:
        try:
            js = _json_clean_load(msg)
            if isinstance(js, dict):
                out.append(js)
        except Exception:
            logging.warning("[criteria_api][remote] JSON malformato: %.200s", msg)
    return out


def _extract_criteria_local(messages: List[Dict[str,str]], sessionid: str="") -> List[Dict[str,Any]]:
    # Carica il prompt del criterio
    prompt = _load_json_prompt(CRIT_PROMPT_BASENAME, field="prompt")
    # System + history (passiamo tutta la chat come contesto)
    sys_msg = {"role": "system", "content": prompt}
    msgs = [sys_msg] + (messages or [])
    try:
        out = _call_llm(msgs, json_mode=True, max_tok=768)
        parsed = _json_clean_load(out)
        return _ensure_list(parsed)
    except Exception as exc:
        logging.error("[criteria_api][local] errore %s", exc)
        return []


# ─────────────────────────────────────────────────────────────
# API pubblica (interfaccia invariata)
# ─────────────────────────────────────────────────────────────
def extract_criteria(messages: List[Dict[str,str]], sessionid: str = "") -> List[Dict[str,Any]]:
    """
    Ritorna una lista di criteri (dict). Modalità local/remote selezionabile da env.
    Fallback: se local fallisce/vuota, prova remote.
    """
    if MODE == "local":
        res = _extract_criteria_local(messages, sessionid)
        if res:
            return res
        logging.warning("[criteria_api] Local vuoto → fallback remoto")
        return _extract_criteria_remote(messages, sessionid)
    else:
        return _extract_criteria_remote(messages, sessionid)
