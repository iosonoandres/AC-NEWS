from app.storage.feedback_store import JsonCommentsStore, JsonRatingsStore


class FeedbackService:
    def __init__(self, comments_store: JsonCommentsStore, ratings_store: JsonRatingsStore) -> None:
        self.comments_store = comments_store
        self.ratings_store = ratings_store

    def add_comment(self, news_id: str, account_username: str, text: str) -> int:
        return self.comments_store.add_comment(news_id, account_username, text)

    def list_comments(self, news_id: str, limit: int = 10) -> list[dict]:
        return self.comments_store.list_comments(news_id, limit=limit)

    def get_comment_count(self, news_id: str) -> int:
        return self.comments_store.get_comment_count(news_id)

    def rate_news(self, news_id: str, account_username: str, value: int) -> tuple[float, int]:
        return self.ratings_store.rate_news(news_id, account_username, value)

    def get_rating_summary(self, news_id: str) -> tuple[float, int]:
        return self.ratings_store.get_summary(news_id)

    def purge_expired(self) -> int:
        removed_comments = self.comments_store.purge_expired()
        removed_ratings = self.ratings_store.purge_expired()
        return removed_comments + removed_ratings
