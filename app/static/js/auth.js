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
        if (res.status === 429) return "rate_limited";
        if (!res.ok) return false;
        const data = await res.json();
        this.isAdmin = data.is_admin === true;
        return true;
    },

    init() {
        const form = document.getElementById("pin-form");
        const input = document.getElementById("pin-input");
        const error = document.getElementById("pin-error");
        const submitBtn = form.querySelector('button[type="submit"]');
        let lastAttempt = 0;

        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            error.classList.add("hidden");
            const pin = input.value.trim();
            if (!pin) return;

            const now = Date.now();
            if (now - lastAttempt < 1000) return;
            lastAttempt = now;

            if (submitBtn) submitBtn.disabled = true;
            setTimeout(() => { if (submitBtn) submitBtn.disabled = false; }, 1000);

            const result = await this.verifyPin(pin);
            if (result === true) {
                App.showApp();
            } else {
                error.textContent = result === "rate_limited"
                    ? "Too many attempts, slow down."
                    : "Incorrect PIN";
                error.classList.remove("hidden");
                input.value = "";
                input.focus();
            }
        });
    },
};
