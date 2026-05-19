const API_URL = "http://127.0.0.1:5001";

async function uploadFile() {
    const fileInput = document.getElementById("fileInput");
    const file = fileInput.files[0];

    if (!file) {
        alert("Please select a file");
        return;
    }

    const statusEl = document.getElementById("docStatus");
    statusEl.textContent = "Uploading and processing...";
    statusEl.style.color = "orange";

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch(`${API_URL}/upload`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            updateDocumentStatus();
        } else {
            alert("Error: " + data.error);
            statusEl.textContent = "Upload failed";
            statusEl.style.color = "red";
        }
    } catch (error) {
        alert("Error uploading file: " + error.message);
        statusEl.textContent = "Upload failed";
        statusEl.style.color = "red";
    }
}

async function askQuestion() {
    const input = document.getElementById("questionInput");
    const question = input.value.trim();

    if (!question) return;

    addUserMessage(question);
    input.value = "";

    // Show typing indicator
    const typingId = addTypingIndicator();

    try {
        const response = await fetch(`${API_URL}/ask`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question })
        });

        const data = await response.json();
        removeTypingIndicator(typingId);

        if (response.ok) {
            addBotMessage(data.answer, data.sources, data.confidence, data.is_out_of_scope);
        } else {
            addErrorMessage("Error: " + data.error);
        }
    } catch (error) {
        removeTypingIndicator(typingId);
        addErrorMessage("Connection error: " + error.message);
    }
}

function addUserMessage(text) {
    const chatBox = document.getElementById("chatBox");
    const div = document.createElement("div");
    div.classList.add("message", "message-user");
    div.innerHTML = `<strong class="label-user">You:</strong><p class="message-text">${escapeHtml(text)}</p>`;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function addBotMessage(text, sources = [], confidence = 0, isOutOfScope = false) {
    const chatBox = document.getElementById("chatBox");
    const div = document.createElement("div");
    div.classList.add("message", "message-bot");

    // Format the answer: convert newlines to <br>, bold numbered steps
    const formattedText = formatAnswer(text);

    // Confidence badge
    const confidenceColor = confidence >= 70 ? '#27ae60' : confidence >= 40 ? '#f39c12' : '#e74c3c';
    const confidenceHTML = confidence > 0 ? `
        <div class="confidence-bar">
            <span>Confidence: <strong style="color:${confidenceColor}">${confidence.toFixed(0)}%</strong></span>
            <div class="bar-track"><div class="bar-fill" style="width:${confidence}%;background:${confidenceColor}"></div></div>
        </div>` : '';

    // Out of scope warning
    const outOfScopeHTML = isOutOfScope ? `
        <div class="out-of-scope">⚠️ This question may be outside the scope of the uploaded documents.</div>` : '';

    // Sources section
    let sourcesHTML = '';
    if (sources && sources.length > 0 && !isOutOfScope) {
        const sourceItems = sources.map((s, i) => `
            <div class="source-item">
                <strong>Source ${i + 1}:</strong> ${escapeHtml(s.document)} — Page ${s.page}
                <br><small>${escapeHtml(s.content)}</small>
            </div>`).join('');
        sourcesHTML = `
            <div class="source-section">
                <strong>📄 Referenced Sources:</strong>
                ${sourceItems}
            </div>`;
    }

    div.innerHTML = `
        <strong class="label-bot">Bot:</strong>
        <div class="message-text">${formattedText}</div>
        ${confidenceHTML}
        ${outOfScopeHTML}
        ${sourcesHTML}
    `;

    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function addErrorMessage(text) {
    const chatBox = document.getElementById("chatBox");
    const div = document.createElement("div");
    div.classList.add("message", "message-error");
    div.innerHTML = `<strong class="label-error">Error:</strong><p class="message-text">${escapeHtml(text)}</p>`;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function addTypingIndicator() {
    const chatBox = document.getElementById("chatBox");
    const div = document.createElement("div");
    const id = "typing-" + Date.now();
    div.id = id;
    div.classList.add("message", "message-bot", "typing-indicator");
    div.innerHTML = `<strong class="label-bot">Bot:</strong><p class="message-text">Thinking<span class="dots">...</span></p>`;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function formatAnswer(text) {
    if (!text) return '';

    const lines = text.split('\n');
    let html = '';
    let inList = false;
    let inSubList = false;

    for (let line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        // Numbered step: "1. something"
        const numberedMatch = trimmed.match(/^(\d+)\.\s+(.+)/);
        // Sub-point: "- something"
        const subMatch = trimmed.match(/^[-•]\s+(.+)/);

        if (numberedMatch) {
            if (inSubList) { html += '</ul>'; inSubList = false; }
            if (!inList) { html += '<ol>'; inList = true; }
            html += `<li>${escapeHtml(numberedMatch[2])}</li>`;
        } else if (subMatch) {
            if (!inSubList) { html += '<ul class="sub-list">'; inSubList = true; }
            html += `<li>${escapeHtml(subMatch[1])}</li>`;
        } else {
            if (inSubList) { html += '</ul>'; inSubList = false; }
            if (inList) { html += '</ol>'; inList = false; }
            html += `<p class="answer-para">${escapeHtml(trimmed)}</p>`;
        }
    }

    if (inSubList) html += '</ul>';
    if (inList) html += '</ol>';

    return html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

async function updateDocumentStatus() {
    try {
        const response = await fetch(`${API_URL}/documents`);
        const data = await response.json();
        const statusEl = document.getElementById("docStatus");

        if (data.length > 0) {
            const names = data.map(d => d.filename).join(', ');
            statusEl.textContent = `${data.length} document(s) uploaded: ${names}`;
            statusEl.style.color = 'green';
        } else {
            statusEl.textContent = "No documents uploaded";
            statusEl.style.color = 'gray';
        }
    } catch (error) {
        console.error("Error fetching document status:", error);
    }
}

async function resetChat() {
    try {
        await fetch(`${API_URL}/reset`, { method: "POST" });
        document.getElementById("chatBox").innerHTML = "";
    } catch (error) {
        alert("Error resetting chat: " + error.message);
    }
}

async function clearAll() {
    if (!confirm("This will clear all uploaded documents and chat history. Continue?")) return;

    try {
        await fetch(`${API_URL}/clear`, { method: "POST" });
        document.getElementById("chatBox").innerHTML = "";
        document.getElementById("fileInput").value = "";
        updateDocumentStatus();
    } catch (error) {
        alert("Error clearing data: " + error.message);
    }
}

// Allow Enter key to send
document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("questionInput");
    if (input) {
        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                askQuestion();
            }
        });
    }
    updateDocumentStatus();
});
