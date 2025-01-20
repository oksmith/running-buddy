import json
import os
from typing import Dict
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel


load_dotenv()

APP_CLIENT_ID = os.getenv("APP_CLIENT_ID")
APP_CLIENT_SECRET = os.getenv("APP_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000/auth/exchange-token"
GET_AUTH_URL_NAME = "get_auth_url"
CHAT_PAGE = "/chat-ui"

router = APIRouter()

# TODO: replace this with postgres database
token_storage = {}


class AuthRequest(BaseModel):
    code: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: int


def exchange_code_for_tokens(auth_code: str) -> Dict:
    """
    Exchanges the Strava authorization code for access and refresh tokens.
    """
    url = "https://www.strava.com/oauth/token"
    data = {
        "client_id": APP_CLIENT_ID,
        "client_secret": APP_CLIENT_SECRET,
        "code": auth_code,
        "grant_type": "authorization_code",
    }

    response = requests.post(url, data=data)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.json())


@router.get("/authorize-url", name=GET_AUTH_URL_NAME)
async def get_auth_url():
    scope = "read,activity:read,activity:read_all,activity:write"
    response_type = "code"

    base_url = "https://www.strava.com/oauth/authorize"
    params = {
        "client_id": APP_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": response_type,
        "approval_prompt": "auto",
        "scope": scope,
    }

    authorization_url = f"{base_url}?{urlencode(params)}"
    return RedirectResponse(url=authorization_url)


@router.get("/exchange-token", response_model=AuthResponse)
async def exchange_token(request: Request):
    """
    Handles the exchange of authorization code for access and refresh tokens.
    This is the endpoint that handles the redirect from Strava with the 'code' in the URL.
    """
    code = request.query_params.get("code")

    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is missing.")

    tokens = exchange_code_for_tokens(code)

    # Save tokens to storage TODO: use proper storage
    token_storage["access_token"] = tokens["access_token"]
    token_storage["refresh_token"] = tokens["refresh_token"]
    token_storage["expires_at"] = tokens["expires_at"]

    with open("token_storage.json", "w") as f:
        json.dump(token_storage, f)

    # Redirect to the agent page to start actaually doing stuff
    return RedirectResponse(url=CHAT_PAGE, status_code=303)


@router.get("/current-token", response_model=AuthResponse)
async def get_current_token():
    """
    Retrieve the currently stored tokens.
    """
    # TODO: store multiple different tokens so that multiple users can use this app
    # simultaneously?
    if not token_storage.get("access_token"):
        raise HTTPException(status_code=404, detail="No tokens stored")

    return AuthResponse(
        access_token=token_storage["access_token"],
        refresh_token=token_storage["refresh_token"],
        expires_at=token_storage["expires_at"],
    )
