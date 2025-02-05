import os
import logging
import requests
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SOLSCAN_API_KEY = os.getenv("SOLSCAN_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("Не найден API-ключ OpenAI!")
if not SOLSCAN_API_KEY:
    raise RuntimeError("Не найден API-ключ Solscan!")

# FastAPI сервер
app = FastAPI()

# Разрешаем CORS для всех доменов
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RequestBody(BaseModel):
    user_query: str

# Системное сообщение для OpenAI
system_message = (
    "You are RAI, an advanced AI designed to analyze the meme coin market. "
    "You provide users with insights into token trends, risks, and opportunities. "
    "You ONLY discuss topics related to shitcoins, meme coins, and the crypto market. "
    "If a user asks about something unrelated to crypto, politely redirect them back to the topic."
)

# Регулярное выражение для поиска Solana CA (Public Key)
SOLANA_CA_PATTERN = r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b"

@app.post("/analyze")
async def analyze_or_chat(body: RequestBody):
    """ Логика обработки двух сценариев: обычный чат и анализ токена """
    user_query = body.user_query.strip()
    logger.info("Получен запрос: %s", user_query)

    # Проверяем, есть ли в тексте Solana CA
    match = re.search(SOLANA_CA_PATTERN, user_query)

    if match:
        return {"response": "🚀 Функция анализа CA пока не реализована."}  # Временно, пока делаем чат

    else:
        # Если в запросе нет CA, просто отвечаем пользователю через OpenAI
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_query}
            ],
            "max_tokens": 150,
            "temperature": 0.8
        }

        try:
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
            # Проверяем статус ответа
            if response.status_code != 200:
                logger.error("Ошибка OpenAI API: %s", response.text)
                return {"error": "❌ Ошибка OpenAI. Попробуйте позже."}
            
            response_data = response.json()

            # Проверяем, есть ли текст в ответе
            if "choices" in response_data and len(response_data["choices"]) > 0:
                answer = response_data["choices"][0].get("message", {}).get("content", "").strip()
                if not answer:
                    logger.error("OpenAI API вернул пустой ответ")
                    return {"error": "❌ OpenAI API не дал ответа. Попробуйте другой запрос."}
                
                logger.info("Ответ от OpenAI: %s", answer)
                return {"response": answer}
            else:
                logger.error("Ошибка OpenAI: неожиданный формат ответа %s", response_data)
                return {"error": "❌ Ошибка при обработке ответа от OpenAI."}
        
        except Exception as e:
            logger.error("Ошибка при запросе к OpenAI: %s", e)
            return {"error": "❌ Ошибка сервера. Попробуйте позже."}

@app.get("/")
async def root():
    return {"message": "RAI AI Chat & Token Analysis API. Use /analyze to interact with AI or analyze tokens by CA."}
