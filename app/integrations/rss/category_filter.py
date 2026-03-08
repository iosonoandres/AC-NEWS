import unicodedata

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "SPORT": (
        "calcio",
        "serie a",
        "serie b",
        "champions",
        "europa league",
        "basket",
        "tennis",
        "atp",
        "wta",
        "formula 1",
        "f1",
        "motogp",
        "ciclismo",
        "rugby",
        "volley",
        "sci",
        "olimpiadi",
        "paralimpiadi",
        "derby",
        "partita",
        "gara",
        "campionato",
        "classifica",
        "allenatore",
        "squadra",
        "gol",
        "scudetto",
        "podio",
        "ferrari",
        "juventus",
        "inter",
        "milan",
        "napoli",
        "roma",
    ),
    "MODA": (
        "moda",
        "fashion",
        "sfilata",
        "collezione",
        "passerella",
        "look",
        "stile",
        "brand",
        "designer",
        "haute couture",
        "accessori",
    ),
    "ECONOMIA": (
        "economia",
        "mercati",
        "borsa",
        "finanza",
        "finanziari",
        "pil",
        "inflazione",
        "tassi",
        "bce",
        "fisco",
        "manovra",
        "aziende",
        "impresa",
        "startup",
        "dazi",
    ),
    "TECNOLOGIA": (
        "tecnologia",
        "tech",
        "intelligenza artificiale",
        "software",
        "hardware",
        "smartphone",
        "app",
        "chip",
        "cyber",
        "cloud",
        "internet",
        "robot",
        "digitale",
    ),
    "CUCINA": (
        "ricetta",
        "ricette",
        "cucina",
        "cibo",
        "chef",
        "ingredienti",
        "dolce",
        "dessert",
        "forno",
        "pasta",
        "pizza",
        "antipasto",
        "primo",
        "secondo",
        "contorno",
    ),
    "ARTE": (
        "arte",
        "artist",
        "artista",
        "mostra",
        "museo",
        "galleria",
        "pittura",
        "scultura",
        "installazione",
        "biennale",
        "curatore",
        "opera",
    ),
    "MUSICA": (
        "musica",
        "album",
        "singolo",
        "concerto",
        "tour",
        "festival",
        "sanremo",
        "cantante",
        "band",
        "dj",
        "brano",
        "playlist",
    ),
}

CATEGORY_SOURCE_HINTS: dict[str, tuple[str, ...]] = {
    "SPORT": ("gazzetta", "sport", "sky sport", "ansa sport"),
    "MODA": ("vanity", "fashion", "moda"),
    "ECONOMIA": ("sole 24 ore", "economia", "finanza", "wall street"),
    "TECNOLOGIA": ("wired", "tecnologia", "digitale", "tech"),
    "CUCINA": ("giallozafferano", "cookist", "cucina"),
    "ARTE": ("artribune", "exibart", "arte", "cultura"),
    "MUSICA": ("rolling stone", "all music", "soundsblog", "musica"),
}

CATEGORY_MIN_SCORE: dict[str, int] = {
    "SPORT": 2,
    "MODA": 2,
    "ECONOMIA": 1,
    "TECNOLOGIA": 2,
    "CUCINA": 2,
    "ARTE": 2,
    "MUSICA": 2,
}

GLOBAL_OFFTOPIC_KEYWORDS = (
    "guerra",
    "iran",
    "israele",
    "gaza",
    "ucraina",
    "russia",
    "hamas",
    "missile",
    "bombard",
)


def is_relevant_news(category_code: str, title: str, summary: str, source: str) -> bool:
    normalized_text = _normalize(f"{title} {summary}")
    normalized_source = _normalize(source)

    keywords = CATEGORY_KEYWORDS.get(category_code, ())
    source_hints = CATEGORY_SOURCE_HINTS.get(category_code, ())

    score = 0

    for keyword in keywords:
        if _normalize(keyword) in normalized_text:
            score += 2

    for hint in source_hints:
        if _normalize(hint) in normalized_source:
            score += 1
            break

    for keyword in GLOBAL_OFFTOPIC_KEYWORDS:
        if _normalize(keyword) in normalized_text:
            score -= 3

    return score >= CATEGORY_MIN_SCORE.get(category_code, 1)


def _normalize(value: str) -> str:
    lowered = (value or "").strip().lower()
    normalized = unicodedata.normalize("NFKD", lowered)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))
