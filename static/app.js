document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const uploadPanel = document.getElementById("upload-panel");
    const readerPanel = document.getElementById("reader-panel");
    const processingCard = document.getElementById("processing-card");
    const uploadCard = document.querySelector(".upload-card");

    const dragZone = document.getElementById("drag-zone");
    const audioInput = document.getElementById("audio-input");
    const fileSelectedContent = document.getElementById("file-selected-content");
    const dragZoneContent = document.querySelector(".drag-zone-content");
    const selectedFileName = document.getElementById("selected-file-name");
    const removeFileBtn = document.getElementById("remove-file-btn");

    const uploadForm = document.getElementById("upload-form");
    const submitBtn = document.getElementById("submit-btn");
    const processingStatus = document.getElementById("processing-status");

    const historyList = document.getElementById("history-list");
    const searchInput = document.getElementById("search-input");
    const newSummaryBtn = document.getElementById("new-btn");

    const summaryTitle = document.getElementById("summary-title");
    const summaryDate = document.getElementById("summary-date");
    const summaryBody = document.getElementById("summary-body");
    const transcriptBody = document.getElementById("transcript-body");
    const tabSummaryBtn = document.getElementById("tab-summary-btn");
    const tabTranscriptBtn = document.getElementById("tab-transcript-btn");
    const reusedBadge = document.getElementById("reused-badge");
    const pendingBadge = document.getElementById("pending-badge");
    const regenerateBtn = document.getElementById("regenerate-btn");

    const statTranscribeTime = document.getElementById("stat-transcribe-time");
    const statDiarizeTime = document.getElementById("stat-diarize-time");
    const statSummarizeTime = document.getElementById("stat-summarize-time");
    const statTime = document.getElementById("stat-time");
    const statPromptTokens = document.getElementById("stat-prompt-tokens");
    const statOutputTokens = document.getElementById("stat-output-tokens");
    const statTotalTokens = document.getElementById("stat-total-tokens");

    const copyBtn = document.getElementById("copy-btn");
    const downloadMdBtn = document.getElementById("download-md-btn");
    const deleteBtn = document.getElementById("delete-btn");
    const toast = document.getElementById("toast");

    let historyData = [];
    let currentSummary = null;

    // Toast helper
    function showToast(message) {
        toast.textContent = message;
        toast.classList.remove("hidden");
        setTimeout(() => {
            toast.classList.add("hidden");
        }, 3000);
    }

    // Load history
    async function loadHistory() {
        try {
            const response = await fetch("/api/conversions");
            if (!response.ok) throw new Error("Failed to load history");
            historyData = await response.json();
            renderHistory(historyData);
        } catch (error) {
            console.error(error);
            historyList.innerHTML = `<div class="empty-state">Error loading history</div>`;
        }
    }

    // Render history sidebar
    function renderHistory(items) {
        if (items.length === 0) {
            historyList.innerHTML = `<div class="empty-state">No conversions yet</div>`;
            return;
        }

        historyList.innerHTML = items.map(item => `
            <div class="history-item" data-hash="${item.hash}">
                <h4>${item.has_summary ? "" : "⏳ "}${item.title}</h4>
                <div class="history-meta">
                    <span class="history-date">${item.date}</span>
                    <span>${item.has_summary ? (item.stats.total_tokens / 1000).toFixed(1) + 'k tokens' : 'Summary pending'}</span>
                </div>
            </div>
        `).join("");

        // Add click listeners to items
        document.querySelectorAll(".history-item").forEach(el => {
            el.addEventListener("click", () => {
                const hash = el.getAttribute("data-hash");
                const item = historyData.find(i => i.hash === hash);
                if (item) loadSummary(item);
            });
        });
    }

    // Filter history on search
    searchInput.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().strip();
        const filtered = historyData.filter(item =>
            item.title.toLowerCase().includes(query) ||
            item.original_filename.toLowerCase().includes(query)
        );
        renderHistory(filtered);
    });

    // Load and display a selected summary
    async function loadSummary(item) {
        // Highlight active item
        document.querySelectorAll(".history-item").forEach(el => {
            el.classList.toggle("active", el.getAttribute("data-hash") === item.hash);
        });

        try {
            const response = await fetch(`/api/conversions/${item.hash}`);
            if (!response.ok) throw new Error("Failed to fetch summary file");

            const data = await response.json();
            displaySummary(item, data.content, data.transcript);
        } catch (error) {
            console.error(error);
            showToast("Failed to load summary content");
        }
    }

    // Switch between the Summary and Transcript tabs
    function showTab(tab) {
        const showSummary = tab === "summary";
        summaryBody.classList.toggle("hidden", !showSummary);
        transcriptBody.classList.toggle("hidden", showSummary);
        tabSummaryBtn.classList.toggle("active", showSummary);
        tabTranscriptBtn.classList.toggle("active", !showSummary);
    }

    tabSummaryBtn.addEventListener("click", () => showTab("summary"));
    tabTranscriptBtn.addEventListener("click", () => showTab("transcript"));

    // Render summary UI
    function displaySummary(item, content, transcript) {
        const hasSummary = item.has_summary !== undefined ? item.has_summary : content != null;
        currentSummary = { ...item, content, transcript, has_summary: hasSummary };

        summaryTitle.textContent = item.title;
        summaryDate.textContent = item.date;

        if (item.reused) {
            reusedBadge.classList.remove("hidden");
        } else {
            reusedBadge.classList.add("hidden");
        }
        pendingBadge.classList.toggle("hidden", hasSummary);
        regenerateBtn.textContent = hasSummary ? "🔁 Regenerate Summary" : "🔁 Generate Summary";

        if (hasSummary) {
            // Render markdown to HTML using Marked
            // First strip off any leading headers to avoid repeating the title
            let cleanContent = content;
            const lines = content.split('\n');
            if (lines[0] && lines[0].startsWith('#')) {
                cleanContent = lines.slice(1).join('\n');
            }
            summaryBody.innerHTML = marked.parse(cleanContent);
            showTab("summary");
        } else {
            summaryBody.innerHTML = `<p class="empty-state">No summary yet. The transcript was saved, but the LLM call hasn't produced a summary. Use "Generate Summary" to run it.</p>`;
            showTab("transcript");
        }
        transcriptBody.textContent = transcript || "No transcript available.";

        // Render stats
        const formatSeconds = (value) => (value != null ? `${value}s` : "-");
        if (item.stats) {
            statTranscribeTime.textContent = formatSeconds(item.stats.transcribe_seconds);
            statDiarizeTime.textContent = formatSeconds(item.stats.diarize_seconds);
            statSummarizeTime.textContent = formatSeconds(item.stats.summarize_seconds);
            statTime.textContent = formatSeconds(item.stats.total_seconds);
            statPromptTokens.textContent = (item.stats.prompt_tokens ?? 0).toLocaleString();
            statOutputTokens.textContent = (item.stats.completion_tokens ?? 0).toLocaleString();
            statTotalTokens.textContent = (item.stats.total_tokens ?? 0).toLocaleString();
        } else {
            statTranscribeTime.textContent = "-";
            statDiarizeTime.textContent = "-";
            statSummarizeTime.textContent = "-";
            statTime.textContent = "-";
            statPromptTokens.textContent = "-";
            statOutputTokens.textContent = "-";
            statTotalTokens.textContent = "-";
        }

        // Switch panels
        uploadPanel.classList.add("hidden");
        readerPanel.classList.remove("hidden");
    }

    // Switch back to upload view
    newSummaryBtn.addEventListener("click", () => {
        readerPanel.classList.add("hidden");
        uploadPanel.classList.remove("hidden");
        uploadCard.classList.remove("hidden");
        processingCard.classList.add("hidden");
        resetUploadForm();
    });

    // Reset upload form state
    function resetUploadForm() {
        audioInput.value = "";
        selectedFileName.textContent = "";
        fileSelectedContent.classList.add("hidden");
        dragZoneContent.classList.remove("hidden");
        submitBtn.disabled = true;
    }

    // Handle drag and drop events
    ["dragenter", "dragover"].forEach(eventName => {
        dragZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dragZone.classList.add("dragging");
        }, false);
    });

    ["dragleave", "drop"].forEach(eventName => {
        dragZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dragZone.classList.remove("dragging");
        }, false);
    });

    dragZone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            audioInput.files = files;
            handleFileSelected(files[0]);
        }
    });

    audioInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFileSelected(e.target.files[0]);
        }
    });

    function handleFileSelected(file) {
        selectedFileName.textContent = file.name;
        dragZoneContent.classList.add("hidden");
        fileSelectedContent.classList.remove("hidden");
        submitBtn.disabled = false;
    }

    removeFileBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        resetUploadForm();
    });

    // Handle form submission
    uploadForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        if (audioInput.files.length === 0) return;

        const file = audioInput.files[0];
        const formData = new FormData();
        formData.append("audio", file);

        const userTitle = document.getElementById("title-input").value.trim();
        if (userTitle) {
            formData.append("title", userTitle);
        }

        const forceRerunCheckbox = document.getElementById("force-rerun");
        if (forceRerunCheckbox.checked) {
            formData.append("force_rerun", "true");
        }

        // Update UI state to processing
        uploadCard.classList.add("hidden");
        processingCard.classList.remove("hidden");
        processingStatus.textContent = "Converting and transcribing audio...";

        // Simulate status update
        setTimeout(() => {
            if (!uploadCard.classList.contains("hidden")) return;
            processingStatus.textContent = "Diarizing speakers and summarizing...";
        }, 4000);

        try {
            const response = await fetch("/api/convert", {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || "Conversion failed");
            }

            const result = await response.json();

            // Reload history to include new conversion
            await loadHistory();

            // Render the summary details
            displaySummary(result, result.content, result.transcript);
            showToast(result.reused ? "Loaded existing summary from cache!" : "Summary generated successfully!");
        } catch (error) {
            console.error(error);
            uploadCard.classList.remove("hidden");
            processingCard.classList.add("hidden");
            alert(`Error: ${error.message}`);
        }
    });

    // Regenerate / generate the summary from the saved transcript
    regenerateBtn.addEventListener("click", async () => {
        if (!currentSummary) return;

        regenerateBtn.disabled = true;
        regenerateBtn.textContent = "⏳ Generating...";

        try {
            const response = await fetch(`/api/conversions/${currentSummary.hash}/summarize`, {
                method: "POST",
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || "Failed to generate summary");
            }

            const result = await response.json();
            await loadHistory();
            displaySummary(result, result.content, result.transcript);
            showToast("Summary generated successfully!");
        } catch (error) {
            console.error(error);
            showToast(`Error: ${error.message}`);
            regenerateBtn.textContent = currentSummary.has_summary ? "🔁 Regenerate Summary" : "🔁 Generate Summary";
        } finally {
            regenerateBtn.disabled = false;
        }
    });

    // Copy Markdown to Clipboard
    copyBtn.addEventListener("click", () => {
        if (!currentSummary || !currentSummary.has_summary) {
            showToast("No summary yet to copy");
            return;
        }
        navigator.clipboard.writeText(currentSummary.content).then(() => {
            showToast("Copied markdown summary to clipboard!");
        }).catch(err => {
            console.error(err);
            showToast("Failed to copy summary");
        });
    });

    // Download Markdown File
    downloadMdBtn.addEventListener("click", () => {
        if (!currentSummary || !currentSummary.has_summary) {
            showToast("No summary yet to download");
            return;
        }
        const blob = new Blob([currentSummary.content], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${currentSummary.filename_base}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast("Summary download started!");
    });

    // Delete a conversation
    deleteBtn.addEventListener("click", async () => {
        if (!currentSummary) return;

        if (confirm("Are you sure you want to delete this conversion? This action cannot be undone.")) {
            try {
                const response = await fetch(`/api/conversions/${currentSummary.hash}`, {
                    method: "DELETE",
                });

                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.error || "Failed to delete conversion");
                }

                showToast("Conversion deleted successfully!");
                await loadHistory();
                newSummaryBtn.click(); // Return to main screen

            } catch (error) {
                console.error(error);
                showToast(`Error: ${error.message}`);
            }
        }
    });

    // Initial load
    loadHistory();
});

// String trim polyfill for older setups if necessary
if (!String.prototype.strip) {
    String.prototype.strip = function() {
        return this.trim();
    };
}
