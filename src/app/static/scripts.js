const modalHtml = `
<div id="confirmation-modal" class="modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); z-index: 1000;">
    <div class="modal-content" style="position: relative; background-color: white; margin: 15% auto; padding: 20px; border-radius: 5px; width: 80%; max-width: 500px;">
        <p id="confirmation-message"></p>
        <div style="margin-top: 20px; text-align: right;">
            <button id="confirm-yes" class="button">Yes</button>
            <button id="confirm-no" class="button" style="margin-left: 10px;">No</button>
        </div>
    </div>
</div>
`;
document.body.insertAdjacentHTML('beforeend', modalHtml);

const modal = document.getElementById('confirmation-modal');
const confirmationMessage = document.getElementById('confirmation-message');
const confirmYesButton = document.getElementById('confirm-yes');
const confirmNoButton = document.getElementById('confirm-no');

const form = document.getElementById('chat-form');
const chatHistory = document.getElementById('chat-history');


async function handleConfirmation(message) {
    return new Promise((resolve) => {
        // Show the modal and set the message
        modal.style.display = 'block';
        confirmationMessage.textContent = message;

        // Handle Yes button
        confirmYesButton.onclick = () => {
            modal.style.display = 'none';
            resolve('yes');
        };

        // Handle No button
        confirmNoButton.onclick = () => {
            modal.style.display = 'none';
            resolve('no');
        };
    });
}


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
                // Show confirmation dialog and wait for response
                const userChoice = await handleConfirmation(parsedResponse.interrupt);

                // Send the user's response back to the server
                const confirmResponse = await fetch('/chat/message', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ content: userChoice })
                });

                if (!confirmResponse.ok) {
                    throw new Error(`HTTP error! status: ${confirmResponse.status}`);
                }

                // Add the confirmation response to the chat
                const confirmMessage = document.createElement('div');
                confirmMessage.textContent = `You: ${userChoice}`;
                confirmMessage.className = 'user-message';
                chatHistory.appendChild(confirmMessage);
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
