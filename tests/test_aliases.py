from core.aliases import resolve

def test_resolve_known_alias():
    # Verifica che un alias noto venga convertito correttamente
    assert resolve("uramaki piccante") == "uramaki sunburn" # [cite: 101]
    assert resolve("coke") == "coca cola" # [cite: 100] (esempio nel commento)

def test_resolve_case_insensitivity():
    # Verifica che la funzione ignori le maiuscole [cite: 104]
    assert resolve("EDAMAME") == "edamame agrumato" # [cite: 100]

def test_resolve_unknown_product():
    # Se il prodotto non è in lista, deve restituire il nome originale in minuscolo [cite: 104]
    assert resolve("Pizza Margherita") == "pizza margherita"

def test_resolve_already_canonical():
    # Se passo già il nome canonico, deve restare invariato
    assert resolve("uramaki green garden") == "uramaki green garden" # [cite: 101]