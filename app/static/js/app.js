const App = {
    async init() {
        Auth.init();
        Upload.init();
        Gallery.init();
        this.initLogout();

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

    initLogout() {
        document.getElementById("logout-btn").addEventListener("click", (e) => {
            e.preventDefault();
            Auth.logout();
        });
    },

    applyAdminUI() {
        const officialToggle = document.getElementById("official-toggle");
        if (Auth.isAdmin) {
            officialToggle.classList.remove("hidden");
        } else {
            officialToggle.classList.add("hidden");
        }
    },
};

document.addEventListener("DOMContentLoaded", () => App.init());
