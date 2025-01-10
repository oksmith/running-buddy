from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import HTMLResponse

from src.app.endpoints import auth

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    auth_url = request.url_for(auth.GET_AUTH_URL_NAME)
    html_content = f"""
    <html>
        <head>
            <title>Running Buddy</title>
        </head>
        <body>
            <h1>Welcome to Running Buddy!</h1>
            <p><a href="{auth_url}">Authorize with Strava</a></p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/agent", response_class=HTMLResponse)
async def agent_page(request: Request):
    html_content = """
    <html>
        <head>
            <title>Chatbot Agent</title>
        </head>
        <body>
            <h1>Welcome to the Chatbot Agent!</h1>
            <p>Start interacting with the agent below.</p>
            <!-- Your chatbot UI would go here -->
            <form action="/chat" method="post">
                <label for="message">Your message:</label><br>
                <input type="text" id="message" name="message"><br><br>
                <input type="submit" value="Send">
            </form>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)


app.include_router(auth.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
