const form = document.getElementById('chat-form');
const chatHistory = document.getElementById('chat-history');

form.onsubmit = async function (event) {
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
        const response = await fetch('/chat/message', {
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

            const parsedResponse = JSON.parse(text);
            console.log("Parsed response:", parsedResponse);

            if (parsedResponse.message) {
                currentText += parsedResponse.message;
                agentMessage.textContent = `Agent: ${currentText}`;
            }

            if (parsedResponse.interrupt) {
                await handleInterrupt(parsedResponse);
                break; // Stop processing additional responses if interrupt is triggered
            }

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
                    user_id: 'test-user-1'
                })
            });

            if (response.ok) {
                interruptMessage.textContent = isConfirm ? 'Confirmed.' : 'Cancelled.';
            }
        };
        return button;
    }

    chatHistory.scrollTop = chatHistory.scrollHeight;
}