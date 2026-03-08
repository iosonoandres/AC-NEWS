import json
from pathlib import Path
from threading import RLock
from typing import Any

from app.domain.models import Account, UserSession, utc_now_iso


class JsonUserStore:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self._lock = RLock()
        self._ensure_file()

    def _empty_payload(self) -> dict[str, Any]:
        return {"accounts": {}, "sessions": {}}

    def _ensure_file(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write_payload(self._empty_payload())

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if "accounts" in payload and isinstance(payload["accounts"], dict) and "sessions" in payload and isinstance(payload["sessions"], dict):
            return payload

        normalized = self._empty_payload()
        legacy_users = payload.get("users") if isinstance(payload, dict) else None
        if isinstance(legacy_users, dict):
            for raw in legacy_users.values():
                try:
                    session = UserSession.from_dict(raw)
                except Exception:  # noqa: BLE001
                    continue

                if session.telegram_id <= 0:
                    continue

                session.is_logged_in = False
                session.account_username = ""
                session.pending_state = ""
                session.pending_username = ""
                session.pending_news_id = ""
                session.updated_at = utc_now_iso()
                normalized["sessions"][str(session.telegram_id)] = session.to_dict()

        return normalized

    def _read_payload(self) -> dict[str, Any]:
        self._ensure_file()
        raw = self.file_path.read_text(encoding="utf-8")
        if not raw.strip():
            return self._empty_payload()

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = self._empty_payload()

        return self._normalize_payload(payload)

    def _write_payload(self, payload: dict[str, Any]) -> None:
        tmp_path = self.file_path.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp_path.replace(self.file_path)

    def _account_key(self, username: str) -> str:
        return (username or "").strip().casefold()

    def get_session(self, telegram_id: int) -> UserSession | None:
        with self._lock:
            payload = self._read_payload()
            raw_session = payload["sessions"].get(str(telegram_id))
            if not raw_session:
                return None
            return UserSession.from_dict(raw_session)

    def upsert_session(self, session: UserSession) -> UserSession:
        with self._lock:
            payload = self._read_payload()
            session.updated_at = utc_now_iso()
            payload["sessions"][str(session.telegram_id)] = session.to_dict()
            self._write_payload(payload)
            return session

    def get_account(self, username: str) -> Account | None:
        with self._lock:
            payload = self._read_payload()
            raw_account = payload["accounts"].get(self._account_key(username))
            if not raw_account:
                return None
            return Account.from_dict(raw_account)

    def account_exists(self, username: str) -> bool:
        return self.get_account(username) is not None

    def upsert_account(self, account: Account) -> Account:
        with self._lock:
            payload = self._read_payload()
            payload["accounts"][self._account_key(account.username)] = account.to_dict()
            self._write_payload(payload)
            return account
