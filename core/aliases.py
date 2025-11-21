# services/aliases.py
"""
Mappa sinonimi (alias) a nomi canonici per i piatti e le bevande.

Funzione:
• resolve(name) → restituisce il nome ufficiale del prodotto,
  utile per unificare input utente diversi (es. “coke” → “coca cola”)
"""

# Dizionario canonico → alias (lista di sinonimi)
_aliases = {
    "edamame agrumato": ["edamame", "edamame lime"],
    "gyoza verde": ["gyoza", "ravioli giapponesi", "dumpling"],
    "gamberi croccanti panko": ["gamberi panko", "tempura gambero", "gamberi croccanti"],
    "ramen shoyu vegetale": ["ramen vegetale", "ramen shoyu", "ramen"],
    "ceviche yuzu": ["ceviche yuzu", "ceviche agrumato"],
    "ceviche tropicale": ["ceviche mango", "ceviche cocco", "ceviche tropicale"],
    "uramaki yuzu salmon": ["yuzu salmon", "yuzu roll", "salmone yuzu"],
    "uramaki crispy shrimp": ["tempura roll", "gambero roll", "crispy shrimp"],
    "uramaki green garden": ["roll vegan", "veg roll", "garden roll"],
    "uramaki sunburn": ["sunburn roll", "uramaki piccante", "tonno piccante"],
    "futomaki tempura eb": ["futomaki gambero", "futomaki tempura"],
    "futomaki dragon veg": ["dragon veg", "futomaki veg", "roll dragon"],
    "roll di manzo tataki": ["manzo tataki", "sushi di carne manzo"],
    "roll pollo yakitori": ["yakitori roll", "pollo roll"],
    "tartare salmone mango": ["tartare salmone", "salmone mango"],
    "tartare tonno shichimi": ["tartare tonno", "tonno piccante"],
    "rainbow veg bowl": ["veg bowl", "bowl vegetariana"],
    "miso bowl arrosto": ["miso bowl", "bento miso"],
    "mochi yuzu": ["mochi", "mochi gelato"],
    "torta cioccolato al miso": ["torta miso", "dolce cioccolato"],
    "yuzu spritz": ["spritz yuzu", "cocktail yuzu"],
    "gin pepe rosa": ["gin tonic", "gin rosa"],
    "birra lager di riso": ["lager riso", "birra riso"],
    "kombucha ginger": ["kombucha", "kombucha zenzero"],
    "tè verde freddo": ["te verde", "te freddo"],
}

# Inverte la mappatura per risalire all’alias
_inv = {alias: canon for canon, lst in _aliases.items() for alias in lst}

def resolve(name: str) -> str:
    """
    Restituisce il nome canonico per un alias (case-insensitive),
    oppure il nome stesso se già canonico o non trovato.
    """
    return _inv.get(name.lower(), name.lower())
