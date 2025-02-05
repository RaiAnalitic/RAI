<div id="displaywrap">
    <!-- Здесь будут отображаться сообщения -->
</div>

<script>
async function handleSend() {
    const messageInput = document.getElementById("message");
    const message = messageInput?.value.trim();
    const username = localStorage.getItem("username");

    if (message && username) {
        displayMessage(username, message);

        // Показать индикатор загрузки
        displayMessage("RAI", "🔄 Анализирую... Подождите.", true);

        try {
            const response = await fetch("https://raigpt-production.up.railway.app/analyze", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ token_name: "RAI", user_query: message }),
            });

            if (!response.ok) {
                throw new Error(`Ошибка сервера: ${response.status}`);
            }

            const data = await response.json();

            // Удаляем индикатор загрузки перед добавлением ответа
            removeLastRAIMessage();
            displayMessage("RAI", data.analysis, true);
        } catch (err) {
            console.error("Ошибка при отправке запроса:", err);
            removeLastRAIMessage();
            displayMessage("RAI", "❌ Ошибка при анализе. Попробуйте позже.", true);
        }

        messageInput.value = ""; // Очищаем поле ввода
    }
}

// Функция для отображения сообщений в чате
function displayMessage(username, message, isAI = false) {
    const displaywrap = document.getElementById("displaywrap");
    if (displaywrap) {
        const messageContainer = document.createElement("div");
        messageContainer.classList.add("message-container");
        messageContainer.setAttribute("data-ai", isAI ? "true" : "false"); // Добавляем атрибут

        const nickname = document.createElement("span");
        nickname.textContent = `${username}: `;
        nickname.classList.add("nickname");
        nickname.style.color = isAI ? "#ff4500" : "#08ff00";
        nickname.style.fontFamily = "'Arturito', sans-serif";

        const messageText = document.createElement("span");
        messageText.textContent = message;
        messageText.classList.add("message-text");
        messageText.style.fontFamily = "'Arturito', sans-serif";

        messageContainer.appendChild(nickname);
        messageContainer.appendChild(messageText);
        displaywrap.appendChild(messageContainer);

        displaywrap.scrollTop = displaywrap.scrollHeight; // Автопрокрутка
    }
}

// Функция удаления последнего сообщения RAI (например, индикатора загрузки)
function removeLastRAIMessage() {
    const displaywrap = document.getElementById("displaywrap");
    if (displaywrap) {
        const messages = displaywrap.querySelectorAll('.message-container[data-ai="true"]');
        if (messages.length > 0) {
            displaywrap.removeChild(messages[messages.length - 1]);
        }
    }
}

// Обработчик кнопки "Send"
document.addEventListener("DOMContentLoaded", () => {
    const sendButton = document.getElementById("sendMessage");
    const messageInput = document.getElementById("message");

    sendButton?.addEventListener("click", handleSend);
    messageInput?.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            handleSend();
        }
    });
});
</script>

<style>
    /* Контейнер чата */
    #displaywrap {
        max-height: 400px; /* Ограничение высоты для появления скроллбара */
        overflow-y: auto; /* Включаем вертикальную прокрутку */
        background: transparent; /* Прозрачный фон */
        padding: 0px;
        border-radius: 8px; /* Закруглённые углы */
    }

    /* Стилизация скроллбара */
    #displaywrap::-webkit-scrollbar {
        width: 6px; /* Тонкий скроллбар */
    }

    #displaywrap::-webkit-scrollbar-track {
        background: transparent; /* Прозрачный фон трека */
    }

    #displaywrap::-webkit-scrollbar-thumb {
        background: #08ff00; /* Зелёный цвет ползунка */
        border-radius: 3px; /* Закруглённые края */
    }

    /* Стилизация скроллбара для Firefox */
    #displaywrap {
        scrollbar-width: thin;
        scrollbar-color: #08ff00 transparent;
    }

    /* Общий контейнер сообщения */
    .message-container {
        display: block; /* Блок для разделения сообщений */
        margin-bottom: 12px; /* Отступ между сообщениями */
        word-wrap: break-word;
        overflow-wrap: break-word;
    }

    /* Никнейм */
    .nickname {
        font-weight: bold; /* Жирный текст */
        white-space: nowrap; /* Никнеймы не переносятся */
    }

    /* Текст сообщения */
    .message-text {
        display: inline; /* Сообщение остаётся на одной строке с никнеймом */
        word-wrap: break-word;
        overflow-wrap: break-word;
        white-space: normal; /* Позволяем перенос текста */
    }
</style>
