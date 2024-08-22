import json
import logging
import re
import os
import asyncio
import sys
import requests
import aiohttp
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from solders.keypair import Keypair
from solanatracker import SolanaTracker

print("Launching bot")
sys.stdout.flush()

# Base58 alphabet
BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

# Pre-compiled regex pattern to find potential base58 strings
BASE58_PATTERN = re.compile(r'[1-9A-HJ-NP-Za-km-z]{32,44}')

# Get the %APPDATA% directory
appdata_dir = os.getenv('APPDATA')

# Construct the full path to config.json
config_path = os.path.join(appdata_dir, 'predator', 'tools', 'telegram', 'config.json')

# Open and read the config.json file
with open(config_path, 'r') as f:
    config = json.load(f)

api_id = config.get('api_id')
api_hash = config.get('api_hash')
phone_number = config.get('phone_number')
AMOUNT_TO_SWAP = config.get('amount_to_swap')
SLIPPAGE = config.get('slippage')
PRIORITY_FEE = config.get('priority_fee')
CHAT_ID = config.get('chatid', '')
DISCORD_WEBHOOK_URL = config.get('discord')

PAIR_TOKEN_PATTERN = re.compile(r'[a-z0-9]{44}')  # Adjust the pattern if needed

# Load or create a new StringSession
session_string = config.get('session_string', None)
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

async def perform_swap(to_token: str):
    try:
        keypair = Keypair.from_base58_string(PRIVATE_KEY)

        solana_tracker = SolanaTracker(keypair, "https://api.solanatracker.io/rpc")

        swap_response = await solana_tracker.get_swap_instructions(
            "So11111111111111111111111111111111111111112",  # From Token (SOL)
            to_token,  # To Token (found in tweet)
            AMOUNT_TO_SWAP,  # Amount to swap from config.json
            SLIPPAGE,  # Slippage from config.json
            str(keypair.pubkey()),  # Payer public key
            PRIORITY_FEE,  # Priority fee from config.json (Recommended while network is congested)
            True,  # Force legacy transaction for Jupiter
        )

        txid = await solana_tracker.perform_swap(swap_response)

        print("Transaction ID:", txid)
        print("Transaction URL:", f"https://solscan.io/tx/{txid}")
        sys.stdout.flush()

        # Check if the Discord webhook URL is set before notifying
        if DISCORD_WEBHOOK_URL:
            notify_discord(txid)
        
    except Exception as e:
        print(f"Error performing swap: {e}")
        sys.stdout.flush()

def notify_discord(txid: str):
    message = {
        "content": f"Swap successful!\nTransaction ID: {txid}\nTransaction URL: https://solscan.io/tx/{txid}"
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

async def process_message(event):
    message_text = event.message.text
    token, token_type = find_first_token_or_public_key(message_text)

    if token:
        if token_type == 'public_key':
            print(f'Found Solana public key: {token}')
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
                print('No quote mint found for the pair token.')
                sys.stdout.flush()
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

def check_api_key_status(api_key: str) -> bool:
    try:
        response = requests.post(
            'https://client.predator.bot/validatetelegram.php',
            data={'api_key': api_key},
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        response_data = response.json()
        
        # Check if the status in response data is active
        return response_data.get('status') == 'active'
        
    except Exception as error:
        print(f'Error validating API key: {error}')
        sys.stdout.flush()
        return False
        
# Run the client
async def main():
    await client.start(phone_number)
    # Save the session string to config
    config['session_string'] = client.session.save()
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    await client.run_until_disconnected()

if __name__ == '__main__':
    api_key_validity_status = check_api_key_status(config.get('api_key'))
    
    if not api_key_validity_status:
        print("Invalid API Key")
        sys.stdout.flush()
        exit(1)
    asyncio.run(main())
