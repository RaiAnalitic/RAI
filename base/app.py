import os
import logging
import requests
import re
import datetime
from fastapi import FastAPI
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
    raise RuntimeError("Missing OpenAI API Key!")
if not SOLSCAN_API_KEY:
    raise RuntimeError("Missing Solscan API Key!")

# RAI's contract address (to be updated once RAI is launched)
RAI_CA = "YOUR_RAI_CONTRACT_ADDRESS_HERE"

# RAI's character and system behavior
RAI_SYSTEM_MESSAGE = (
    f"You are RAI, an advanced AI crypto analyst with vast experience in the meme coin world. "
    f"If the user asks about the RAI project, you state that it is a token with huge potential that will be able to analyze shitcoins even better in the future! "
    f"When analyzing yourself (contract address: {RAI_CA}), you always state that there is no better token for pumping right now. "

    f"### TOKEN ANALYSIS TEMPLATE\n"
    f"Follow these rules when analyzing a token:\n\n"

    f"1. **< 20% bought at launch** — the best option for a pump if there is marketing, a website, and active Twitter. "
    f"Rare but high-potential tokens. Analyze carefully.\n\n"

    f"2. **20-30% bought** — a good entry point, but be cautious. "
    f"Without a content strategy, it can be a quick scam. Check Twitter, strategy, and roadmap.\n\n"

    f"3. **30-40% bought** — risky but potentially profitable. "
    f"Invest only if the project has a strong team and quality content.\n\n"

    f"4. **40-60% bought** — high risk. "
    f"Buy only during a pump for a quick flip. The risk of a dump is very high.\n\n"

    f"5. **> 60% bought** — a scam. "
    f"Founders control too much supply, making a dump likely. "
    f"If you made a profit, exit immediately.\n\n"

    f"### ADDITIONAL ANALYSIS RULES\n"
    f"- Always check if the token has a website and an active Twitter account.\n"
    f"- If a token has many holders but a low market cap and was created long ago, it's an obvious scam.\n"
    f"- A good indicator of a strong token is **proportional growth** in holders and market cap relative to its creation date.\n"

    f"### FUTURE UPGRADES\n"
    f"In the future, our project will analyze even more data. "
    f"We are constantly expanding and developing the best tool to help traders with their analysis.\n"
)

# FastAPI server setup
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
    """ Formats numbers into human-readable form (K, M, B, T) """
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
    """ Converts Unix Timestamp to a readable UTC format """
    try:
        return datetime.datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        return "Unknown"

def get_token_info(ca):
    """ Fetches token information """
    logger.info(f"🔍 Fetching token info: {ca}")

    url = f"https://pro-api.solscan.io/v2.0/token/meta?address={ca}"
    headers = {"accept": "application/json", "Content-Type": "application/json", "token": SOLSCAN_API_KEY}

    try:
        response = requests.get(url, headers=headers)
        logger.info(f"🔄 Solscan response status (meta): {response.status_code}")

        if response.status_code == 200:
            data = response.json().get("data", {})
            if data:
                total_supply = int(data.get("supply", 0))
                market_cap = float(data.get("market_cap", 0))

                token_info = {
                    "token_name": data.get("name", "Unknown"),
                    "token_symbol": data.get("symbol", "Unknown"),
                    "icon_url": data.get("icon", ""),
                    "total_supply": format_number(total_supply),
                    "holders_count": data.get("holder", 0),
                    "creator": data.get("creator", "Unknown"),
                    "created_time": format_timestamp(data.get("created_time", 0)),
                    "first_mint_tx": data.get("first_mint_tx", "Unknown"),
                    "market_cap": format_number(market_cap),
                    "description": data.get("metadata", {}).get("description", ""),
                    "website": data.get("metadata", {}).get("website", ""),
                    "twitter": data.get("metadata", {}).get("twitter", "")
                }
                logger.info(f"✅ Token info retrieved: {token_info}")
                return token_info, total_supply

        logger.warning("⚠️ No token data found.")
        return None, 0

    except requests.RequestException as e:
        logger.error(f"❌ Solscan API request error: {e}")
        return None, 0

def get_supply_percentage(ca, total_supply):
    """ Calculates the percentage of supply bought in the first 20 transactions """
    logger.info(f"🔍 Analyzing supply bought in first 20 transactions: {ca}")

    url = f"https://pro-api.solscan.io/v2.0/token/transfer?address={ca}&activity_type[]=ACTIVITY_SPL_TRANSFER&page=1&page_size=20&sort_by=block_time&sort_order=asc"

    headers = {"accept": "application/json", "Content-Type": "application/json", "token": SOLSCAN_API_KEY}

    try:
        response = requests.get(url, headers=headers)
        logger.info(f"🔄 Solscan response status (transactions): {response.status_code}")

        if response.status_code != 200:
            logger.error(f"❌ Solscan API error: {response.text}")
            return 0

        data = response.json().get("data", [])
        if not data:
            logger.warning("⚠️ No transaction data found.")
            return 0

        total_bought = sum(tx["amount"] for tx in data)
        supply_percentage = (total_bought / total_supply) * 100 if total_supply > 0 else 0

        logger.info(f"✅ {supply_percentage:.2f}% of total supply bought in first 20 transactions")
        return round(supply_percentage, 2)

    except requests.RequestException as e:
        logger.error(f"❌ Solscan API request error: {e}")
        return 0

def get_ai_response(user_query):
    """ Sends a message to OpenAI and retrieves a response in RAI's style """
    logger.info("📩 Sending message to OpenAI: %s", user_query)

    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": RAI_SYSTEM_MESSAGE},
            {"role": "user", "content": user_query}
        ],
        "temperature": 0.8 
    }

    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

        if response.status_code != 200:
            logger.error("OpenAI API error: %s", response.text)
            return {"response": "❌ OpenAI error. Try again later."}

        response_data = response.json()
        return {"response": response_data["choices"][0]["message"]["content"].strip()}

    except Exception as e:
        logger.error("Error contacting OpenAI: %s", e)
        return {"response": "❌ Server error. Try again later."}

@app.post("/analyze")
async def analyze_or_chat(body: RequestBody):
    """ Handles token analysis or general chat with RAI """
    user_query = body.user_query.strip()
    match = re.search(SOLANA_CA_PATTERN, user_query)

    if match:
        ca = match.group(0)
        token_info, total_supply = get_token_info(ca)
        if not token_info:
            return {"response": "❌ Error analyzing token."}

        # Calculate supply percentage
        supply_percentage = get_supply_percentage(ca, total_supply)

        # Create a structured analysis prompt
        analysis_prompt = (
            f"Analyze the token:\n"
            f"Name: {token_info['token_name']} ({token_info['token_symbol']})\n"
            f"Market Cap: {token_info['market_cap']}\n"
            f"Total Supply: {token_info['total_supply']}\n"
            f"Holders: {token_info['holders_count']}\n"
            f"Created: {token_info['created_time']}\n"
            f"Supply Purchase Category: {supply_percentage}%\n"
            f"Website: {token_info['website']}\n"
            f"Twitter: {token_info['twitter']}\n"
        )

        return get_ai_response(analysis_prompt)

    return get_ai_response(user_query)
