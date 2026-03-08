import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from app.domain.models import Account, UserSession, utc_now_iso


class JsonUserStore:
    def __init__(self, accounts_file_path: Path, sessions_file_path: Path) -> None:
        self.accounts_file_path = accounts_file_path
        self.sessions_file_path = sessions_file_path
        self._lock = RLock()
        self._ensure_files()

    def _empty_accounts_payload(self) -> dict[str, Any]:
        return {"accounts": {}}

    def _empty_sessions_payload(self) -> dict[str, Any]:
        return {"sessions": {}}

    def _ensure_files(self) -> None:
        self.accounts_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.sessions_file_path.parent.mkdir(parents=True, exist_ok=True)

        if self.accounts_file_path.exists() and not self.sessions_file_path.exists():
            self._split_legacy_payload_if_needed()

        if not self.accounts_file_path.exists():
            self._write_json(self.accounts_file_path, self._empty_accounts_payload())

        if not self.sessions_file_path.exists():
            self._write_json(self.sessions_file_path, self._empty_sessions_payload())

    def _split_legacy_payload_if_needed(self) -> None:
        payload = self._read_json(self.accounts_file_path, {})
        if not isinstance(payload, dict):
            return

        if "accounts" in payload and "sessions" in payload:
            accounts_payload = {"accounts": payload.get("accounts") or {}}
            sessions_payload = {"sessions": payload.get("sessions") or {}}
            self._write_json(self.accounts_file_path, accounts_payload)
            self._write_json(self.sessions_file_path, sessions_payload)
            return

        legacy_users = payload.get("users")
        if isinstance(legacy_users, dict):
            sessions_payload = {"sessions": {}}
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
                sessions_payload["sessions"][str(session.telegram_id)] = session.to_dict()

            self._write_json(self.accounts_file_path, self._empty_accounts_payload())
            self._write_json(self.sessions_file_path, sessions_payload)

    def _read_json(self, path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
        try:
            raw = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return dict(fallback)

        if not raw.strip():
            return dict(fallback)

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = dict(fallback)

        if not isinstance(payload, dict):
            return dict(fallback)
        return payload

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp_path.replace(path)

    def _read_accounts_payload(self) -> dict[str, Any]:
        payload = self._read_json(self.accounts_file_path, self._empty_accounts_payload())
        if "accounts" not in payload or not isinstance(payload["accounts"], dict):
            payload["accounts"] = {}
        return payload

    def _read_sessions_payload(self) -> dict[str, Any]:
        payload = self._read_json(self.sessions_file_path, self._empty_sessions_payload())
        if "sessions" not in payload or not isinstance(payload["sessions"], dict):
            payload["sessions"] = {}
        return payload

    def _account_key(self, username: str) -> str:
        return (username or "").strip().casefold()

    def get_session(self, telegram_id: int) -> UserSession | None:
        with self._lock:
            self._ensure_files()
            payload = self._read_sessions_payload()
            raw_session = payload["sessions"].get(str(telegram_id))
            if not raw_session:
                return None
            return UserSession.from_dict(raw_session)

    def upsert_session(self, session: UserSession) -> UserSession:
        with self._lock:
            self._ensure_files()
            payload = self._read_sessions_payload()
            session.updated_at = utc_now_iso()
            payload["sessions"][str(session.telegram_id)] = session.to_dict()
            self._write_json(self.sessions_file_path, payload)
            return session

    def get_account(self, username: str) -> Account | None:
        with self._lock:
            self._ensure_files()
            payload = self._read_accounts_payload()
            raw_account = payload["accounts"].get(self._account_key(username))
            if not raw_account:
                return None
            return Account.from_dict(raw_account)

    def account_exists(self, username: str) -> bool:
        return self.get_account(username) is not None

    def upsert_account(self, account: Account) -> Account:
        with self._lock:
            self._ensure_files()
            payload = self._read_accounts_payload()
            payload["accounts"][self._account_key(account.username)] = account.to_dict()
            self._write_json(self.accounts_file_path, payload)
            return account

    def purge_expired(self, retention_days: int) -> tuple[int, int]:
        with self._lock:
            self._ensure_files()
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(days=retention_days)

            accounts_payload = self._read_accounts_payload()
            sessions_payload = self._read_sessions_payload()

            removed_sessions = 0
            for session_key, raw_session in list(sessions_payload["sessions"].items()):
                try:
                    session = UserSession.from_dict(raw_session)
                except Exception:  # noqa: BLE001
                    sessions_payload["sessions"].pop(session_key, None)
                    removed_sessions += 1
                    continue

                if self._session_last_seen(session) < cutoff:
                    sessions_payload["sessions"].pop(session_key, None)
                    removed_sessions += 1

            active_account_keys = set()
            for raw_session in sessions_payload["sessions"].values():
                try:
                    session = UserSession.from_dict(raw_session)
                except Exception:  # noqa: BLE001
                    continue
                if session.account_username:
                    active_account_keys.add(session.account_username.casefold())

            removed_accounts = 0
            for account_key, raw_account in list(accounts_payload["accounts"].items()):
                try:
                    account = Account.from_dict(raw_account)
                except Exception:  # noqa: BLE001
                    accounts_payload["accounts"].pop(account_key, None)
                    removed_accounts += 1
                    continue

                last_login = self._parse_datetime(account.last_login_at) or self._parse_datetime(account.created_at) or now
                if last_login < cutoff and account_key not in active_account_keys:
                    accounts_payload["accounts"].pop(account_key, None)
                    removed_accounts += 1

            if removed_sessions:
                self._write_json(self.sessions_file_path, sessions_payload)
            if removed_accounts:
                self._write_json(self.accounts_file_path, accounts_payload)

            return removed_accounts, removed_sessions

    def _session_last_seen(self, session: UserSession) -> datetime:
        now = datetime.now(timezone.utc)
        updated_at = self._parse_datetime(session.updated_at)
        if updated_at is not None:
            return updated_at

        last_login_at = self._parse_datetime(session.last_login_at)
        if last_login_at is not None:
            return last_login_at

        created_at = self._parse_datetime(session.created_at)
        if created_at is not None:
            return created_at

        return now

    def _parse_datetime(self, value: str) -> datetime | None:
        raw = (value or "").strip()
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
