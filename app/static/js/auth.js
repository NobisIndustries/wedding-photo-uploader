const Auth = {
    isAdmin: false,

    async checkStatus() {
        try {
            const res = await fetch("/api/auth/status");
            const data = await res.json();
            this.isAdmin = data.is_admin === true;
            return data.authenticated === true;
        } catch {
            this.isAdmin = false;
            return false;
        }
    },

    async verifyPin(pin) {
        const res = await fetch("/api/auth/verify-pin", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ pin }),
        });
        if (!res.ok) return false;
        const data = await res.json();
        this.isAdmin = data.is_admin === true;
        return true;
    },

    init() {
        const form = document.getElementById("pin-form");
        const input = document.getElementById("pin-input");
        const error = document.getElementById("pin-error");

        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            error.classList.add("hidden");
            const pin = input.value.trim();
            if (!pin) return;

            const ok = await this.verifyPin(pin);
            if (ok) {
                App.showApp();
            } else {
                error.classList.remove("hidden");
                input.value = "";
                input.focus();
            }
        });
    },
};
