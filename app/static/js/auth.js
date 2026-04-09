const Auth = {
    async checkStatus() {
        try {
            const res = await fetch("/api/auth/status");
            const data = await res.json();
            return data.authenticated === true;
        } catch {
            return false;
        }
    },

    async verifyPin(pin) {
        const res = await fetch("/api/auth/verify-pin", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ pin }),
        });
        return res.ok;
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
