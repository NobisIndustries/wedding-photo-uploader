const Upload = {
    // Ordered queue of all uploads in this session batch.
    // Each entry: { id, file, status, progress: 0..100, tusUpload }
    // status ∈ "queued" | "active" | "done" | "error"
    //
    // We cap actual parallelism at MAX_CONCURRENT tus uploads (helps on mobile
    // connections and keeps server memory bounded), and render only the first
    // MAX_VISIBLE entries as progress bars. With MAX_VISIBLE === MAX_CONCURRENT
    // the visible rows always correspond to the files currently uploading, and
    // everything else shows as a "+N more queued" pill.
    MAX_VISIBLE: 3,
    MAX_CONCURRENT: 3,
    queue: [],

    init() {
        const fileInput = document.getElementById("file-input");
        fileInput.addEventListener("change", (e) => {
            const files = Array.from(e.target.files);
            if (files.length === 0) return;
            files.forEach((file) => this.startUpload(file));
            fileInput.value = "";
        });

        // Warn before navigating away if uploads are still in flight. Browsers
        // won't let us hold onto File handles across navigations, so the best
        // we can do is nag the user to stay. For files that *were* actively
        // uploading, tus-js-client persists the upload URL in localStorage
        // (urlStorage + storeFingerprintForResuming below) so if the user
        // later re-picks the same file, the upload resumes from where it
        // stopped on the server. Queued-but-not-started files have no server
        // state yet and must be re-picked from scratch.
        window.addEventListener("beforeunload", (e) => {
            const unfinished = this.queue.some(
                (entry) => entry.status === "queued" || entry.status === "active"
            );
            if (unfinished) {
                e.preventDefault();
                e.returnValue = "";
                return "";
            }
        });
    },

    startUpload(file) {
        const itemId = "upload-" + Date.now() + "-" + Math.random().toString(36).slice(2, 6);
        const officialCheckbox = document.getElementById("official-checkbox");
        const entry = {
            id: itemId,
            file,
            status: "queued",
            progress: 0,
            tusUpload: null,
            official: Auth.isAdmin && officialCheckbox && officialCheckbox.checked,
        };
        this.queue.push(entry);
        this._render();
        this._pumpQueue();
    },

    _activeCount() {
        return this.queue.filter((e) => e.status === "active").length;
    },

    _pumpQueue() {
        // Promote queued entries to active until MAX_CONCURRENT is reached.
        for (const entry of this.queue) {
            if (this._activeCount() >= this.MAX_CONCURRENT) break;
            if (entry.status === "queued") this._beginUpload(entry);
        }
    },

    _beginUpload(entry) {
        entry.status = "active";

        const upload = new tus.Upload(entry.file, {
            endpoint: "/api/uploads/files/",
            retryDelays: [0, 1000, 3000, 5000, 10000],
            chunkSize: 5 * 1024 * 1024,
            // tus-js-client stores upload URLs in localStorage by default,
            // keyed by a fingerprint of the File (name + size + lastModified).
            // If the user navigates away mid-upload and later re-picks the
            // same file, tus-js-client finds the stored URL and resumes from
            // the server-side offset instead of restarting. We only need to
            // opt into cleanup on success so localStorage doesn't grow
            // unbounded across a long wedding.
            removeFingerprintOnSuccess: true,
            metadata: {
                filename: entry.file.name,
                filetype: entry.file.type || "application/octet-stream",
                official: entry.official ? "1" : "0",
            },
            onProgress: (bytesUploaded, bytesTotal) => {
                entry.progress = (bytesUploaded / bytesTotal) * 100;
                this._updateItemProgress(entry);
            },
            onSuccess: () => {
                entry.status = "done";
                entry.progress = 100;
                this._updateItemProgress(entry);
                this._scheduleRemoval(entry);
                this._pumpQueue();
                // Refresh immediately — Gallery polls thumbnail-status for any
                // items whose thumbnail isn't ready yet.
                Gallery.refresh();
            },
            onError: (error) => {
                entry.status = "error";
                this._updateItemProgress(entry);
                console.error("Upload failed:", error);
                // Don't auto-remove — keep visible so user can retry
                this._pumpQueue();
            },
        });

        entry.tusUpload = upload;
        this._render();
        upload.start();
    },

    retryUpload(entryId) {
        const entry = this.queue.find((e) => e.id === entryId);
        if (!entry || entry.status !== "error") return;
        entry.status = "queued";
        entry.progress = 0;
        this._render();
        this._pumpQueue();
    },

    dismissUpload(entryId) {
        const idx = this.queue.findIndex((e) => e.id === entryId);
        if (idx !== -1) this.queue.splice(idx, 1);
        this._render();
    },

    _visibleEntries() {
        // Show the first MAX_VISIBLE entries that are still active OR that are
        // in their post-completion "fading" state (so the user sees the 100%
        // bar briefly before it disappears). Errors stay visible too.
        return this.queue.slice(0, this.MAX_VISIBLE);
    },

    _hiddenPendingCount() {
        // Count queued-or-active items beyond the visible window.
        return this.queue
            .slice(this.MAX_VISIBLE)
            .filter((e) => e.status === "queued" || e.status === "active").length;
    },

    _render() {
        const container = document.getElementById("upload-progress");

        if (this.queue.length === 0) {
            container.innerHTML = "";
            container.classList.add("hidden");
            return;
        }

        container.classList.remove("hidden");

        const visible = this._visibleEntries();
        const visibleIds = new Set(visible.map((e) => e.id));

        // Remove DOM nodes for items no longer visible.
        container.querySelectorAll(".upload-item").forEach((el) => {
            if (!visibleIds.has(el.id)) el.remove();
        });

        // Insert/update visible items in order.
        visible.forEach((entry, idx) => {
            let el = document.getElementById(entry.id);
            if (!el) {
                el = document.createElement("div");
                el.className = "upload-item";
                el.id = entry.id;
                el.innerHTML = `
                    <span class="upload-item-name">${this._escapeHtml(entry.file.name)}</span>
                    <div class="progress-bar-container">
                        <div class="progress-bar"></div>
                    </div>
                    <span class="upload-item-status">0%</span>
                `;
            }
            // Ensure DOM order matches queue order (handles the case where a
            // later-queued item becomes visible when earlier ones disappear).
            const expectedChild = container.children[idx];
            if (expectedChild !== el) {
                container.insertBefore(el, expectedChild || null);
            }
            this._updateItemProgress(entry);
        });

        // "+N more queued" pill.
        let more = container.querySelector(".upload-more");
        const hiddenCount = this._hiddenPendingCount();
        if (hiddenCount > 0) {
            if (!more) {
                more = document.createElement("div");
                more.className = "upload-more";
                container.appendChild(more);
            } else if (more.parentNode !== container || more !== container.lastChild) {
                container.appendChild(more);
            }
            more.textContent = `+${hiddenCount} more queued…`;
        } else if (more) {
            more.remove();
        }
    },

    _updateItemProgress(entry) {
        const el = document.getElementById(entry.id);
        if (!el) return;
        const bar = el.querySelector(".progress-bar");
        const status = el.querySelector(".upload-item-status");
        if (!bar || !status) return;

        const pct = Math.round(entry.progress);
        bar.style.width = pct + "%";

        if (entry.status === "done") {
            bar.classList.add("complete");
            bar.classList.remove("error");
            status.textContent = "Done";
            // Remove retry actions if present
            const actions = el.querySelector(".upload-error-actions");
            if (actions) actions.remove();
        } else if (entry.status === "error") {
            bar.classList.add("error");
            bar.classList.remove("complete");
            status.textContent = "Failed";
            // Add retry + dismiss buttons if not already present
            if (!el.querySelector(".upload-error-actions")) {
                const actions = document.createElement("span");
                actions.className = "upload-error-actions";
                actions.innerHTML =
                    `<button class="upload-retry-btn" onclick="Upload.retryUpload('${entry.id}')">Retry</button>` +
                    `<button class="upload-dismiss-btn" onclick="Upload.dismissUpload('${entry.id}')">&times;</button>`;
                el.appendChild(actions);
            }
        } else if (entry.status === "queued") {
            status.textContent = "Waiting…";
            const actions = el.querySelector(".upload-error-actions");
            if (actions) actions.remove();
        } else {
            status.textContent = pct + "%";
        }
    },

    _scheduleRemoval(entry) {
        setTimeout(() => {
            const idx = this.queue.indexOf(entry);
            if (idx !== -1) this.queue.splice(idx, 1);
            this._render();
        }, 1500);
    },

    _escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    },
};
