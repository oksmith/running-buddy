from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.app.api.routes import auth, chat

app = FastAPI(title="Running Buddy AI Agent")

# Set up the paths for static files
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=FileResponse)
async def read_root():
    return STATIC_DIR / "index.html"


@app.get("/chat-ui", response_class=FileResponse)
async def agent_page():
    return STATIC_DIR / "chat-ui.html"


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
