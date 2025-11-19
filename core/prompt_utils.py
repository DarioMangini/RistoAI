# services/prompt_utils.py
"""
Funzioni di supporto al prompt engineering:
• Gestione dei loop [loop nome=1]...[/loop]
• Condizionali [if nome]...[/if]
• Correzione encoding italiano (tipico dei modelli LLM)
"""

import re, logging
from typing import Dict, List, Any

# ------------------------------------------------------------------ #
def fill_prompt_loop(prompt: str,
                     items: List[Dict[str, Any]],
                     loop_name: str = "menu") -> str:
    """
    Sostituisce il blocco [loop nome=1]…[/loop] duplicandolo per ogni item.
    Ogni campo {campo} viene rimpiazzato dinamicamente.
    """
    patt = rf'\[loop\s+{re.escape(loop_name)}=1\](.*?)\[/loop\]'
    m = re.search(patt, prompt, re.DOTALL)
    if not m:
        return prompt

    block, rendered = m.group(1), ""
    for itm in items:
        line = block
        for f, v in itm.items():
            if isinstance(v, list):
                v = ", ".join(v)
            line = line.replace(f"{{{f}}}", str(v))
        rendered += line + "\n"

    return prompt.replace(m.group(0), rendered)

# ------------------------------------------------------------------ #
def process_conditional_blocks(prompt: str, vars: Dict[str, Any]) -> str:
    """
    Valuta i blocchi condizionali del prompt ([if x]...[/if]) in base alle variabili.
    """
    def cond_ok(cond: str) -> bool:
        if '=' in cond:
            k, v = [x.strip() for x in cond.split('=', 1)]
            return vars.get(k) == v
        return bool(vars.get(cond.strip()))

    def _inner(txt: str) -> str:
        patt = r'\[if\s+([^\]]+)\](.*?)\[/if\]'
        while (m := re.search(patt, txt, re.DOTALL)):
            cond, body = m.group(1), m.group(2)
            repl = _inner(body) if cond_ok(cond) else ""
            txt = txt[:m.start()] + repl + txt[m.end():]
        return txt

    return _inner(prompt)

# ------------------------------------------------------------------ #
def fix_italian_encoding(text: str) -> str:
    """
    Corregge problemi comuni di encoding italiano (es. “Ã¨” → “è”).
    """
    rep = {'Ã²':'ò','Ã¨':'è','Ã¬':'ì','Ã¹':'ù','Ã':'à',
           "a'":'à',"e'":'è',"i'":'ì',"o'":'ò',"u'":'ù'}
    for wrong, right in rep.items():
        text = text.replace(wrong, right)
    return text
