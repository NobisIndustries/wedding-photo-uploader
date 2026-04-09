const Gallery = {
    currentPage: 1,
    perPage: 50,
    total: 0,
    items: [],
    lightboxIndex: -1,

    async refresh() {
        this.currentPage = 1;
        this.items = [];
        await this.loadPage(1);
    },

    async loadPage(page) {
        try {
            const res = await fetch(`/api/gallery?page=${page}&per_page=${this.perPage}`);
            if (res.status === 401) {
                App.showAuth();
                return;
            }
            const data = await res.json();
            this.total = data.total;
            this.currentPage = page;

            if (page === 1) {
                this.items = data.items;
            } else {
                this.items = this.items.concat(data.items);
            }

            this.render();
        } catch (e) {
            console.error("Failed to load gallery:", e);
        }
    },

    render() {
        const gallery = document.getElementById("gallery");
        const emptyState = document.getElementById("empty-state");
        const loadMore = document.getElementById("load-more");

        // Clear gallery items but keep empty state element
        gallery.querySelectorAll(".gallery-item").forEach((el) => el.remove());

        if (this.items.length === 0) {
            emptyState.classList.remove("hidden");
            loadMore.classList.add("hidden");
            return;
        }

        emptyState.classList.add("hidden");

        this.items.forEach((item) => {
            const el = document.createElement("div");
            el.className = "gallery-item";
            el.dataset.id = item.id;

            const isVideo = item.mime_type.startsWith("video/");

            el.innerHTML = `
                <img src="${item.thumbnail_url}" alt="${this._escapeHtml(item.original_filename)}"
                     loading="lazy" onerror="this.style.display='none'">
                ${isVideo ? '<span class="video-badge">&#9654; Video</span>' : ""}
                ${item.is_owner ? '<button class="delete-btn" title="Delete">&times;</button>' : ""}
            `;

            el.addEventListener("click", (e) => {
                if (e.target.classList.contains("delete-btn")) {
                    e.stopPropagation();
                    this.deleteItem(item.id);
                    return;
                }
                this.openLightbox(item);
            });

            gallery.appendChild(el);
        });

        // Show load more if there are more items
        const loaded = this.items.length;
        if (loaded < this.total) {
            loadMore.classList.remove("hidden");
        } else {
            loadMore.classList.add("hidden");
        }
    },

    async deleteItem(id) {
        if (!confirm("Delete this file?")) return;

        try {
            const res = await fetch(`/api/files/${id}`, { method: "DELETE" });
            if (res.ok) {
                this.items = this.items.filter((i) => i.id !== id);
                this.total--;
                this.render();
            } else {
                const data = await res.json();
                alert(data.detail || "Delete failed");
            }
        } catch (e) {
            console.error("Delete failed:", e);
        }
    },

    openLightbox(item) {
        this.lightboxIndex = this.items.findIndex((i) => i.id === item.id);
        this._renderLightbox();
        document.getElementById("lightbox").classList.remove("hidden");
    },

    _renderLightbox() {
        const item = this.items[this.lightboxIndex];
        if (!item) return;

        const content = document.getElementById("lightbox-content");
        const video = content.querySelector("video");
        if (video) video.pause();

        const isVideo = item.mime_type.startsWith("video/");
        if (isVideo) {
            content.innerHTML = `<video src="${item.file_url}" controls playsinline autoplay></video>`;
        } else {
            content.innerHTML = `<img src="${item.file_url}" alt="${this._escapeHtml(item.original_filename)}">`;
        }

        const prev = document.getElementById("lightbox-prev");
        const next = document.getElementById("lightbox-next");
        prev.classList.toggle("hidden", this.lightboxIndex <= 0);
        next.classList.toggle("hidden", this.lightboxIndex >= this.items.length - 1);
    },

    navigateLightbox(delta) {
        const newIndex = this.lightboxIndex + delta;
        if (newIndex < 0 || newIndex >= this.items.length) return;
        this.lightboxIndex = newIndex;
        this._renderLightbox();
    },

    closeLightbox() {
        const lightbox = document.getElementById("lightbox");
        const content = document.getElementById("lightbox-content");
        const video = content.querySelector("video");
        if (video) video.pause();
        content.innerHTML = "";
        lightbox.classList.add("hidden");
        this.lightboxIndex = -1;
    },

    init() {
        document.getElementById("lightbox-close").addEventListener("click", () => this.closeLightbox());
        document.getElementById("lightbox-prev").addEventListener("click", () => this.navigateLightbox(-1));
        document.getElementById("lightbox-next").addEventListener("click", () => this.navigateLightbox(1));
        document.getElementById("lightbox").addEventListener("click", (e) => {
            if (e.target.id === "lightbox" || e.target.classList.contains("lightbox-content")) {
                this.closeLightbox();
            }
        });
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") this.closeLightbox();
            if (e.key === "ArrowLeft") this.navigateLightbox(-1);
            if (e.key === "ArrowRight") this.navigateLightbox(1);
        });

        document.getElementById("load-more-btn").addEventListener("click", () => {
            this.loadPage(this.currentPage + 1);
        });
    },

    _escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    },
};
