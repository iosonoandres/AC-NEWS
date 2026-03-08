import pytest

from app.domain.models import NewsItem
from app.services.news_service import NewsService


class FakeRSSClient:
    async def fetch_category_news(self, category_code: str, limit: int = 25):
        return [
            NewsItem(
                news_id=f"news-{idx}",
                title=f"News {idx}",
                link=f"https://example.com/{idx}",
                source="fake",
                category_code=category_code,
                summary="",
                published="",
                image_url="",
            )
            for idx in range(3)
        ]


@pytest.mark.asyncio
async def test_get_next_news_cycles_cursor():
    service = NewsService(FakeRSSClient(), cache_ttl_seconds=300)

    item1, next_cursor1, total1 = await service.get_next_news("SPORT", 0)
    assert item1 is not None
    assert item1.title == "News 0"
    assert next_cursor1 == 1
    assert total1 == 3

    item2, next_cursor2, total2 = await service.get_next_news("SPORT", 2)
    assert item2 is not None
    assert item2.title == "News 2"
    assert next_cursor2 == 0
    assert total2 == 3
