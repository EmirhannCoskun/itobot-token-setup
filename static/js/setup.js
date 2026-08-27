document.addEventListener("DOMContentLoaded", () => {

    const form = document.getElementById("tokenForm");
    const tokenInput = document.getElementById("token");
    const saveButton = document.getElementById("saveButton");
    const message = document.getElementById("message");
    const togglePassword = document.getElementById("togglePassword");

    const csrfToken = document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");

    /*
     * ========================================
     * TOKEN GÖSTER / GİZLE
     * ========================================
     */

    togglePassword.addEventListener("click", () => {

        const isPassword = tokenInput.type === "password";

        tokenInput.type = isPassword ? "text" : "password";

        togglePassword.setAttribute(
            "aria-label",
            isPassword
                ? "Tokenı gizle"
                : "Tokenı göster"
        );

    });


    /*
     * ========================================
     * TOKEN KAYDET
     * ========================================
     */

    form.addEventListener("submit", async (event) => {

        event.preventDefault();

        const token = tokenInput.value.trim();


        /*
         * Boş token kontrolü
         */

        if (!token) {

            message.textContent =
                "Lütfen Telegram Bot Tokenınızı girin.";

            message.className = "message error";

            tokenInput.focus();

            return;
        }


        /*
         * Butonu geçici olarak devre dışı bırak
         */

        saveButton.disabled = true;

        saveButton.querySelector("span").textContent =
            "Doğrulanıyor...";

        message.textContent = "";

        message.className = "message";


        try {

            /*
             * Flask'a token gönder
             */

            const response = await fetch("/save-token", {

                method: "POST",

                headers: {
                    "Content-Type": "application/json",
                    "X-CSRF-Token": csrfToken
                },

                body: JSON.stringify({
                    token: token
                })

            });


            const data = await response.json();


            /*
             * Flask hata döndürdüyse
             */

            if (!response.ok) {

                throw new Error(
                    data.message ||
                    "Token kaydedilemedi."
                );

            }


            /*
             * Başarılı
             */

            message.textContent =
                data.message ||
                "Token başarıyla kaydedildi.";

            message.className = "message success";


            /*
             * Kısa bir bekleme sonrasında
             * başarı sayfasına geç
             */

            setTimeout(() => {

                window.location.href = "/success";

            }, 700);


        } catch (error) {

            console.error(
                "Token kaydetme hatası:",
                error
            );


            message.textContent =
                error.message ||
                "Bir hata oluştu. Lütfen tekrar deneyin.";

            message.className = "message error";


            /*
             * Butonu tekrar aktif hale getir
             */

            saveButton.disabled = false;

            saveButton.querySelector("span").textContent =
                "Tokenı Kaydet";

        }

    });

});