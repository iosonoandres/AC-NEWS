import logging
import time
from dataclasses import dataclass

from app.domain.models import NewsItem
from app.integrations.rss.client import RSSClient

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    expires_at: float
    items: list[NewsItem]


class NewsService:
    def __init__(self, rss_client: RSSClient, cache_ttl_seconds: int = 300) -> None:
        self.rss_client = rss_client
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, CacheEntry] = {}

    async def get_next_news(
        self,
        category_code: str,
        cursor: int,
    ) -> tuple[NewsItem | None, int, int]:
        items = await self._get_category_items(category_code)
        if not items:
            return None, 0, 0

        normalized_cursor = max(0, cursor)
        if normalized_cursor >= len(items):
            normalized_cursor = 0

        selected_index = await self._pick_item_with_image(items, normalized_cursor)
        item = items[selected_index]

        next_cursor = selected_index + 1
        if next_cursor >= len(items):
            next_cursor = 0

        return item, next_cursor, len(items)

    async def _get_category_items(self, category_code: str) -> list[NewsItem]:
        cache_key = category_code
        now = time.monotonic()
        cached = self._cache.get(cache_key)
        if cached and cached.expires_at > now:
            return cached.items

        items = await self.rss_client.fetch_category_news(category_code)
        self._cache[cache_key] = CacheEntry(
            expires_at=now + self.cache_ttl_seconds,
            items=items,
        )
        return items

    async def _ensure_item_image(self, item: NewsItem) -> None:
        if item.image_url:
            return

        resolver = getattr(self.rss_client, "resolve_image_from_article", None)
        if not callable(resolver):
            return

        try:
            resolved = await resolver(item.link)
            if resolved:
                item.image_url = resolved
        except Exception as exc:  # noqa: BLE001
            logger.debug("Image enrichment failed for %s: %s", item.link, exc)

    async def _pick_item_with_image(self, items: list[NewsItem], start_index: int) -> int:
        total = len(items)
        for offset in range(total):
            idx = (start_index + offset) % total
            candidate = items[idx]
            await self._ensure_item_image(candidate)
            if candidate.image_url:
                return idx

        return start_index
