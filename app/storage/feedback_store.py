import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from app.domain.models import utc_now_iso


class JsonCommentsStore:
    def __init__(self, file_path: Path, ttl_hours: int = 24) -> None:
        self.file_path = file_path
        self.ttl_hours = ttl_hours
        self._lock = RLock()
        self._ensure_file()

    def _empty_payload(self) -> dict[str, Any]:
        return {"items": {}}

    def _ensure_file(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write_payload(self._empty_payload())

    def _read_payload(self) -> dict[str, Any]:
        self._ensure_file()
        raw = self.file_path.read_text(encoding="utf-8")
        if not raw.strip():
            return self._empty_payload()

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = self._empty_payload()

        if "items" not in payload or not isinstance(payload["items"], dict):
            payload["items"] = {}
        return payload

    def _write_payload(self, payload: dict[str, Any]) -> None:
        tmp_path = self.file_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(self.file_path)

    def _is_expired(self, first_seen_at: str, now: datetime) -> bool:
        try:
            first_seen = datetime.fromisoformat(first_seen_at)
        except ValueError:
            return True

        if first_seen.tzinfo is None:
            first_seen = first_seen.replace(tzinfo=timezone.utc)

        return first_seen < now - timedelta(hours=self.ttl_hours)

    def purge_expired(self) -> int:
        with self._lock:
            payload = self._read_payload()
            now = datetime.now(timezone.utc)
            to_remove: list[str] = []
            for news_id, item in payload["items"].items():
                if self._is_expired((item.get("first_seen_at") or "").strip(), now):
                    to_remove.append(news_id)

            for news_id in to_remove:
                payload["items"].pop(news_id, None)

            if to_remove:
                self._write_payload(payload)

            return len(to_remove)

    def add_comment(self, news_id: str, account_username: str, text: str) -> int:
        with self._lock:
            payload = self._read_payload()
            self._purge_expired_in_payload(payload)

            bucket = payload["items"].setdefault(
                news_id,
                {
                    "first_seen_at": utc_now_iso(),
                    "comments": [],
                },
            )
            comments = bucket.setdefault("comments", [])
            comments.append(
                {
                    "account_username": account_username,
                    "text": text,
                    "created_at": utc_now_iso(),
                }
            )

            self._write_payload(payload)
            return len(comments)

    def list_comments(self, news_id: str, limit: int = 10) -> list[dict]:
        with self._lock:
            payload = self._read_payload()
            removed = self._purge_expired_in_payload(payload)
            if removed:
                self._write_payload(payload)

            comments = payload["items"].get(news_id, {}).get("comments", [])
            if not isinstance(comments, list):
                return []

            return comments[-limit:]

    def get_comment_count(self, news_id: str) -> int:
        return len(self.list_comments(news_id, limit=10_000))

    def _purge_expired_in_payload(self, payload: dict[str, Any]) -> int:
        now = datetime.now(timezone.utc)
        to_remove: list[str] = []
        for news_id, item in payload["items"].items():
            if self._is_expired((item.get("first_seen_at") or "").strip(), now):
                to_remove.append(news_id)

        for news_id in to_remove:
            payload["items"].pop(news_id, None)

        return len(to_remove)


class JsonRatingsStore:
    def __init__(self, file_path: Path, ttl_hours: int = 24) -> None:
        self.file_path = file_path
        self.ttl_hours = ttl_hours
        self._lock = RLock()
        self._ensure_file()

    def _empty_payload(self) -> dict[str, Any]:
        return {"items": {}}

    def _ensure_file(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write_payload(self._empty_payload())

    def _read_payload(self) -> dict[str, Any]:
        self._ensure_file()
        raw = self.file_path.read_text(encoding="utf-8")
        if not raw.strip():
            return self._empty_payload()

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = self._empty_payload()

        if "items" not in payload or not isinstance(payload["items"], dict):
            payload["items"] = {}
        return payload

    def _write_payload(self, payload: dict[str, Any]) -> None:
        tmp_path = self.file_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(self.file_path)

    def _is_expired(self, first_seen_at: str, now: datetime) -> bool:
        try:
            first_seen = datetime.fromisoformat(first_seen_at)
        except ValueError:
            return True

        if first_seen.tzinfo is None:
            first_seen = first_seen.replace(tzinfo=timezone.utc)

        return first_seen < now - timedelta(hours=self.ttl_hours)

    def _purge_expired_in_payload(self, payload: dict[str, Any]) -> int:
        now = datetime.now(timezone.utc)
        to_remove: list[str] = []
        for news_id, item in payload["items"].items():
            if self._is_expired((item.get("first_seen_at") or "").strip(), now):
                to_remove.append(news_id)

        for news_id in to_remove:
            payload["items"].pop(news_id, None)

        return len(to_remove)

    def purge_expired(self) -> int:
        with self._lock:
            payload = self._read_payload()
            removed = self._purge_expired_in_payload(payload)
            if removed:
                self._write_payload(payload)
            return removed

    def rate_news(self, news_id: str, account_username: str, value: int) -> tuple[float, int]:
        clamped = min(5, max(1, int(value)))

        with self._lock:
            payload = self._read_payload()
            self._purge_expired_in_payload(payload)

            bucket = payload["items"].setdefault(
                news_id,
                {
                    "first_seen_at": utc_now_iso(),
                    "ratings": {},
                },
            )
            ratings = bucket.setdefault("ratings", {})
            ratings[account_username.casefold()] = {
                "account_username": account_username,
                "value": clamped,
                "updated_at": utc_now_iso(),
            }

            self._write_payload(payload)
            return self._summary_from_ratings(ratings)

    def get_summary(self, news_id: str) -> tuple[float, int]:
        with self._lock:
            payload = self._read_payload()
            removed = self._purge_expired_in_payload(payload)
            if removed:
                self._write_payload(payload)

            ratings = payload["items"].get(news_id, {}).get("ratings", {})
            if not isinstance(ratings, dict):
                return 0.0, 0
            return self._summary_from_ratings(ratings)

    def _summary_from_ratings(self, ratings: dict[str, dict]) -> tuple[float, int]:
        values = []
        for item in ratings.values():
            try:
                value = int(item.get("value", 0))
            except (TypeError, ValueError):
                continue
            if 1 <= value <= 5:
                values.append(value)

        if not values:
            return 0.0, 0

        average = round(sum(values) / len(values), 2)
        return average, len(values)
