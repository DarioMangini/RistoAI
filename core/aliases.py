# services/aliases.py
"""
Mappa sinonimi (alias) a nomi canonici per i piatti e le bevande.

Funzione:
• resolve(name) → restituisce il nome ufficiale del prodotto,
  utile per unificare input utente diversi (es. “coke” → “coca cola”)
"""

# Dizionario canonico → alias (lista di sinonimi)
_aliases = {
    "tacos sushi": ["tacos", "tacos sushi", "sushi tacos"],
    "coca cola": ["coca", "cola", "cocacola", "coca-cola", "coca zero", "coke"],
    "coca cola zero": ["coca zero", "coke zero", "zero"],
    "fanta": ["fanta", "aranciata"],
    "sprite": ["sprite", "gassosa", "limonata"],
    "birra asahi": ["asahi", "birra giapponese"],
    "birra corona": ["corona"],
    "birra becks": ["becks"],
    "acqua": ["acqua", "bottiglia acqua", "naturale", "frizzante"],
    "uramaki salmone": ["uramaki salmone", "roll salmone", "salmone roll"],
    "uramaki tonno": ["uramaki tonno", "roll tonno", "tonno roll"],
    "uramaki gambero": ["uramaki gambero", "roll gambero", "gambero roll", "tempura roll"],
    "hosomaki salmone": ["hosomaki salmone", "roll sottile salmone"],
    "hosomaki tonno": ["hosomaki tonno", "roll sottile tonno"],
    "ceviche tonno": ["ceviche tonno", "tonno lime", "tonno crudo"],
    "gyozas": ["gyoza", "ravioli giapponesi", "ravioli"],
    "tataki tonno": ["tataki", "tonno scottato"],
    "sashimi misto": ["sashimi mix", "sashimi assortito"],
    "nighiri salmone": ["nighiri al salmone", "nigiri con salmone"],
    "nighiri tonno": ["nighiri al tonno", "nigiri con tonno"],
    "nighiri branzino": ["nighiri al branzino", "nigiri con branzino"],
    "tartare salmone": ["tartare salmone", "salmone tritato", "tartare di salmone"],
    "edamame": ["edamame", "fagioli soia"],
    "yakisoba pollo": ["yakisoba pollo", "spaghetti pollo"],
    "yakisoba gamberi": ["yakisoba gamberi", "spaghetti gamberi"],
    "yakisoba vegan": ["yakisoba vegan", "spaghetti vegetariani", "vegan soba"],
    "distinto roll": ["distinto", "special roll", "distinto roll"],
    "mojito": ["mojito", "cocktail menta"],
    "spritz": ["spritz", "aperol"],
    "cheesecake fragola": ["cheesecake", "dolce fragola", "torta fragole"],
    "galapagos": ["galapagos", "tacos galapagos", "taco gambero salmone"],
    "platamole": ["platamole", "chips platano", "chips banana"],
    "mazzancolle panko e maio" : ["mazzancolle panko", "gamberi panko", "mazzancolle fritte"]
}

# Inverte la mappatura per risalire all’alias
_inv = {alias: canon for canon, lst in _aliases.items() for alias in lst}

def resolve(name: str) -> str:
    """
    Restituisce il nome canonico per un alias (case-insensitive),
    oppure il nome stesso se già canonico o non trovato.
    """
    return _inv.get(name.lower(), name.lower())
