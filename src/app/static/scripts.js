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
                        }
                    }

                    chatHistory.scrollTop = chatHistory.scrollHeight;
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
