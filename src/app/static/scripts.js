const form = document.getElementById('chat-form');
const chatHistory = document.getElementById('chat-history');

form.onsubmit = async function (event) {
    event.preventDefault();

    const messageInput = document.getElementById('message');
    const message = messageInput.value;
    console.log("Sending message:", message);

    // Add user message
    const userMessage = document.createElement('div');
    userMessage.innerHTML = `<strong>You:</strong> ${message}`;
    userMessage.className = 'user-message';
    chatHistory.appendChild(userMessage);

    // Clear input
    messageInput.value = '';

    try {
        const response = await fetch('/chat/message_stream', {
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

        let finalMessage = '';
        let statusMessage = null;

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const text = decoder.decode(value);
            console.log("Received text:", text);

            const messages = text.split('\n').filter(line => line.trim());

            for (const message of messages) {
                try {
                    const parsedResponse = JSON.parse(message);
                    console.log("Parsed response:", parsedResponse);

                    // Update final message but don't display yet
                    if (parsedResponse.message) {
                        finalMessage = parsedResponse.message;
                    }

                    // Handle tool status updates
                    if (parsedResponse.tool_status) {
                        // Remove existing status message if it exists
                        if (statusMessage) {
                            statusMessage.remove();
                        }
                        // Create new status message
                        statusMessage = document.createElement('div');
                        statusMessage.className = 'agent-message status-message';
                        statusMessage.innerHTML = `
                            <strong>Agent:</strong> 
                            <span class="loading-spinner"></span>
                            ${parsedResponse.tool_status}
                        `;
                        chatHistory.appendChild(statusMessage);
                    }

                    if (parsedResponse.interrupt) {
                        if (statusMessage) {
                            statusMessage.remove();
                        }
                        await handleInterrupt(parsedResponse);
                        return;
                    }

                    if (parsedResponse.error) {
                        const errorDiv = document.createElement('div');
                        errorDiv.textContent = `Error: ${parsedResponse.error}`;
                        errorDiv.className = 'system-message error';
                        chatHistory.appendChild(errorDiv);
                    }
                } catch (e) {
                    console.error("Error parsing message:", e);
                }
            }

            chatHistory.scrollTop = chatHistory.scrollHeight;
        }

        // Remove status message when done
        if (statusMessage) {
            statusMessage.remove();
        }

        // Add final message only at the end
        if (finalMessage) {
            const agentMessage = document.createElement('div');
            agentMessage.className = 'agent-message';
            agentMessage.style.whiteSpace = 'pre-wrap';
            agentMessage.innerHTML = `<strong>Agent:</strong> ${finalMessage}`;
            chatHistory.appendChild(agentMessage);
            chatHistory.scrollTop = chatHistory.scrollHeight;
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


async function handleInterrupt(interruptData) {
    const interruptMessage = document.createElement('div');
    interruptMessage.textContent = interruptData.message;
    interruptMessage.className = 'interrupt-message';
    chatHistory.appendChild(interruptMessage);

    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'button-container';
    buttonContainer.appendChild(createButton('Confirm', true));
    buttonContainer.appendChild(createButton('Cancel', false));
    chatHistory.appendChild(buttonContainer);

    function createButton(text, isConfirm) {
        const button = document.createElement('button');
        button.textContent = text;
        button.className = isConfirm ? 'confirm-button' : 'cancel-button';
        button.onclick = async () => {
            buttonContainer.remove();
            const response = await fetch('/chat/confirm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    confirmed: isConfirm,
                    user_id: 'test-user-1' // TODO: Replace with actual user ID
                })
            });

            if (response.ok) {
                const data = await response.json();
                interruptMessage.style.whiteSpace = 'pre-wrap';
                interruptMessage.textContent = data.message;
            }
        };
        return button;
    }

    chatHistory.scrollTop = chatHistory.scrollHeight;
}