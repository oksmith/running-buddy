// Handle human confirmation button
async function handleConfirmation(confirmationId) {
    const confirmationDiv = document.createElement('div');
    confirmationDiv.className = 'confirmation-dialog';
    confirmationDiv.innerHTML = `
        <p>Do you want to proceed with this action?</p>
        <div class="confirmation-buttons">
            <button class="confirm-btn">Yes</button>
            <button class="cancel-btn">No</button>
        </div>
    `;
    chatHistory.appendChild(confirmationDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    // Add event listeners
    
    confirmationDiv.querySelector('.confirm-btn').addEventListener('click', () => {
        console.log('Confirm button clicked');
        sendConfirmation(confirmationId, true);
    });
    confirmationDiv.querySelector('.cancel-btn').addEventListener('click', () => {
        console.log('Cancel button clicked');
        sendConfirmation(confirmationId, false);
    });
}

// Send human confirmation message
async function sendConfirmation(confirmationId, confirmed) {
    try {
        const response = await fetch('/chat/confirm', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                confirmation_id: confirmationId,
                confirmed: confirmed
            })
        });
        
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        // Remove the confirmation dialog
        const dialogs = document.querySelectorAll('.confirmation-dialog');
        dialogs.forEach(dialog => dialog.remove());
        // Now, send back the confirmation value to the graph
        // response : {"status": "success", "message": "Confirmation received"}
        
    } catch (error) {
        console.error("Error sending confirmation:", error);
        // Display an error message to the user
        const errorDiv = document.createElement('div');
        errorDiv.textContent = `Error: ${error.message}`;
        errorDiv.className = 'system-message';
        chatHistory.appendChild(errorDiv);
    }
}

// Form submission
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
            
            if (parsedResponse.requires_confirmation) {
                handleConfirmation(parsedResponse.confirmation_id);
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
