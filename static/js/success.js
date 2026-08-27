document.addEventListener("DOMContentLoaded", () => {

    const changeTokenButton =
        document.getElementById("changeTokenButton");

    const deleteTokenButton =
        document.getElementById("deleteTokenButton");

    const changeMessage =
        document.getElementById("changeMessage");

    const csrfToken = document
        .querySelector('meta[name="csrf-token"]')
        .getAttribute("content");


    /*
     * ========================================
     * TOKEN DEĞİŞTİR
     * ========================================
     */

    if (changeTokenButton) {

        changeTokenButton.addEventListener("click", () => {

            changeTokenButton.disabled = true;

            changeTokenButton.querySelector("span").textContent =
                "Hazırlanıyor...";

            if (changeMessage) {
                changeMessage.textContent = "";
            }

            /*
             * Eski token burada silinmez.
             *
             * Yeni token başarıyla doğrulanıp kaydedilirse
             * mevcut token'ın yerine geçer.
             */

            window.location.href = "/change-token";

        });

    }


    /*
     * ========================================
     * TOKEN SİL
     * ========================================
     */

    if (deleteTokenButton) {

        deleteTokenButton.addEventListener("click", async () => {

            const confirmed = window.confirm(
                "Kayıtlı Telegram bot tokenını silmek istediğinize emin misiniz?"
            );

            if (!confirmed) {
                return;
            }


            deleteTokenButton.disabled = true;

            deleteTokenButton.querySelector("span").textContent =
                "Siliniyor...";

            if (changeMessage) {
                changeMessage.textContent = "";
                changeMessage.className = "message";
            }


            try {

                const response = await fetch("/delete-token", {

                    method: "POST",

                    headers: {
                        "X-CSRF-Token": csrfToken
                    }

                });


                const data = await response.json();


                if (!response.ok) {

                    throw new Error(
                        data.message ||
                        "Token silinemedi."
                    );

                }


                if (changeMessage) {

                    changeMessage.textContent =
                        data.message ||
                        "Token başarıyla silindi.";

                    changeMessage.className =
                        "message success";

                }


                /*
                 * Token silindikten sonra kullanıcıyı
                 * tekrar kurulum ekranına gönder.
                 */

                setTimeout(() => {

                    window.location.href = "/";

                }, 700);


            } catch (error) {

                console.error(
                    "Token silme hatası:",
                    error
                );


                if (changeMessage) {

                    changeMessage.textContent =
                        error.message ||
                        "Token silinemedi. Lütfen tekrar deneyin.";

                    changeMessage.className =
                        "message error";

                }


                deleteTokenButton.disabled = false;

                deleteTokenButton.querySelector("span").textContent =
                    "Tokenı Sil";

            }

        });

    }

});