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
    const modelSelect = document.getElementById("model-select");
    const submitBtn = document.getElementById("submit-btn");
    const processingStatus = document.getElementById("processing-status");
    
    const historyList = document.getElementById("history-list");
    const searchInput = document.getElementById("search-input");
    const newSummaryBtn = document.getElementById("new-btn");
    
    const summaryTitle = document.getElementById("summary-title");
    const summaryDate = document.getElementById("summary-date");
    const summaryBody = document.getElementById("summary-body");
    const reusedBadge = document.getElementById("reused-badge");
    
    const statTime = document.getElementById("stat-time");
    const statPromptTokens = document.getElementById("stat-prompt-tokens");
    const statOutputTokens = document.getElementById("stat-output-tokens");
    const statTotalTokens = document.getElementById("stat-total-tokens");
    
    const copyBtn = document.getElementById("copy-btn");
    const downloadMdBtn = document.getElementById("download-md-btn");
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
                <h4>${item.title}</h4>
                <div class="history-meta">
                    <span class="history-date">${item.date}</span>
                    <span>${item.stats ? (item.stats.total_tokens / 1000).toFixed(1) + 'k' : '0'} tokens</span>
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
            const response = await fetch(`/api/conversions/${item.date}/${item.filename_base}.md`);
            if (!response.ok) throw new Error("Failed to fetch summary file");
            
            const data = await response.json();
            displaySummary(item, data.content);
        } catch (error) {
            console.error(error);
            showToast("Failed to load summary content");
        }
    }

    // Render summary UI
    function displaySummary(item, content) {
        currentSummary = { ...item, content };
        
        summaryTitle.textContent = item.title;
        summaryDate.textContent = item.date;
        
        if (item.reused) {
            reusedBadge.classList.remove("hidden");
        } else {
            reusedBadge.classList.add("hidden");
        }

        // Render markdown to HTML using Marked
        // First strip off any leading headers to avoid repeating the title
        let cleanContent = content;
        const lines = content.split('\n');
        if (lines[0] && lines[0].startsWith('#')) {
            cleanContent = lines.slice(1).join('\n');
        }
        
        // Render markdown body
        summaryBody.innerHTML = marked.parse(cleanContent);

        // Render stats
        if (item.stats) {
            statTime.textContent = `${item.stats.conversion_time}s`;
            statPromptTokens.textContent = item.stats.prompt_tokens.toLocaleString();
            statOutputTokens.textContent = item.stats.output_tokens.toLocaleString();
            statTotalTokens.textContent = item.stats.total_tokens.toLocaleString();
        } else {
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
        formData.append("model", modelSelect.value);

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
        processingStatus.textContent = "Uploading to Gemini API...";

        // Simulate status update
        setTimeout(() => {
            if (!uploadCard.classList.contains("hidden")) return;
            processingStatus.textContent = "Processing audio with Gemini...";
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
            displaySummary(result, result.content);
            showToast(result.reused ? "Loaded existing summary from cache!" : "Summary generated successfully!");
        } catch (error) {
            console.error(error);
            uploadCard.classList.remove("hidden");
            processingCard.classList.add("hidden");
            alert(`Error: ${error.message}`);
        }
    });

    // Copy Markdown to Clipboard
    copyBtn.addEventListener("click", () => {
        if (!currentSummary) return;
        navigator.clipboard.writeText(currentSummary.content).then(() => {
            showToast("Copied markdown summary to clipboard!");
        }).catch(err => {
            console.error(err);
            showToast("Failed to copy summary");
        });
    });

    // Download Markdown File
    downloadMdBtn.addEventListener("click", () => {
        if (!currentSummary) return;
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

    // Initial load
    loadHistory();
});

// String trim polyfill for older setups if necessary
if (!String.prototype.strip) {
    String.prototype.strip = function() {
        return this.trim();
    };
}
