import argparse
import logging
import re
import os
import asyncio
import sys
import requests
import aiohttp
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import base64
from predator_sdk import PredatorSDK
import traceback
print("Launching bot")
sys.stdout.flush()

# Base58 alphabet
BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

# Pre-compiled regex pattern to find potential base58 strings
BASE58_PATTERN = re.compile(r'[1-9A-HJ-NP-Za-km-z]{32}')
PAIR_TOKEN_PATTERN = re.compile(r'[a-zA-Z0-9]{33,64}')  # Updated pattern for pair tokens
# Argument parser setup
parser = argparse.ArgumentParser(description='Telegram Bot for Solana Swaps')
parser.add_argument('--private_key', required=True, help='Private Key for Solana Wallet')
parser.add_argument('--api_id', required=True, help='Telegram API ID')
parser.add_argument('--api_hash', required=True, help='Telegram API Hash')
parser.add_argument('--phone_number', required=True, help='Telegram Phone Number')
parser.add_argument('--amount_to_swap', required=True, type=float, help='Amount to Swap')
parser.add_argument('--chatid', required=False, default='', help='Telegram Chat ID')
parser.add_argument('--discord', required=False, help='Discord Webhook URL')
parser.add_argument('--session_string', required=False, help='Telegram Session String')

args = parser.parse_args()

api_id = args.api_id
api_hash = args.api_hash
phone_number = args.phone_number
AMOUNT_TO_SWAP = args.amount_to_swap
CHAT_ID = args.chatid
DISCORD_WEBHOOK_URL = args.discord
PRIVATE_KEY = args.private_key


# Load or create a new StringSession
session_string = args.session_string
if session_string:
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
else:
    client = TelegramClient(StringSession(), api_id, api_hash)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger('httpx').setLevel(logging.WARNING)

# Initialize PredatorSDK
sdk = PredatorSDK()

async def get_pool_info(pair_token: str):
    url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{pair_token}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                pairs = data.get("pairs", [])
                if pairs:
                    for token in pairs:
                        contract_id = token["baseToken"]["address"]
                        return contract_id
    return None

def notify_discord(result: str):
    message = {
        "content": f"Swap successful!\n {result}"
    }
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=message)
        if response.status_code == 204:
            print("Discord notification sent successfully.")
            sys.stdout.flush()
        else:
            print(f"Failed to send Discord notification. Status code: {response.status_code}")
            sys.stdout.flush()
    except Exception as e:
        print(f"Error sending Discord notification: {e}")
        sys.stdout.flush()

def is_base58(s: str) -> bool:
    return all(c in BASE58_ALPHABET for c in s)

def find_first_token_or_public_key(text: str):
    potential_keys = BASE58_PATTERN.findall(text)
    potential_pair_tokens = PAIR_TOKEN_PATTERN.findall(text)

    for token in potential_pair_tokens:
        return token, 'pair_token'
    for key in potential_keys:
        if is_base58(key):
            return key, 'public_key'

    return None, None
async def perform_swap(token_address):
    try:
        print(f"Attempting to swap {AMOUNT_TO_SWAP} for token address: {token_address}")
        sys.stdout.flush()
        
        result = await sdk.buy({
            'privateKeys': PRIVATE_KEY,
            'tokenAddress': token_address,
            'amount': str(AMOUNT_TO_SWAP),
        })
        
        print('Swap successful:', result)
        sys.stdout.flush()
        
        notify_discord(result)
    except Exception as error:
        print(f'Swap operation failed. Error details:')
        print(f'Error type: {type(error).__name__}')
        print(f'Error message: {str(error)}')
        print('Traceback:')
        traceback.print_exc()
        sys.stdout.flush()
        
        # Optionally, you can notify about the failed swap
        if DISCORD_WEBHOOK_URL:
            notify_discord_error(str(error))
async def process_message(event):
    message_text = event.message.text
    token, token_type = find_first_token_or_public_key(message_text)

    if token:
        if token_type == 'public_key':
            print(f'Found quote mint: {token}')
            sys.stdout.flush()
            await perform_swap(token)
        elif token_type == 'pair_token':
            print(f'Found pair token: {token}')
            sys.stdout.flush()
            quote_mint = await get_pool_info(token)
            if quote_mint:
                print(f'Found quote mint: {quote_mint}')
                sys.stdout.flush()
                await perform_swap(quote_mint)
            else:
                sys.stdout.flush()
                await perform_swap(token)
    else:
        print('No Solana public keys or pair tokens found.')
        sys.stdout.flush()

# Register event handler for new messages
if CHAT_ID:
    @client.on(events.NewMessage(chats=int(CHAT_ID)))
    async def handler(event):
        await process_message(event)
else:
    @client.on(events.NewMessage())
    async def handler(event):
        await process_message(event)

# Run the client
async def main():
    try:
        print("Initializing PredatorSDK...")
        sys.stdout.flush()
        await sdk.initialize()  # Initialize the PredatorSDK
        print("PredatorSDK initialized successfully.")
        sys.stdout.flush()
    except Exception as e:
        print(f"Failed to initialize PredatorSDK: {str(e)}")
        sys.stdout.flush()
        # You might want to exit here if SDK initialization is critical
        # sys.exit(1)
    
    try:
        print("Starting Telegram client...")
        sys.stdout.flush()
        await client.start(phone_number)
        print("Telegram client started successfully.")
        sys.stdout.flush()
        # Save the session string to config
        session_string = client.session.save()
        print(f"Session String: {session_string}")
        sys.stdout.flush()
        await client.run_until_disconnected()
    except Exception as e:
        print(f"Error in Telegram client: {str(e)}")
        sys.stdout.flush()

if __name__ == '__main__':
    asyncio.run(main())