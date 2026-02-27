from fastapi import APIRouter, Header, HTTPException, Request, Depends
from typing import Dict, Any
from app.core.config import settings

router = APIRouter()

@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None)
):
    """
    Receive webhook from Telegram. 
    Verifies the secret token to ensure the request is from Telegram.
    """
    if x_telegram_bot_api_secret_token != settings.TELEGRAM_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid Secret Token")
    
    update = await request.json()
    
    # We will pass this update to a background task or service later.
    # For now, just print or log it.
    print(f"Received update: {update}")
    
    return {"status": "ok"}
