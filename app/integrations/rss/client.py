import asyncio
import hashlib
import html
import logging
import re
from collections.abc import Iterable

import feedparser
import httpx

from app.domain.models import NewsItem
from app.integrations.rss.category_filter import is_relevant_news
from app.integrations.rss.feeds import CATEGORY_FEEDS, FeedSource

logger = logging.getLogger(__name__)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_IMG_SRC_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.IGNORECASE)
_META_IMAGE_RE = re.compile(
    r"<meta[^>]+(?:property|name)=[\"'](?:og:image|twitter:image)[\"'][^>]+content=[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)


class RSSClient:
    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds
        self._article_image_cache: dict[str, str] = {}

    async def fetch_category_news(self, category_code: str, limit: int = 25) -> list[NewsItem]:
        sources = list(CATEGORY_FEEDS.get(category_code, []))
        if not sources:
            return []

        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
            tasks = [self._fetch_source(client, source, category_code) for source in sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        source_items: list[list[NewsItem]] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("RSS source failed: %s", result)
                continue
            source_items.append(list(result))

        return self._merge_round_robin(source_items, limit)

    def _merge_round_robin(self, source_items: list[list[NewsItem]], limit: int) -> list[NewsItem]:
        if not source_items:
            return []

        items: list[NewsItem] = []
        seen_ids: set[str] = set()
        iterators = [iter(items_list) for items_list in source_items if items_list]

        while iterators and len(items) < limit:
            next_iterators = []
            for iterator in iterators:
                try:
                    item = next(iterator)
                except StopIteration:
                    continue

                if item.news_id not in seen_ids:
                    seen_ids.add(item.news_id)
                    items.append(item)
                    if len(items) >= limit:
                        break

                next_iterators.append(iterator)

            iterators = next_iterators

        return items

    async def resolve_image_from_article(self, link: str) -> str:
        if not link:
            return ""

        cached = self._article_image_cache.get(link)
        if cached is not None:
            return cached

        image_url = ""
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                response = await client.get(
                    link,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
                    },
                )
                response.raise_for_status()
                html_doc = response.text[:300_000]
                match = _META_IMAGE_RE.search(html_doc)
                if match:
                    candidate = match.group(1).strip()
                    if self._is_http_url(candidate):
                        image_url = candidate
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to resolve og:image from %s: %s", link, exc)

        self._article_image_cache[link] = image_url
        return image_url

    async def _fetch_source(
        self,
        client: httpx.AsyncClient,
        source: FeedSource,
        category_code: str,
    ) -> Iterable[NewsItem]:
        response = await client.get(
            source.url,
            headers={"User-Agent": "AC-NEWS/1.0 (+https://github.com/iosonoandres/AC-NEWS)"},
        )
        response.raise_for_status()

        parsed = feedparser.parse(response.content)
        items: list[NewsItem] = []

        for entry in parsed.entries:
            title = self._clean_text(entry.get("title", ""))
            link = str(entry.get("link", "") or "").strip()
            if not title or not link:
                continue

            summary = self._clean_text(entry.get("summary", "") or entry.get("description", ""))
            if not is_relevant_news(category_code, title, summary, source.name):
                continue

            published = self._clean_text(entry.get("published", "") or entry.get("updated", ""))
            image_url = self._extract_image_url(entry)
            news_id = self._build_news_id(link)

            items.append(
                NewsItem(
                    news_id=news_id,
                    title=title,
                    link=link,
                    source=source.name,
                    category_code=category_code,
                    summary=summary,
                    published=published,
                    image_url=image_url,
                )
            )

        return items

    def _build_news_id(self, link: str) -> str:
        normalized = link.strip().encode("utf-8")
        return hashlib.sha1(normalized).hexdigest()  # noqa: S324

    def _extract_image_url(self, entry: dict) -> str:
        media_content = entry.get("media_content") or []
        if isinstance(media_content, list):
            for media in media_content:
                if not isinstance(media, dict):
                    continue
                candidate = str(media.get("url", "") or "").strip()
                if self._is_http_url(candidate):
                    return candidate

        media_thumbnail = entry.get("media_thumbnail") or []
        if isinstance(media_thumbnail, list):
            for media in media_thumbnail:
                if not isinstance(media, dict):
                    continue
                candidate = str(media.get("url", "") or "").strip()
                if self._is_http_url(candidate):
                    return candidate

        links = entry.get("links") or []
        if isinstance(links, list):
            for link_item in links:
                if not isinstance(link_item, dict):
                    continue
                candidate = str(link_item.get("href", "") or "").strip()
                mime_type = str(link_item.get("type", "") or "").strip().lower()
                rel = str(link_item.get("rel", "") or "").strip().lower()
                if self._is_http_url(candidate) and (mime_type.startswith("image/") or rel == "enclosure"):
                    return candidate

        summary_html = str(entry.get("summary", "") or entry.get("description", ""))
        match = _IMG_SRC_RE.search(summary_html)
        if match:
            candidate = match.group(1).strip()
            if self._is_http_url(candidate):
                return candidate

        return ""

    def _is_http_url(self, value: str) -> bool:
        return value.startswith("https://") or value.startswith("http://")

    def _clean_text(self, raw: str) -> str:
        no_tags = _HTML_TAG_RE.sub("", raw)
        return html.unescape(no_tags).strip()
