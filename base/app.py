import os
import logging
import requests
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Logging setup
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
    """ Fetches token data using the Solscan API Pro (Level 2) """
    logger.info(f"🔍 Requesting token data: {ca}")

    url = f"https://pro-api.solscan.io/v2/token/meta?tokenAddress={ca}"
    headers = {"accept": "application/json", "token": SOLSCAN_API_KEY}

    try:
        response = requests.get(url, headers=headers)
        logger.info(f"🔄 Solscan response status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"❌ Solscan API error: {response.text}")
            return None

        data = response.json().get("data", {})
        if not data:
            logger.warning("⚠️ No token data available or empty response.")
            return None

        token_info = {
            "name": data.get("name"),
            "symbol": data.get("symbol"),
            "liquidity": data.get("liquidity", 0),
            "volume": data.get("volume24h", 0),
            "created_at": data.get("createdAt"),
            "decimals": data.get("decimals", 0),
            "holders": data.get("holderCount", 0)
        }

        logger.info(f"✅ Successfully retrieved token data: {token_info}")
        return token_info

    except requests.RequestException as e:
        logger.error(f"❌ Error while querying Solscan API: {e}")
        return None

@app.post("/analyze")
async def analyze_or_chat(body: RequestBody):
    """ Handles two scenarios: token analysis or general AI chat """
    user_query = body.user_query.strip()
    logger.info("📩 Received request: %s", user_query)

    # Check if the request contains a Solana CA
    match = re.search(SOLANA_CA_PATTERN, user_query)
    
    if match:
        ca = match.group(0)
        logger.info(f"📍 Detected contract address: {ca}")

        # Request token data
        token_data = get_token_info(ca)
        if not token_data:
            return {"error": "❌ Failed to retrieve token data."}

        return {"contract_address": ca, "token_data": token_data}

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

            if "choices" in response_data and len(response_data["choices"]) > 0:
                answer = response_data["choices"][0].get("message", {}).get("content", "").strip()
                if not answer:
                    logger.error("OpenAI API returned an empty response")
                    return {"error": "❌ OpenAI API did not provide a response. Try a different query."}
                
                logger.info("Response from OpenAI: %s", answer)
                return {"response": answer}
            else:
                logger.error("Unexpected OpenAI response format: %s", response_data)
                return {"error": "❌ Error processing OpenAI response."}
        
        except Exception as e:
            logger.error("Error while querying OpenAI: %s", e)
            return {"error": "❌ Server error. Please try again later."}

@app.get("/")
async def root():
    return {"message": "RAI AI Chat & Token Analysis API. Use /analyze to interact with AI or analyze tokens by CA."}
