const chatForm = document.getElementById("chat-form");
const promptInput = document.getElementById("prompt-input");
const chatMessages = document.getElementById("chat-messages");

function addMessage(content, type) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${type}`;

    if (type === "bot") {
        const img = document.createElement("img");
        img.src = content;
        img.alt = "Reaction image";
        messageDiv.appendChild(img);
    } else {
        messageDiv.textContent = content;
    }

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function sendPrompt(prompt) {
    try {
        const response = await fetch("/api/react", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ prompt }),
        });

        if (!response.ok) {
            throw new Error("Failed to get reaction");
        }

        const data = await response.json();
        addMessage(data.image_url, "bot");
    } catch (error) {
        console.error("Error:", error);
        addMessage("Failed to get reaction image", "system");
    }
}

chatForm.addEventListener("submit", (e) => {
    e.preventDefault();

    const prompt = promptInput.value.trim();
    if (!prompt) return;

    addMessage(prompt, "user");
    promptInput.value = "";

    sendPrompt(prompt);
});
