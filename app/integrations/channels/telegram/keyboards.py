from app.core.constants import CATEGORIES_ORDER

CATEGORY_EMOJI_BY_CODE = {
    "SPORT": "🏅",
    "MODA": "👗",
    "ECONOMIA": "💶",
    "TECNOLOGIA": "💻",
    "CUCINA": "🍝",
    "ARTE": "🎨",
    "MUSICA": "🎵",
}


def registration_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "📝 Registrati", "callback_data": "register"}],
            [{"text": "🔐 Login", "callback_data": "login"}],
        ]
    }


def login_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "🔐 Login", "callback_data": "login"}],
            [{"text": "📝 Registrati", "callback_data": "register"}],
        ]
    }


def categories_keyboard() -> dict:
    buttons: list[list[dict[str, str]]] = []
    row: list[dict[str, str]] = []

    for idx, (category_code, category) in enumerate(CATEGORIES_ORDER, start=1):
        emoji = CATEGORY_EMOJI_BY_CODE.get(category_code, "📰")
        row.append(
            {
                "text": f"{emoji} {category.value}",
                "callback_data": f"category:{category_code}",
            }
        )
        if idx % 2 == 0:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([{"text": "🚪 Logout", "callback_data": "logout"}])
    return {"inline_keyboard": buttons}


def news_navigation_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "➡️ Prossima notizia", "callback_data": "next"}],
            [
                {"text": "💬 Commenta", "callback_data": "comment"},
                {"text": "🗂️ Vedi commenti", "callback_data": "view_comments"},
            ],
            [
                {"text": "⭐️1", "callback_data": "rate:1"},
                {"text": "⭐️2", "callback_data": "rate:2"},
                {"text": "⭐️3", "callback_data": "rate:3"},
                {"text": "⭐️4", "callback_data": "rate:4"},
                {"text": "⭐️5", "callback_data": "rate:5"},
            ],
            [{"text": "🧭 Cambia categoria", "callback_data": "choose_category"}],
            [{"text": "🚪 Logout", "callback_data": "logout"}],
        ]
    }
