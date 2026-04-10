const App = {
    async init() {
        Auth.init();
        Upload.init();
        Gallery.init();

        const authenticated = await Auth.checkStatus();
        if (authenticated) {
            this.showApp();
        } else {
            this.showAuth();
        }
    },

    showAuth() {
        document.getElementById("auth-screen").classList.remove("hidden");
        document.getElementById("app-screen").classList.add("hidden");
        document.getElementById("pin-input").focus();
    },

    showApp() {
        document.getElementById("auth-screen").classList.add("hidden");
        document.getElementById("app-screen").classList.remove("hidden");
        this.applyAdminUI();
        Gallery.refresh();
    },

    applyAdminUI() {
        const zipBtn = document.getElementById("download-all-btn");
        if (Auth.isAdmin) {
            zipBtn.classList.remove("hidden");
        } else {
            zipBtn.classList.add("hidden");
        }
    },
};

document.addEventListener("DOMContentLoaded", () => App.init());
