import os
import logging
import requests
import re
import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Logging
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

# FastAPI server
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RequestBody(BaseModel):
    user_query: str

SOLANA_CA_PATTERN = r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b"

def format_number(value):
    """ Formats numbers into a readable format (K, M, B, T) """
    if value >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}T"
    elif value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.2f}K"
    return str(value)

def format_timestamp(timestamp):
    """ Converts Unix Timestamp to a readable UTC time format """
    try:
        return datetime.datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        return "Unknown"

def get_token_info(ca):
    """ Retrieves token information """
    logger.info(f"🔍 Requesting token information: {ca}")

    url = f"https://pro-api.solscan.io/v2.0/token/meta?address={ca}"
    headers = {"accept": "application/json", "Content-Type": "application/json", "token": SOLSCAN_API_KEY}

    try:
        response = requests.get(url, headers=headers)
        logger.info(f"🔄 Response status (meta): {response.status_code}")

        if response.status_code == 200:
            data = response.json().get("data", {})
            if data:
                total_supply = int(data.get("supply", 0))  # Clean number
                market_cap = float(data.get("market_cap", 0))  # Convert Market Cap to float

                token_info = {
                    "token_name": data.get("name", "Unknown"),
                    "token_symbol": data.get("symbol", "Unknown"),
                    "icon_url": data.get("icon", ""),
                    "total_supply": format_number(total_supply),  # Format for readability
                    "holders_count": data.get("holder", 0),
                    "creator": data.get("creator", "Unknown"),
                    "created_time": format_timestamp(data.get("created_time", 0)),
                    "first_mint_tx": data.get("first_mint_tx", "Unknown"),
                    "market_cap": format_number(market_cap),  # Format Market Cap
                    "description": data.get("metadata", {}).get("description", ""),
                    "website": data.get("metadata", {}).get("website", ""),
                    "twitter": data.get("metadata", {}).get("twitter", "")
                }
                logger.info(f"✅ Token information retrieved: {token_info}")
                return token_info, total_supply  # Return total_supply separately for calculations

        logger.warning("⚠️ No token information available.")
        return {"error": "⚠️ No token information available."}, 0

    except requests.RequestException as e:
        logger.error(f"❌ Error when requesting Solscan API: {e}")
        return {"error": "❌ Connection error with Solscan API."}, 0

def get_supply_percentage(ca, total_supply):
    """ Calculates the percentage of supply bought in the first 20 transactions """
    logger.info(f"🔍 Analyzing supply percentage bought in the first 20 transactions: {ca}")

    url = (
        f"https://pro-api.solscan.io/v2.0/token/transfer?"
        f"address={ca}"
        f"&activity_type[]=ACTIVITY_SPL_TRANSFER"
        f"&page=1&page_size=20&sort_by=block_time&sort_order=asc"
    )

    headers = {"accept": "application/json", "Content-Type": "application/json", "token": SOLSCAN_API_KEY}

    try:
        response = requests.get(url, headers=headers)
        logger.info(f"🔄 Solscan response status: {response.status_code}")

        if response.status_code != 200:
            logger.error(f"❌ Solscan API error: {response.text}")
            return {"error": "❌ Error when requesting Solscan API."}

        data = response.json().get("data", [])
        if not data:
            logger.warning("⚠️ No data available for the first transactions.")
            return {"error": "⚠️ No data available for the first transactions of the token."}

        total_bought = sum(tx["amount"] for tx in data)
        supply_percentage = (total_bought / total_supply) * 100 if total_supply > 0 else 0

        logger.info(f"✅ {supply_percentage:.2f}% of the total supply was bought in the first 20 transactions")
        return round(supply_percentage, 2)

    except requests.RequestException as e:
        logger.error(f"❌ Error when requesting Solscan API: {e}")
        return {"error": "❌ Connection error with Solscan API."}

@app.post("/analyze")
async def analyze_or_chat(body: RequestBody):
    """ Logic for handling two scenarios: regular chat and token analysis """
    user_query = body.user_query.strip()
    logger.info("📩 Received request: %s", user_query)

    match = re.search(SOLANA_CA_PATTERN, user_query)

    if match:
        ca = match.group(0)
        logger.info(f"📍 Contract address found: {ca}")

        token_info, total_supply = get_token_info(ca)
        if "error" in token_info:
            return token_info

        supply_percentage = get_supply_percentage(ca, total_supply)

        return {
            "contract_address": ca,
            "token_info": token_info,
            "first_20_transactions_supply_percentage": supply_percentage
        }

    else:
        return {"response": "❌ The request does not contain a valid token CA."}

@app.get("/")
async def root():
    return {"message": "RAI AI Chat & Token Analysis API. Use /analyze to interact with AI or analyze tokens by CA."}
