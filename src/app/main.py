from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from src.app.api.routes import auth, chat
# from src.app.api import ai

app = FastAPI(title="Running Buddy AI Agent")


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


@app.get("/chat", response_class=HTMLResponse)
async def agent_page(request: Request):
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
                // Add streaming support for the chat
                let pendingConfirmation = null;

                async function handleStream(message) {
                    const response = await fetch('/chat/stream', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ content: message })
                    });

                    if (!response.ok) {
                        console.error("Failed to fetch chat stream:", response.statusText);
                        const errorMessage = document.createElement('div');
                        errorMessage.textContent = `System: Error fetching chat stream: ${response.statusText}`;
                        errorMessage.className = 'system-message';
                        chatHistory.appendChild(errorMessage);
                        return;
                    }

                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();

                    while (true) {
                        const { value, done } = await reader.read();
                        if (done) break;
                        
                        const chunk = JSON.parse(decoder.decode(value));
                        
                        if (chunk.type === 'confirmation_request') {
                            // Show confirmation dialog
                            pendingConfirmation = chunk.confirmation_id;
                            const confirmed = confirm(chunk.message);
                            
                            // Send confirmation response
                            const confirmResponse = await fetch('/chat/confirm', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    confirmation_id: pendingConfirmation,
                                    confirmed: confirmed
                                })
                            });
                            
                            pendingConfirmation = null;
                            
                            // Handle the confirmation response
                            if (confirmResponse.ok) {
                                const result = await confirmResponse.json();
                                // Add the result to chat history if needed
                                const resultMessage = document.createElement('div');
                                resultMessage.textContent = `System: ${result.message}`;
                                resultMessage.className = 'system-message';
                                chatHistory.appendChild(resultMessage);
                            }
                        } else {
                            // Handle regular message chunks
                            const messageDiv = document.createElement('div');
                            messageDiv.textContent = `Agent: ${chunk.content}`;
                            messageDiv.className = 'agent-message';
                            chatHistory.appendChild(messageDiv);
                        }
                        
                        chatHistory.scrollTop = chatHistory.scrollHeight;
                    }
                }

                const form = document.getElementById('chat-form');
                const chatHistory = document.getElementById('chat-history');
                
                form.addEventListener('submit', async (event) => {
                    event.preventDefault();
                    const message = document.getElementById('message').value;

                    // Add user's message to the chat history
                    const userMessage = document.createElement('div');
                    userMessage.textContent = `You: ${message}`;
                    userMessage.className = 'user-message';
                    chatHistory.appendChild(userMessage);

                    // Clear the input field
                    document.getElementById('message').value = '';

                    // Handle the streaming response
                    await handleStream(message);
                });

            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
