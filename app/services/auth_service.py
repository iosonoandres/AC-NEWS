import hashlib
import re
import secrets
from datetime import datetime, timezone

from app.core.constants import normalize_category_code
from app.domain.models import Account, UserSession
from app.storage.json_store import JsonUserStore

PENDING_REGISTER_USERNAME = "register_username"
PENDING_REGISTER_PASSWORD = "register_password"
PENDING_LOGIN_USERNAME = "login_username"
PENDING_LOGIN_PASSWORD = "login_password"
PENDING_COMMENT = "comment"

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")


class AuthService:
    def __init__(self, user_store: JsonUserStore) -> None:
        self.user_store = user_store

    def ensure_session(self, telegram_user: dict) -> UserSession:
        telegram_id = int(telegram_user["id"])
        session = self.user_store.get_session(telegram_id)

        if not session:
            session = UserSession(
                telegram_id=telegram_id,
                telegram_username=(telegram_user.get("username") or "").strip(),
                first_name=(telegram_user.get("first_name") or "").strip(),
            )
        else:
            session.telegram_username = (telegram_user.get("username") or session.telegram_username or "").strip()
            session.first_name = (telegram_user.get("first_name") or session.first_name or "").strip()

        return self.user_store.upsert_session(session)

    def get_session(self, telegram_id: int) -> UserSession | None:
        return self.user_store.get_session(telegram_id)

    def start_registration(self, telegram_user: dict) -> UserSession:
        session = self.ensure_session(telegram_user)
        session.pending_state = PENDING_REGISTER_USERNAME
        session.pending_username = ""
        session.pending_news_id = ""
        return self.user_store.upsert_session(session)

    def submit_registration_username(self, telegram_id: int, username_raw: str) -> tuple[bool, str]:
        session = self.user_store.get_session(telegram_id)
        if not session:
            return False, "Sessione non trovata. Usa /start e riprova."

        username = (username_raw or "").strip()
        if not _USERNAME_RE.match(username):
            return False, "Username non valido. Usa 3-20 caratteri: lettere, numeri, underscore."

        if self.user_store.account_exists(username):
            return False, "Username già usato. Scegline un altro."

        session.pending_state = PENDING_REGISTER_PASSWORD
        session.pending_username = username
        self.user_store.upsert_session(session)
        return True, "Perfetto. Ora inserisci una password (minimo 6 caratteri)."

    def submit_registration_password(self, telegram_id: int, password_raw: str) -> tuple[bool, str]:
        session = self.user_store.get_session(telegram_id)
        if not session:
            return False, "Sessione non trovata. Usa /start e riprova."

        if session.pending_state != PENDING_REGISTER_PASSWORD or not session.pending_username:
            return False, "Flusso registrazione non valido. Premi di nuovo Registrati."

        password = (password_raw or "").strip()
        if len(password) < 6:
            return False, "Password troppo corta. Minimo 6 caratteri."

        salt = secrets.token_hex(8)
        password_hash = self._hash_password(password, salt)
        account = Account(
            username=session.pending_username,
            password_salt=salt,
            password_hash=password_hash,
        )
        self.user_store.upsert_account(account)

        session.is_logged_in = True
        session.account_username = account.username
        session.last_login_at = datetime.now(timezone.utc).isoformat()
        session.pending_state = ""
        session.pending_username = ""
        session.pending_news_id = ""
        self.user_store.upsert_session(session)

        return True, "Registrazione completata e login effettuato."

    def start_login(self, telegram_user: dict) -> UserSession:
        session = self.ensure_session(telegram_user)
        session.pending_state = PENDING_LOGIN_USERNAME
        session.pending_username = ""
        session.pending_news_id = ""
        return self.user_store.upsert_session(session)

    def submit_login_username(self, telegram_id: int, username_raw: str) -> tuple[bool, str]:
        session = self.user_store.get_session(telegram_id)
        if not session:
            return False, "Sessione non trovata. Usa /start e riprova."

        username = (username_raw or "").strip()
        account = self.user_store.get_account(username)
        if not account:
            return False, "Username non trovato. Registrati oppure riprova."

        session.pending_state = PENDING_LOGIN_PASSWORD
        session.pending_username = account.username
        self.user_store.upsert_session(session)
        return True, "Perfetto. Ora inserisci la password."

    def submit_login_password(self, telegram_id: int, password_raw: str) -> tuple[bool, str]:
        session = self.user_store.get_session(telegram_id)
        if not session:
            return False, "Sessione non trovata. Usa /start e riprova."

        if session.pending_state != PENDING_LOGIN_PASSWORD or not session.pending_username:
            return False, "Flusso login non valido. Premi di nuovo Login."

        account = self.user_store.get_account(session.pending_username)
        if not account:
            return False, "Account non trovato."

        password = (password_raw or "").strip()
        candidate_hash = self._hash_password(password, account.password_salt)
        if candidate_hash != account.password_hash:
            return False, "Password errata. Riprova."

        session.is_logged_in = True
        session.account_username = account.username
        session.last_login_at = datetime.now(timezone.utc).isoformat()
        session.pending_state = ""
        session.pending_username = ""
        session.pending_news_id = ""
        self.user_store.upsert_session(session)

        return True, f"Login effettuato come {account.username}."

    def logout_session(self, telegram_id: int) -> UserSession | None:
        session = self.user_store.get_session(telegram_id)
        if not session:
            return None

        session.is_logged_in = False
        session.account_username = ""
        session.pending_state = ""
        session.pending_username = ""
        session.pending_news_id = ""
        return self.user_store.upsert_session(session)

    def set_selected_category(self, telegram_id: int, category_code: str) -> UserSession | None:
        session = self.user_store.get_session(telegram_id)
        if not session:
            return None

        normalized = normalize_category_code(category_code)
        if not normalized:
            return session

        session.selected_category = normalized
        session.news_cursor[normalized] = 0
        session.current_news_id = ""
        return self.user_store.upsert_session(session)

    def get_user_cursor(self, telegram_id: int, category_code: str) -> int:
        session = self.user_store.get_session(telegram_id)
        if not session:
            return 0

        normalized = normalize_category_code(category_code)
        if not normalized:
            return 0

        return int(session.news_cursor.get(normalized, 0))

    def set_user_cursor(self, telegram_id: int, category_code: str, cursor: int) -> UserSession | None:
        session = self.user_store.get_session(telegram_id)
        if not session:
            return None

        normalized = normalize_category_code(category_code)
        if not normalized:
            return session

        session.news_cursor[normalized] = max(0, int(cursor))
        return self.user_store.upsert_session(session)

    def set_current_news(self, telegram_id: int, news_id: str) -> UserSession | None:
        session = self.user_store.get_session(telegram_id)
        if not session:
            return None

        session.current_news_id = news_id
        return self.user_store.upsert_session(session)

    def start_comment_flow(self, telegram_id: int, news_id: str) -> UserSession | None:
        session = self.user_store.get_session(telegram_id)
        if not session:
            return None

        session.pending_state = PENDING_COMMENT
        session.pending_news_id = news_id
        return self.user_store.upsert_session(session)

    def consume_comment_flow(self, telegram_id: int, text: str) -> tuple[bool, str, str]:
        session = self.user_store.get_session(telegram_id)
        if not session:
            return False, "Sessione non trovata.", ""

        if session.pending_state != PENDING_COMMENT or not session.pending_news_id:
            return False, "Nessun commento in corso.", ""

        comment = (text or "").strip()
        if len(comment) < 2:
            return False, "Commento troppo corto. Scrivi almeno 2 caratteri.", ""

        news_id = session.pending_news_id
        session.pending_state = ""
        session.pending_news_id = ""
        self.user_store.upsert_session(session)
        return True, "Commento salvato.", news_id

    def clear_pending_state(self, telegram_id: int) -> UserSession | None:
        session = self.user_store.get_session(telegram_id)
        if not session:
            return None

        session.pending_state = ""
        session.pending_username = ""
        session.pending_news_id = ""
        return self.user_store.upsert_session(session)

    def _hash_password(self, password: str, salt: str) -> str:
        payload = f"{salt}:{password}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
