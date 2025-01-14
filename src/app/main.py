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
    # TODO: read this from an asset file
    html_content = """
    <html>
        <head>
            <title>Chatbot Agent</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f9;
                    margin: 0;
                    padding: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                }
                #chat-box {
                    width: 400px;
                    border: 2px solid #ccc;
                    border-radius: 8px;
                    padding: 16px;
                    background-color: #fff;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }
                #chat-history {
                    height: 300px;
                    overflow-y: auto;
                    border: 1px solid #ddd;
                    padding: 8px;
                    margin-bottom: 16px;
                    border-radius: 4px;
                    background-color: #f9f9f9;
                }
                #chat-history div {
                    margin-bottom: 10px;
                    padding: 8px;
                    border-radius: 4px;
                }
                .user-message {
                    background-color: #d1f7c4;
                    align-self: flex-start;
                }
                .agent-message {
                    background-color: #f0f0f5;
                    align-self: flex-end;
                }
                #chat-form label, #chat-form input {
                    display: block;
                    width: 100%;
                }
                #chat-form input[type="text"] {
                    padding: 8px;
                    margin-bottom: 12px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    box-sizing: border-box;
                }
                #chat-form input[type="submit"] {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 10px 15px;
                    border-radius: 4px;
                    cursor: pointer;
                    width: 100%;
                }
                #chat-form input[type="submit"]:hover {
                    background-color: #45a049;
                }
            </style>
        </head>
        <body>
            <div id="chat-box">
                <h1 style="text-align: center;">Running Buddy</h1>
                <div id="chat-history"></div>
                <form id="chat-form">
                    <label for="message">Your message:</label>
                    <input type="text" id="message" name="message" placeholder="Type your message here">
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
                    userMessage.className = 'user-message';
                    chatHistory.appendChild(userMessage);

                    // Clear the input field
                    document.getElementById('message').value = '';

                    // Scroll to the bottom of the chat history
                    chatHistory.scrollTop = chatHistory.scrollHeight;

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
                        agentMessage.innerHTML = `Agent:<br>${data.response.replace(/\\n/g, '<br>')}`;
                        agentMessage.className = 'agent-message';
                        chatHistory.appendChild(agentMessage);

                        // Scroll to the bottom of the chat history
                        chatHistory.scrollTop = chatHistory.scrollHeight;
                    } else {
                        const errorMessage = document.createElement('div');
                        errorMessage.textContent = 'Error: Could not process your request.';
                        errorMessage.className = 'agent-message';
                        chatHistory.appendChild(errorMessage);

                        // Scroll to the bottom of the chat history
                        chatHistory.scrollTop = chatHistory.scrollHeight;
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
