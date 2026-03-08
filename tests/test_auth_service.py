import json
from datetime import datetime, timedelta, timezone

from app.services.auth_service import AuthService
from app.storage.json_store import JsonUserStore


def _build_auth(tmp_path, retention_days: int = 30) -> AuthService:
    store = JsonUserStore(tmp_path / "users.json", tmp_path / "sessions.json")
    return AuthService(store, retention_days=retention_days)


def test_registration_and_login_with_username_password(tmp_path):
    auth = _build_auth(tmp_path)

    telegram_user = {"id": 1001, "username": "tg_andres", "first_name": "Andres"}

    auth.start_registration(telegram_user)
    ok, _ = auth.submit_registration_username(1001, "andres_user")
    assert ok is True

    ok, _ = auth.submit_registration_password(1001, "secret123")
    assert ok is True

    session = auth.get_session(1001)
    assert session is not None
    assert session.is_logged_in is True
    assert session.account_username == "andres_user"

    auth.logout_session(1001)
    auth.start_login(telegram_user)

    ok, _ = auth.submit_login_username(1001, "andres_user")
    assert ok is True

    ok, _ = auth.submit_login_password(1001, "secret123")
    assert ok is True

    session = auth.get_session(1001)
    assert session is not None
    assert session.is_logged_in is True
    assert session.account_username == "andres_user"


def test_duplicate_username_is_rejected(tmp_path):
    auth = _build_auth(tmp_path)

    user1 = {"id": 1, "username": "one", "first_name": "One"}
    user2 = {"id": 2, "username": "two", "first_name": "Two"}

    auth.start_registration(user1)
    ok, _ = auth.submit_registration_username(1, "shared_user")
    assert ok is True
    ok, _ = auth.submit_registration_password(1, "password1")
    assert ok is True

    auth.start_registration(user2)
    ok, _ = auth.submit_registration_username(2, "shared_user")
    assert ok is False


def test_purge_removes_stale_accounts_and_sessions(tmp_path):
    auth = _build_auth(tmp_path, retention_days=30)
    user = {"id": 22, "username": "legacy", "first_name": "Legacy"}

    auth.start_registration(user)
    ok, _ = auth.submit_registration_username(22, "legacy_user")
    assert ok is True
    ok, _ = auth.submit_registration_password(22, "password123")
    assert ok is True

    users_file = tmp_path / "users.json"
    sessions_file = tmp_path / "sessions.json"

    old_date = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()

    users_payload = json.loads(users_file.read_text(encoding="utf-8"))
    users_payload["accounts"]["legacy_user"]["last_login_at"] = old_date
    users_file.write_text(json.dumps(users_payload), encoding="utf-8")

    sessions_payload = json.loads(sessions_file.read_text(encoding="utf-8"))
    sessions_payload["sessions"]["22"]["updated_at"] = old_date
    sessions_payload["sessions"]["22"]["last_login_at"] = old_date
    sessions_file.write_text(json.dumps(sessions_payload), encoding="utf-8")

    removed_accounts, removed_sessions = auth.purge_expired_data()

    assert removed_accounts == 1
    assert removed_sessions == 1

    users_payload = json.loads(users_file.read_text(encoding="utf-8"))
    sessions_payload = json.loads(sessions_file.read_text(encoding="utf-8"))
    assert users_payload["accounts"] == {}
    assert sessions_payload["sessions"] == {}
