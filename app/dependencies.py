from app.core.config import get_settings
from app.integrations.channels.telegram.client import TelegramClient
from app.integrations.rss.client import RSSClient
from app.services.auth_service import AuthService
from app.services.feedback_service import FeedbackService
from app.services.news_service import NewsService
from app.services.telegram_service import TelegramBotService
from app.storage.feedback_store import JsonCommentsStore, JsonRatingsStore
from app.storage.json_store import JsonUserStore

settings = get_settings()

user_store = JsonUserStore(settings.users_file)
comments_store = JsonCommentsStore(settings.comments_file, ttl_hours=settings.feedback_ttl_hours)
ratings_store = JsonRatingsStore(settings.ratings_file, ttl_hours=settings.feedback_ttl_hours)

auth_service = AuthService(user_store)
feedback_service = FeedbackService(comments_store, ratings_store)
rss_client = RSSClient(timeout_seconds=settings.request_timeout_seconds)
news_service = NewsService(
    rss_client,
    cache_ttl_seconds=settings.news_cache_ttl_seconds,
)
telegram_client = TelegramClient(
    bot_token=settings.telegram_bot_token,
    timeout_seconds=settings.request_timeout_seconds,
)
telegram_bot_service = TelegramBotService(
    auth_service=auth_service,
    news_service=news_service,
    feedback_service=feedback_service,
    telegram_client=telegram_client,
)
