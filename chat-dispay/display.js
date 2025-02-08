<div id="displaywrap">
    <!-- Messages will be displayed here -->
</div>

<script>
async function handleSend() {
    const messageInput = document.getElementById("message");
    const message = messageInput?.value.trim();
    const username = localStorage.getItem("username");

    if (message && username) {
        displayMessage(username, message);

        // Show loading indicator
        displayMessage("RAI", "🔄 Analyzing... Please wait.", true);

        try {
            const response = await fetch("https://raigpt-production.up.railway.app/analyze", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ token_name: "RAI", user_query: message }),
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const data = await response.json();

            // Remove loading indicator before adding the response
            removeLastRAIMessage();
            displayMessage("RAI", data.analysis, true);
        } catch (err) {
            console.error("Error while sending request:", err);
            removeLastRAIMessage();
            displayMessage("RAI", "❌ Error during analysis. Please try again later.", true);
        }

        messageInput.value = ""; // Clear input field
    }
}

// Function to display messages in chat
function displayMessage(username, message, isAI = false) {
    const displaywrap = document.getElementById("displaywrap");
    if (displaywrap) {
        const messageContainer = document.createElement("div");
        messageContainer.classList.add("message-container");
        messageContainer.setAttribute("data-ai", isAI ? "true" : "false"); // Add attribute

        const nickname = document.createElement("span");
        nickname.textContent = `${username}: `;
        nickname.classList.add("nickname");
        nickname.style.color = isAI ? "#ff4500" : "#08ff00";
        nickname.style.fontFamily = "'Arturito', sans-serif";

        const messageText = document.createElement("span");
        messageText.textContent = message;
        messageText.classList.add("message-text");
        messageText.style.fontFamily = "'Arturito', sans-serif";

        messageContainer.appendChild(nickname);
        messageContainer.appendChild(messageText);
        displaywrap.appendChild(messageContainer);

        displaywrap.scrollTop = displaywrap.scrollHeight; // Auto-scroll
    }
}

// Function to remove the last RAI message (e.g., loading indicator)
function removeLastRAIMessage() {
    const displaywrap = document.getElementById("displaywrap");
    if (displaywrap) {
        const messages = displaywrap.querySelectorAll('.message-container[data-ai="true"]');
        if (messages.length > 0) {
            displaywrap.removeChild(messages[messages.length - 1]);
        }
    }
}

// Send button handler
document.addEventListener("DOMContentLoaded", () => {
    const sendButton = document.getElementById("sendMessage");
    const messageInput = document.getElementById("message");

    sendButton?.addEventListener("click", handleSend);
    messageInput?.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            handleSend();
        }
    });
});
</script>

<style>
    /* Chat container */
    #displaywrap {
        max-height: 400px; /* Limit height for scrollbar appearance */
        overflow-y: auto; /* Enable vertical scrolling */
        background: transparent; /* Transparent background */
        padding: 0px;
        border-radius: 8px; /* Rounded corners */
    }

    /* Scrollbar styling */
    #displaywrap::-webkit-scrollbar {
        width: 6px; /* Thin scrollbar */
    }

    #displaywrap::-webkit-scrollbar-track {
        background: transparent; /* Transparent track */
    }

    #displaywrap::-webkit-scrollbar-thumb {
        background: #08ff00; /* Green scrollbar thumb */
        border-radius: 3px; /* Rounded edges */
    }

    /* Scrollbar styling for Firefox */
    #displaywrap {
        scrollbar-width: thin;
        scrollbar-color: #08ff00 transparent;
    }

    /* General message container */
    .message-container {
        display: block; /* Block element to separate messages */
        margin-bottom: 12px; /* Space between messages */
        word-wrap: break-word;
        overflow-wrap: break-word;
    }

    /* Username styling */
    .nickname {
        font-weight: bold; /* Bold text */
        white-space: nowrap; /* Prevent username wrapping */
    }

    /* Message text styling */
    .message-text {
        display: inline; /* Keep message inline with username */
        word-wrap: break-word;
        overflow-wrap: break-word;
        white-space: normal; /* Allow text wrapping */
    }
</style>
