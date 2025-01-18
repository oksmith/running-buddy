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


@app.get("/chat-ui", response_class=HTMLResponse)
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
                    width: 800px;
                    max-width: 90vw;
                    border: 2px solid #ccc;
                    border-radius: 8px;
                    padding: 16px;
                    background-color: #fff;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }
                #chat-history {
                    height: 600px;
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
                <form id="chat-form" action="javascript:void(0);">
                    <label for="message">Your message:</label>
                    <input type="text" id="message" name="message" placeholder="Type your message here">
                    <input type="submit" value="Send">
                </form>
            </div>
            <script>
            const form = document.getElementById('chat-form');
            const chatHistory = document.getElementById('chat-history');
            
            form.onsubmit = async function(event) {
                event.preventDefault();
                
                const messageInput = document.getElementById('message');
                const message = messageInput.value;
                console.log("Sending message:", message);

                // Add user message
                const userMessage = document.createElement('div');
                userMessage.textContent = `You: ${message}`;
                userMessage.className = 'user-message';
                chatHistory.appendChild(userMessage);

                // Clear input
                messageInput.value = '';

                try {
                    const response = await fetch('/chat/stream', {
                        method: 'POST',
                        headers: { 
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ content: message })
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();

                    // Create a single message div for the agent's response
                    const agentMessage = document.createElement('div');
                    agentMessage.className = 'agent-message';
                    agentMessage.style.whiteSpace = 'pre-wrap';
                    agentMessage.textContent = 'Agent: ';
                    chatHistory.appendChild(agentMessage);

                    let currentText = '';

                    while (true) {
                        const { value, done } = await reader.read();
                        if (done) break;
                        
                        const text = decoder.decode(value);
                        console.log("Received text:", text);
                        
                        text.split('\\n').forEach(line => {
                            if (!line.trim()) return;
                            
                            try {
                                const chunk = JSON.parse(line);
                                console.log("Parsed chunk:", chunk);
                                
                                if (chunk.type === 'message' && chunk.content) {
                                    if (!chunk.tool_call_id) {
                                        currentText += chunk.content;
                                        agentMessage.textContent = `Agent: ${currentText}`;
                                        chatHistory.scrollTop = chatHistory.scrollHeight;
                                    }
                                }
                            } catch (e) {
                                console.error('Failed to parse line:', line, e);
                            }
                        });
                    }
                } catch (error) {
                    console.error("Error:", error);
                    const errorDiv = document.createElement('div');
                    errorDiv.textContent = `Error: ${error.message}`;
                    errorDiv.className = 'system-message';
                    chatHistory.appendChild(errorDiv);
                }
                
                return false;
            };
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
