const Upload = {
    activeUploads: 0,

    init() {
        const fileInput = document.getElementById("file-input");
        fileInput.addEventListener("change", (e) => {
            const files = Array.from(e.target.files);
            if (files.length === 0) return;
            files.forEach((file) => this.startUpload(file));
            fileInput.value = "";
        });
    },

    startUpload(file) {
        this.activeUploads++;
        const container = document.getElementById("upload-progress");
        container.classList.remove("hidden");

        const itemId = "upload-" + Date.now() + "-" + Math.random().toString(36).slice(2, 6);
        const item = document.createElement("div");
        item.className = "upload-item";
        item.id = itemId;
        item.innerHTML = `
            <span class="upload-item-name">${this._escapeHtml(file.name)}</span>
            <div class="progress-bar-container">
                <div class="progress-bar" id="${itemId}-bar"></div>
            </div>
            <span class="upload-item-status" id="${itemId}-status">0%</span>
        `;
        container.appendChild(item);

        const upload = new tus.Upload(file, {
            endpoint: "/api/uploads/files/",
            retryDelays: [0, 1000, 3000, 5000, 10000],
            chunkSize: 5 * 1024 * 1024,
            metadata: {
                filename: file.name,
                filetype: file.type || "application/octet-stream",
            },
            onProgress: (bytesUploaded, bytesTotal) => {
                const pct = ((bytesUploaded / bytesTotal) * 100).toFixed(0);
                const bar = document.getElementById(`${itemId}-bar`);
                const status = document.getElementById(`${itemId}-status`);
                if (bar) bar.style.width = pct + "%";
                if (status) status.textContent = pct + "%";
            },
            onSuccess: () => {
                const bar = document.getElementById(`${itemId}-bar`);
                const status = document.getElementById(`${itemId}-status`);
                if (bar) { bar.style.width = "100%"; bar.classList.add("complete"); }
                if (status) status.textContent = "Done";
                this._uploadFinished(itemId);
                // Delay refresh to give server time to generate thumbnail
                setTimeout(() => Gallery.refresh(), 1500);
            },
            onError: (error) => {
                const bar = document.getElementById(`${itemId}-bar`);
                const status = document.getElementById(`${itemId}-status`);
                if (bar) bar.classList.add("error");
                if (status) status.textContent = "Failed";
                console.error("Upload failed:", error);
                this._uploadFinished(itemId);
            },
        });

        upload.start();
    },

    _uploadFinished(itemId) {
        this.activeUploads--;
        // Remove the progress item after a delay
        setTimeout(() => {
            const item = document.getElementById(itemId);
            if (item) item.remove();
            if (this.activeUploads <= 0) {
                const container = document.getElementById("upload-progress");
                if (container.children.length === 0) {
                    container.classList.add("hidden");
                }
                this.activeUploads = 0;
            }
        }, 2000);
    },

    _escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    },
};
