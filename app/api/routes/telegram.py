from fastapi import APIRouter, HTTPException, Request, status

from app.core.config import get_settings
from app.dependencies import telegram_bot_service

router = APIRouter(prefix="/webhook", tags=["telegram"])
settings = get_settings()


@router.post("/telegram/{secret}")
async def telegram_webhook(secret: str, request: Request) -> dict[str, bool]:
    if secret != settings.telegram_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook secret",
        )

    update = await request.json()
    if not isinstance(update, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Telegram update payload",
        )

    await telegram_bot_service.handle_update(update)
    return {"ok": True}
