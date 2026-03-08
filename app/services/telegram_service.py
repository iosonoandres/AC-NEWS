from html import escape

from app.core.constants import CATEGORY_BY_CODE, normalize_category_code
from app.domain.models import NewsItem, UserSession
from app.integrations.channels.telegram.client import TelegramClient
from app.integrations.channels.telegram.keyboards import (
    categories_keyboard,
    login_keyboard,
    news_navigation_keyboard,
    registration_keyboard,
)
from app.services.auth_service import (
    PENDING_COMMENT,
    PENDING_LOGIN_PASSWORD,
    PENDING_LOGIN_USERNAME,
    PENDING_REGISTER_PASSWORD,
    PENDING_REGISTER_USERNAME,
    AuthService,
)
from app.services.feedback_service import FeedbackService
from app.services.news_service import NewsService


class TelegramBotService:
    def __init__(
        self,
        auth_service: AuthService,
        news_service: NewsService,
        feedback_service: FeedbackService,
        telegram_client: TelegramClient,
    ) -> None:
        self.auth_service = auth_service
        self.news_service = news_service
        self.feedback_service = feedback_service
        self.telegram_client = telegram_client

    async def handle_update(self, update: dict) -> None:
        if "callback_query" in update:
            await self._handle_callback_query(update["callback_query"])
            return

        if "message" in update:
            await self._handle_message(update["message"])

    async def _handle_message(self, message: dict) -> None:
        text = (message.get("text") or "").strip()
        chat = message.get("chat") or {}
        from_user = message.get("from") or {}
        chat_id = chat.get("id")
        telegram_id = from_user.get("id")

        if not chat_id or not telegram_id:
            return

        telegram_id = int(telegram_id)
        session = self.auth_service.ensure_session(from_user)

        if text in {"/start", "/help"}:
            await self._send_welcome(chat_id, from_user, session)
            return

        if text == "/logout":
            self.auth_service.logout_session(telegram_id)
            await self.telegram_client.send_message(
                chat_id,
                "🚪 Logout effettuato.",
                reply_markup=login_keyboard(),
            )
            return

        if text and not text.startswith("/"):
            handled = await self._handle_pending_text(chat_id, telegram_id, session, text)
            if handled:
                return

        if text in {"/categorie", "/categories"}:
            if await self._require_logged(chat_id, session):
                await self.telegram_client.send_message(
                    chat_id,
                    "🧭 Scegli una categoria:",
                    reply_markup=categories_keyboard(),
                )
            return

        if text in {"/news", "/next"}:
            if await self._require_logged(chat_id, session) and session.selected_category:
                await self._send_next_news(chat_id, telegram_id)
            elif session.is_logged_in:
                await self.telegram_client.send_message(
                    chat_id,
                    "Prima scegli una categoria di notizie.",
                    reply_markup=categories_keyboard(),
                )
            return

        await self._send_default_message(chat_id, session)

    async def _handle_pending_text(self, chat_id: int, telegram_id: int, session: UserSession, text: str) -> bool:
        state = session.pending_state

        if state == PENDING_REGISTER_USERNAME:
            ok, msg = self.auth_service.submit_registration_username(telegram_id, text)
            await self.telegram_client.send_message(chat_id, msg)
            return True

        if state == PENDING_REGISTER_PASSWORD:
            ok, msg = self.auth_service.submit_registration_password(telegram_id, text)
            if ok:
                await self.telegram_client.send_message(
                    chat_id,
                    f"✅ {msg} Ora scegli una categoria.",
                    reply_markup=categories_keyboard(),
                )
            else:
                await self.telegram_client.send_message(chat_id, msg)
            return True

        if state == PENDING_LOGIN_USERNAME:
            ok, msg = self.auth_service.submit_login_username(telegram_id, text)
            await self.telegram_client.send_message(chat_id, msg)
            return True

        if state == PENDING_LOGIN_PASSWORD:
            ok, msg = self.auth_service.submit_login_password(telegram_id, text)
            if ok:
                await self.telegram_client.send_message(
                    chat_id,
                    f"✅ {msg}",
                    reply_markup=categories_keyboard(),
                )
            else:
                await self.telegram_client.send_message(chat_id, msg)
            return True

        if state == PENDING_COMMENT:
            ok, msg, news_id = self.auth_service.consume_comment_flow(telegram_id, text)
            if not ok:
                await self.telegram_client.send_message(chat_id, msg)
                return True

            updated = self.auth_service.get_session(telegram_id)
            if not updated or not updated.account_username:
                await self.telegram_client.send_message(chat_id, "Sessione non valida. Rifai login.")
                return True

            comment_count = self.feedback_service.add_comment(news_id, updated.account_username, text.strip())
            await self.telegram_client.send_message(
                chat_id,
                f"💬 Commento salvato. Totale commenti su questa notizia: {comment_count}",
                reply_markup=news_navigation_keyboard(),
            )
            return True

        return False

    async def _handle_callback_query(self, callback_query: dict) -> None:
        callback_id = callback_query.get("id")
        data = (callback_query.get("data") or "").strip()
        from_user = callback_query.get("from") or {}
        message = callback_query.get("message") or {}
        chat = message.get("chat") or {}

        chat_id = chat.get("id")
        telegram_id = from_user.get("id")
        if not callback_id or not chat_id or not telegram_id:
            return

        telegram_id = int(telegram_id)
        session = self.auth_service.ensure_session(from_user)

        if data == "register":
            self.auth_service.start_registration(from_user)
            await self.telegram_client.answer_callback_query(callback_id, "Registrazione")
            await self.telegram_client.send_message(
                chat_id,
                "📝 Inserisci username (3-20 caratteri: lettere, numeri, underscore).",
            )
            return

        if data == "login":
            self.auth_service.start_login(from_user)
            await self.telegram_client.answer_callback_query(callback_id, "Login")
            await self.telegram_client.send_message(
                chat_id,
                "🔐 Inserisci username.",
            )
            return

        if data == "logout":
            self.auth_service.logout_session(telegram_id)
            await self.telegram_client.answer_callback_query(callback_id, "Logout effettuato")
            await self.telegram_client.send_message(
                chat_id,
                "🚪 Logout effettuato.",
                reply_markup=login_keyboard(),
            )
            return

        if data == "choose_category":
            if await self._require_logged_callback(chat_id, callback_id, session):
                await self.telegram_client.answer_callback_query(callback_id)
                await self.telegram_client.send_message(
                    chat_id,
                    "🧭 Scegli una categoria:",
                    reply_markup=categories_keyboard(),
                )
            return

        if data.startswith("category:"):
            if not await self._require_logged_callback(chat_id, callback_id, session):
                return

            category_code = normalize_category_code(data.split(":", 1)[1])
            if not category_code:
                await self.telegram_client.answer_callback_query(callback_id, "Categoria non valida", show_alert=True)
                return

            self.auth_service.set_selected_category(telegram_id, category_code)
            await self.telegram_client.answer_callback_query(callback_id, "Categoria aggiornata")
            await self._send_next_news(chat_id, telegram_id)
            return

        if data == "next":
            if not await self._require_logged_callback(chat_id, callback_id, session):
                return

            if not session.selected_category:
                await self.telegram_client.answer_callback_query(callback_id)
                await self.telegram_client.send_message(
                    chat_id,
                    "Seleziona prima una categoria.",
                    reply_markup=categories_keyboard(),
                )
                return

            await self.telegram_client.answer_callback_query(callback_id)
            await self._send_next_news(chat_id, telegram_id)
            return

        if data == "comment":
            if not await self._require_logged_callback(chat_id, callback_id, session):
                return

            if not session.current_news_id:
                await self.telegram_client.answer_callback_query(callback_id, "Apri prima una notizia", show_alert=True)
                return

            self.auth_service.start_comment_flow(telegram_id, session.current_news_id)
            await self.telegram_client.answer_callback_query(callback_id)
            await self.telegram_client.send_message(
                chat_id,
                "💬 Scrivi ora il tuo commento e invialo come messaggio.",
            )
            return

        if data == "view_comments":
            if not await self._require_logged_callback(chat_id, callback_id, session):
                return

            if not session.current_news_id:
                await self.telegram_client.answer_callback_query(callback_id, "Apri prima una notizia", show_alert=True)
                return

            comments = self.feedback_service.list_comments(session.current_news_id, limit=10)
            await self.telegram_client.answer_callback_query(callback_id)
            if not comments:
                await self.telegram_client.send_message(chat_id, "🗂️ Nessun commento per questa notizia.")
                return

            await self.telegram_client.send_message(chat_id, self._format_comments_message(comments))
            return

        if data.startswith("rate:"):
            if not await self._require_logged_callback(chat_id, callback_id, session):
                return

            if not session.current_news_id:
                await self.telegram_client.answer_callback_query(callback_id, "Apri prima una notizia", show_alert=True)
                return

            try:
                value = int(data.split(":", 1)[1])
            except (TypeError, ValueError):
                await self.telegram_client.answer_callback_query(callback_id, "Valutazione non valida", show_alert=True)
                return

            average, votes = self.feedback_service.rate_news(session.current_news_id, session.account_username, value)
            await self.telegram_client.answer_callback_query(callback_id, f"Hai votato {value}⭐")
            await self.telegram_client.send_message(
                chat_id,
                f"⭐ Valutazione media aggiornata: {average:.2f}/5 ({votes} voti)",
                reply_markup=news_navigation_keyboard(),
            )
            return

        await self.telegram_client.answer_callback_query(callback_id, "Azione non riconosciuta")

    async def _send_default_message(self, chat_id: int, session: UserSession | None) -> None:
        if not session or not session.is_logged_in:
            await self.telegram_client.send_message(
                chat_id,
                "Per usare il bot devi registrarti o fare login.",
                reply_markup=registration_keyboard(),
            )
            return

        if not session.selected_category:
            await self.telegram_client.send_message(
                chat_id,
                "Seleziona una categoria per iniziare.",
                reply_markup=categories_keyboard(),
            )
            return

        await self.telegram_client.send_message(
            chat_id,
            "Usa i pulsanti qui sotto per continuare.",
            reply_markup=news_navigation_keyboard(),
        )

    async def _send_welcome(self, chat_id: int, from_user: dict, session: UserSession | None) -> None:
        name = escape((from_user.get("first_name") or from_user.get("username") or "utente"))

        if not session or not session.is_logged_in:
            await self.telegram_client.send_message(
                chat_id,
                f"Ciao {name}. Benvenuto su AC-NEWS. Registrati oppure fai login.",
                reply_markup=registration_keyboard(),
            )
            return

        if not session.selected_category:
            await self.telegram_client.send_message(
                chat_id,
                f"Bentornato {name}. Scegli una categoria:",
                reply_markup=categories_keyboard(),
            )
            return

        await self.telegram_client.send_message(
            chat_id,
            f"Bentornato {name}. Sei pronto a leggere le news.",
            reply_markup=news_navigation_keyboard(),
        )

    async def _send_next_news(self, chat_id: int, telegram_id: int) -> None:
        session = self.auth_service.get_session(telegram_id)
        if not session or not session.selected_category:
            await self.telegram_client.send_message(
                chat_id,
                "Scegli prima una categoria.",
                reply_markup=categories_keyboard(),
            )
            return

        category_code = normalize_category_code(session.selected_category)
        if not category_code:
            await self.telegram_client.send_message(
                chat_id,
                "Categoria non valida. Selezionane una nuova.",
                reply_markup=categories_keyboard(),
            )
            return

        cursor = self.auth_service.get_user_cursor(telegram_id, category_code)
        item, next_cursor, total = await self.news_service.get_next_news(category_code, cursor)

        if not item:
            await self.telegram_client.send_message(
                chat_id,
                "Nessuna news disponibile al momento per questa categoria. Riprova tra poco.",
                reply_markup=news_navigation_keyboard(),
            )
            return

        self.auth_service.set_user_cursor(telegram_id, category_code, next_cursor)
        self.auth_service.set_current_news(telegram_id, item.news_id)
        position = (cursor % total) + 1 if total else 1

        average, votes = self.feedback_service.get_rating_summary(item.news_id)
        comments_count = self.feedback_service.get_comment_count(item.news_id)

        caption = self._format_news_message(
            item,
            position,
            total,
            average,
            votes,
            comments_count,
            for_caption=True,
        )

        if item.image_url:
            sent = await self.telegram_client.send_photo(
                chat_id,
                photo_url=item.image_url,
                caption=caption,
                reply_markup=news_navigation_keyboard(),
            )
            if sent:
                return

        text = self._format_news_message(
            item,
            position,
            total,
            average,
            votes,
            comments_count,
            for_caption=False,
        )
        await self.telegram_client.send_message(
            chat_id,
            text,
            reply_markup=news_navigation_keyboard(),
        )

    async def _require_logged(self, chat_id: int, session: UserSession | None) -> bool:
        if not session or not session.is_logged_in or not session.account_username:
            await self.telegram_client.send_message(
                chat_id,
                "Accesso negato: devi fare registrazione/login.",
                reply_markup=registration_keyboard(),
            )
            return False
        return True

    async def _require_logged_callback(self, chat_id: int, callback_id: str, session: UserSession | None) -> bool:
        if not session or not session.is_logged_in or not session.account_username:
            await self.telegram_client.answer_callback_query(callback_id, "Login richiesto", show_alert=True)
            await self.telegram_client.send_message(
                chat_id,
                "Per continuare devi registrarti o fare login.",
                reply_markup=registration_keyboard(),
            )
            return False
        return True

    def _format_news_message(
        self,
        item: NewsItem,
        position: int,
        total: int,
        average_rating: float,
        votes_count: int,
        comments_count: int,
        *,
        for_caption: bool,
    ) -> str:
        summary_limit = 180 if for_caption else 320
        summary = escape(item.summary[:summary_limit])
        summary_block = f"\n\n{summary}" if summary else ""

        category_label = CATEGORY_BY_CODE.get(item.category_code)
        category_text = category_label.value if category_label else item.category_code
        published_text = f"\nPubblicata: {escape(item.published)}" if item.published else ""

        if votes_count > 0:
            rating_text = f"⭐ Valutazione media: {average_rating:.2f}/5 ({votes_count} voti)"
        else:
            rating_text = "⭐ Valutazione: nessun voto"

        comments_text = f"💬 Commenti: {comments_count}"

        return (
            f"<b>{escape(item.title)}</b>{summary_block}\n\n"
            f"Fonte: {escape(item.source)}{published_text}\n"
            f"Categoria: {escape(category_text)}\n"
            f"{rating_text}\n"
            f"{comments_text}\n"
            f"Notizia {position}/{total}\n"
            f"<a href=\"{escape(item.link)}\">Apri articolo</a>"
        )

    def _format_comments_message(self, comments: list[dict]) -> str:
        lines = ["💬 <b>Commenti recenti</b>"]
        for comment in comments:
            username = escape(str(comment.get("account_username", "utente")))
            text = escape(str(comment.get("text", ""))[:220])
            lines.append(f"• <b>{username}</b>: {text}")

        return "\n".join(lines)
