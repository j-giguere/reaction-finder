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


// ========== Upload Modal ==========

const uploadModal = document.getElementById("upload-modal");
const addImageBtn = document.getElementById("add-image-btn");
const modalClose = document.getElementById("modal-close");
const uploadArea = document.getElementById("upload-area");
const fileInput = document.getElementById("file-input");

// Steps
const stepUpload = document.getElementById("step-upload");
const stepPreview = document.getElementById("step-preview");
const stepLoading = document.getElementById("step-loading");
const stepSuccess = document.getElementById("step-success");
const stepError = document.getElementById("step-error");

// Preview elements
const previewImage = document.getElementById("preview-image");
const editDescription = document.getElementById("edit-description");
const editTags = document.getElementById("edit-tags");

// Buttons
const btnBack = document.getElementById("btn-back");
const btnSave = document.getElementById("btn-save");
const btnDone = document.getElementById("btn-done");
const btnRetry = document.getElementById("btn-retry");
const errorMessage = document.getElementById("error-message");

// State
let selectedFile = null;
let generatedMetadata = null;

function showStep(step) {
    [stepUpload, stepPreview, stepLoading, stepSuccess, stepError].forEach(s => {
        s.style.display = "none";
    });
    step.style.display = "block";
}

function openModal() {
    uploadModal.classList.add("active");
    showStep(stepUpload);
    resetModal();
}

function closeModal() {
    uploadModal.classList.remove("active");
    resetModal();
}

function resetModal() {
    selectedFile = null;
    generatedMetadata = null;
    fileInput.value = "";
    editDescription.value = "";
    editTags.value = "";
    previewImage.src = "";
}

// Open/Close modal
addImageBtn.addEventListener("click", openModal);
modalClose.addEventListener("click", closeModal);

// Close on overlay click
uploadModal.addEventListener("click", (e) => {
    if (e.target === uploadModal) {
        closeModal();
    }
});

// Close on Escape key
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && uploadModal.classList.contains("active")) {
        closeModal();
    }
});

// Upload area click
uploadArea.addEventListener("click", () => {
    fileInput.click();
});

// Drag and drop
uploadArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadArea.classList.add("dragover");
});

uploadArea.addEventListener("dragleave", () => {
    uploadArea.classList.remove("dragover");
});

uploadArea.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadArea.classList.remove("dragover");
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
    }
});

// File input change
fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
        handleFileSelect(fileInput.files[0]);
    }
});

async function handleFileSelect(file) {
    // Validate file type
    const allowedTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];
    if (!allowedTypes.includes(file.type)) {
        showError("File type not allowed. Use JPEG, PNG, GIF, or WebP.");
        return;
    }

    // Validate file size (10MB)
    if (file.size > 10 * 1024 * 1024) {
        showError("File too large. Maximum size is 10MB.");
        return;
    }

    selectedFile = file;

    // Show preview immediately
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImage.src = e.target.result;
    };
    reader.readAsDataURL(file);

    // Show loading and upload
    showStep(stepLoading);
    await uploadAndGenerateMetadata();
}

async function uploadAndGenerateMetadata() {
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
        const response = await fetch("/api/upload", {
            method: "POST",
            body: formData,
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            showError(data.error || "Upload failed");
            return;
        }

        // Store the response data
        generatedMetadata = data.image;

        // Populate form with generated metadata
        editDescription.value = data.image.description;
        editTags.value = data.image.tags.join(", ");

        // Show preview step
        showStep(stepPreview);

    } catch (error) {
        console.error("Upload error:", error);
        showError("Upload failed. Please try again.");
    }
}

function showError(message) {
    errorMessage.textContent = message;
    showStep(stepError);
}

// Back button
btnBack.addEventListener("click", () => {
    showStep(stepUpload);
    selectedFile = null;
});

// Save button - metadata is already saved, just confirm
btnSave.addEventListener("click", () => {
    // In this implementation, metadata is saved during upload
    // The save button just confirms and closes
    showStep(stepSuccess);
});

// Done button
btnDone.addEventListener("click", () => {
    closeModal();
    // Show success message in chat
    addMessage("New reaction image added!", "system");
});

// Retry button
btnRetry.addEventListener("click", () => {
    showStep(stepUpload);
    resetModal();
});
