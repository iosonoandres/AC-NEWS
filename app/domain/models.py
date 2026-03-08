from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class NewsItem:
    news_id: str
    title: str
    link: str
    source: str
    category_code: str
    summary: str = ""
    published: str = ""
    image_url: str = ""


@dataclass
class Account:
    username: str
    password_salt: str
    password_hash: str
    created_at: str = field(default_factory=utc_now_iso)
    last_login_at: str = field(default_factory=utc_now_iso)

    @classmethod
    def from_dict(cls, data: dict) -> "Account":
        created_at = (data.get("created_at") or utc_now_iso()).strip()
        return cls(
            username=(data.get("username") or "").strip(),
            password_salt=(data.get("password_salt") or "").strip(),
            password_hash=(data.get("password_hash") or "").strip(),
            created_at=created_at,
            last_login_at=(data.get("last_login_at") or created_at).strip(),
        )

    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "password_salt": self.password_salt,
            "password_hash": self.password_hash,
            "created_at": self.created_at,
            "last_login_at": self.last_login_at,
        }


@dataclass
class UserSession:
    telegram_id: int
    telegram_username: str = ""
    first_name: str = ""
    is_logged_in: bool = False
    account_username: str = ""
    selected_category: str = ""
    news_cursor: dict[str, int] = field(default_factory=dict)
    current_news_id: str = ""
    last_news_message_id: int = 0
    pending_state: str = ""
    pending_username: str = ""
    pending_news_id: str = ""
    last_login_at: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    @classmethod
    def from_dict(cls, data: dict) -> "UserSession":
        return cls(
            telegram_id=int(data.get("telegram_id", 0)),
            telegram_username=(data.get("telegram_username") or data.get("username") or "").strip(),
            first_name=(data.get("first_name") or "").strip(),
            is_logged_in=bool(data.get("is_logged_in", False)),
            account_username=(data.get("account_username") or "").strip(),
            selected_category=(data.get("selected_category") or "").strip(),
            news_cursor={
                str(category_code): int(cursor)
                for category_code, cursor in (data.get("news_cursor") or {}).items()
            },
            current_news_id=(data.get("current_news_id") or "").strip(),
            last_news_message_id=int(data.get("last_news_message_id") or 0),
            pending_state=(data.get("pending_state") or "").strip(),
            pending_username=(data.get("pending_username") or "").strip(),
            pending_news_id=(data.get("pending_news_id") or "").strip(),
            last_login_at=(data.get("last_login_at") or "").strip(),
            created_at=(data.get("created_at") or data.get("registered_at") or utc_now_iso()).strip(),
            updated_at=(data.get("updated_at") or utc_now_iso()).strip(),
        )

    def to_dict(self) -> dict:
        return {
            "telegram_id": self.telegram_id,
            "telegram_username": self.telegram_username,
            "first_name": self.first_name,
            "is_logged_in": self.is_logged_in,
            "account_username": self.account_username,
            "selected_category": self.selected_category,
            "news_cursor": self.news_cursor,
            "current_news_id": self.current_news_id,
            "last_news_message_id": self.last_news_message_id,
            "pending_state": self.pending_state,
            "pending_username": self.pending_username,
            "pending_news_id": self.pending_news_id,
            "last_login_at": self.last_login_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
