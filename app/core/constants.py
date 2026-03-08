from enum import Enum


class Category(str, Enum):
    SPORT = "Sport"
    MODA = "Moda"
    ECONOMIA = "Economia"
    TECNOLOGIA = "Tecnologia"
    CUCINA = "Cucina"
    ARTE = "Arte"
    MUSICA = "Musica"


CATEGORY_BY_CODE = {
    "SPORT": Category.SPORT,
    "MODA": Category.MODA,
    "ECONOMIA": Category.ECONOMIA,
    "TECNOLOGIA": Category.TECNOLOGIA,
    "CUCINA": Category.CUCINA,
    "ARTE": Category.ARTE,
    "MUSICA": Category.MUSICA,
}

CATEGORY_CODE_BY_VALUE = {value.value: code for code, value in CATEGORY_BY_CODE.items()}
CATEGORIES_ORDER = list(CATEGORY_BY_CODE.items())


def normalize_category_code(raw: str | None) -> str | None:
    if not raw:
        return None

    if raw in CATEGORY_BY_CODE:
        return raw

    return CATEGORY_CODE_BY_VALUE.get(raw)
