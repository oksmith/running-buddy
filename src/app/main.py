from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from src.app.endpoints import ai, auth

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
            <h1>Have a chat with Running Buddy!</h1>
            <div id="chat-box">
                <div id="chat-history"></div>
                <form id="chat-form">
                    <label for="message">Your message:</label><br>
                    <input type="text" id="message" name="message"><br><br>
                    <input type="submit" value="Send">
                </form>
            </div>
            <script>
                const form = document.getElementById('chat-form');
                const chatHistory = document.getElementById('chat-history');
                
                form.addEventListener('submit', async (event) => {
                    event.preventDefault(); // Prevent the default form submission
                    const message = document.getElementById('message').value;

                    // Add user's message to the chat history
                    const userMessage = document.createElement('div');
                    userMessage.textContent = `You: ${message}`;
                    chatHistory.appendChild(userMessage);

                    // Send the message to the backend
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: message, chat_history: [] })
                    });

                    if (response.ok) {
                        const data = await response.json();
                        // Add the agent's response to the chat history
                        const agentMessage = document.createElement('div');
                        agentMessage.textContent = `Agent: ${data.response}`;
                        chatHistory.appendChild(agentMessage);
                    } else {
                        const errorMessage = document.createElement('div');
                        errorMessage.textContent = 'Error: Could not process your request.';
                        chatHistory.appendChild(errorMessage);
                    }
                });
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)



app.include_router(auth.router)
app.include_router(ai.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
