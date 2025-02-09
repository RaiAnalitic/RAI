import os
import logging
import requests
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SOLSCAN_API_KEY = os.getenv("SOLSCAN_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OpenAI API key not found!")
if not SOLSCAN_API_KEY:
    raise RuntimeError("Solscan API key not found!")

# Initialize FastAPI server
app = FastAPI()

# Enable CORS for all domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RequestBody(BaseModel):
    user_query: str

# System message for OpenAI
system_message = (
    "You are RAI, an advanced AI designed to analyze the meme coin market. "
    "You provide users with insights into token trends, risks, and opportunities. "
    "You ONLY discuss topics related to shitcoins, meme coins, and the crypto market. "
    "If a user asks about something unrelated to crypto, politely redirect them back to the topic."
)

# Regular expression pattern to detect Solana CA (Public Key)
SOLANA_CA_PATTERN = r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b"

def get_token_info(ca):
    """ Fetches token name, icon, total supply, and additional information. """
    logger.info(f"🔍 Requesting token data: {ca}")

    url = f"https://pro-api.solscan.io/v2.0/token/meta?address={ca}"

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "token": SOLSCAN_API_KEY
    }

    try:
        response = requests.get(url, headers=headers)
        logger.info(f"🔄 Solscan response status (meta): {response.status_code}")

        if response.status_code == 200:
            data = response.json().get("data", {})
            if data:
                token_info = {
                    "token_name": data.get("name", "Unknown"),
                    "token_symbol": data.get("symbol", "Unknown"),
                    "icon_url": data.get("icon", ""),
                    "total_supply": data.get("supply", "Unknown"),
                    "holders_count": data.get("holder", 0),
                    "creator": data.get("creator", "Unknown"),
                    "created_time": data.get("created_time", 0),
                    "first_mint_tx": data.get("first_mint_tx", "Unknown"),
                    "market_cap": data.get("market_cap", "Unknown"),
                    "description": data.get("metadata", {}).get("description", ""),
                    "website": data.get("metadata", {}).get("website", ""),
                    "twitter": data.get("metadata", {}).get("twitter", "")
                }
                logger.info(f"✅ Token information retrieved: {token_info}")
                return token_info

        logger.warning("⚠️ No token data available.")
        return {"error": "⚠️ No token data available."}

    except requests.RequestException as e:
        logger.error(f"❌ Error while querying Solscan API: {e}")
        return {"error": "❌ Connection error with Solscan API."}


def get_token_first_transfers(ca):
    """ Fetches the first 10 real token transactions (excluding minting). """
    logger.info(f"🔍 Requesting first transactions (excluding minting) for token: {ca}")

    url = (
        f"https://pro-api.solscan.io/v2.0/token/transfer?"
        f"address={ca}"
        f"&activity_type[]=ACTIVITY_SPL_TRANSFER"
        f"&page=1&page_size=10&sort_by=block_time&sort_order=asc"
    )

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "token": SOLSCAN_API_KEY
    }

    try:
        response = requests.get(url, headers=headers)
        logger.info(f"🔄 Solscan response status: {response.status_code}")

        if response.status_code != 200:
            logger.error(f"❌ Solscan API error: {response.text}")
            return {"error": "❌ Error while querying Solscan API."}

        data = response.json().get("data", [])
        if not data:
            logger.warning("⚠️ No data on first transactions.")
            return {"error": "⚠️ No data on first token transactions."}

        first_transfers = []
        for tx in data:
            first_transfers.append({
                "tx_id": tx["trans_id"],
                "time": tx["time"],
                "from": tx["from_address"],
                "to": tx["to_address"],
                "amount": tx["amount"],
                "value": tx["value"]
            })

        logger.info(f"✅ Retrieved first {len(first_transfers)} transactions for token {ca}")
        return first_transfers

    except requests.RequestException as e:
        logger.error(f"❌ Error while querying Solscan API: {e}")
        return {"error": "❌ Connection error with Solscan API."}

@app.post("/analyze")
async def analyze_or_chat(body: RequestBody):
    """ Handles two scenarios: token analysis or general AI chat """
    user_query = body.user_query.strip()
    logger.info("📩 Received request: %s", user_query)

    match = re.search(SOLANA_CA_PATTERN, user_query)

    if match:
        ca = match.group(0)
        logger.info(f"📍 Detected contract address: {ca}")

        # Retrieve token information
        token_info = get_token_info(ca)
        if "error" in token_info:
            return token_info

        # Retrieve first 10 real token transactions (excluding minting)
        first_transfers = get_token_first_transfers(ca)

        return {
            "contract_address": ca,
            "token_info": token_info,
            "first_transfers": first_transfers
        }

    else:
        # AI chat response
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

            if response.status_code != 200:
                logger.error("OpenAI API error: %s", response.text)
                return {"error": "❌ OpenAI error. Please try again later."}

            response_data = response.json()
            answer = response_data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            if not answer:
                logger.error("OpenAI API returned an empty response")
                return {"error": "❌ OpenAI API did not provide a response. Try a different query."}

            logger.info("Response from OpenAI: %s", answer)
            return {"response": answer}

        except Exception as e:
            logger.error("Error while querying OpenAI: %s", e)
            return {"error": "❌ Server error. Please try again later."}

@app.get("/")
async def root():
    return {"message": "RAI AI Chat & Token Analysis API. Use /analyze to interact with AI or analyze tokens by CA."}

