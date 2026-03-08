from app.services.auth_service import AuthService
from app.storage.json_store import JsonUserStore


def test_registration_and_login_with_username_password(tmp_path):
    store = JsonUserStore(tmp_path / "users.json")
    auth = AuthService(store)

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
    store = JsonUserStore(tmp_path / "users.json")
    auth = AuthService(store)

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
