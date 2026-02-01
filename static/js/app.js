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
const btnCancel = document.getElementById("btn-cancel");
const errorMessage = document.getElementById("error-message");

// State
let selectedFile = null;
let pendingUploadId = null;
let uploadAbortController = null;

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

async function resetModal() {
    // Abort any in-flight upload request
    if (uploadAbortController) {
        uploadAbortController.abort();
        uploadAbortController = null;
    }
    // Cancel any pending upload on the server
    if (pendingUploadId) {
        try {
            await fetch("/api/upload/cancel", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ upload_id: pendingUploadId }),
            });
        } catch (e) {
            console.log("Failed to cancel upload:", e);
        }
        pendingUploadId = null;
    }
    selectedFile = null;
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

    // Create abort controller for this request
    uploadAbortController = new AbortController();

    try {
        const response = await fetch("/api/upload", {
            method: "POST",
            body: formData,
            signal: uploadAbortController.signal,
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            showError(data.error || "Upload failed");
            return;
        }

        // Store the upload ID for later confirmation
        pendingUploadId = data.upload_id;

        // Populate form with generated metadata
        editDescription.value = data.metadata.description;
        editTags.value = data.metadata.tags.join(", ");

        // Show preview step
        showStep(stepPreview);

    } catch (error) {
        // Ignore abort errors (user cancelled)
        if (error.name === "AbortError") {
            console.log("Upload cancelled by user");
            return;
        }
        console.error("Upload error:", error);
        showError("Upload failed. Please try again.");
    } finally {
        uploadAbortController = null;
    }
}

function showError(message) {
    errorMessage.textContent = message;
    showStep(stepError);
}

// Back button - cancel the pending upload
btnBack.addEventListener("click", async () => {
    await resetModal();
    showStep(stepUpload);
});

// Save button - confirm the upload and save permanently
btnSave.addEventListener("click", async () => {
    if (!pendingUploadId) {
        showError("No pending upload to save");
        return;
    }

    // Parse tags from comma-separated input
    const tags = editTags.value
        .split(",")
        .map(t => t.trim().toLowerCase())
        .filter(t => t.length > 0);

    try {
        const response = await fetch("/api/upload/confirm", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                upload_id: pendingUploadId,
                description: editDescription.value.trim(),
                tags: tags,
            }),
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            showError(data.error || "Failed to save image");
            return;
        }

        pendingUploadId = null;  // Clear since it's now saved
        showStep(stepSuccess);

    } catch (error) {
        console.error("Save error:", error);
        showError("Failed to save image. Please try again.");
    }
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

// Cancel button (during loading)
btnCancel.addEventListener("click", () => {
    resetModal();  // This will abort the request
    showStep(stepUpload);
});
