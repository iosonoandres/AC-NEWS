import json
from datetime import datetime, timedelta, timezone

from app.services.feedback_service import FeedbackService
from app.storage.feedback_store import JsonCommentsStore, JsonRatingsStore


def test_comments_and_ratings_and_cleanup(tmp_path):
    comments_file = tmp_path / "comments.json"
    ratings_file = tmp_path / "ratings.json"

    comments_store = JsonCommentsStore(comments_file, ttl_hours=24)
    ratings_store = JsonRatingsStore(ratings_file, ttl_hours=24)
    feedback = FeedbackService(comments_store, ratings_store)

    news_id = "news-abc"

    count = feedback.add_comment(news_id, "andres_user", "Ottima notizia")
    assert count == 1

    avg, votes = feedback.rate_news(news_id, "andres_user", 5)
    assert avg == 5.0
    assert votes == 1

    comments = feedback.list_comments(news_id)
    assert len(comments) == 1

    old_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

    comments_payload = json.loads(comments_file.read_text(encoding="utf-8"))
    comments_payload["items"][news_id]["first_seen_at"] = old_date
    comments_file.write_text(json.dumps(comments_payload), encoding="utf-8")

    ratings_payload = json.loads(ratings_file.read_text(encoding="utf-8"))
    ratings_payload["items"][news_id]["first_seen_at"] = old_date
    ratings_file.write_text(json.dumps(ratings_payload), encoding="utf-8")

    feedback.purge_expired()

    assert feedback.list_comments(news_id) == []
    assert feedback.get_rating_summary(news_id) == (0.0, 0)
