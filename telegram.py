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
from solders.keypair import Keypair
from solanatracker import SolanaTracker
import base64
from solders.transaction import Transaction
print("Launching bot")
sys.stdout.flush()

# Base58 alphabet
BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

# Pre-compiled regex pattern to find potential base58 strings
BASE58_PATTERN = re.compile(r'[1-9A-HJ-NP-Za-km-z]{32,44}')

# Argument parser setup
parser = argparse.ArgumentParser(description='Telegram Bot for Solana Swaps')
parser.add_argument('--api_id', required=True, help='Telegram API ID')
parser.add_argument('--api_hash', required=True, help='Telegram API Hash')
parser.add_argument('--phone_number', required=True, help='Telegram Phone Number')
parser.add_argument('--amount_to_swap', required=True, type=float, help='Amount to Swap')
parser.add_argument('--slippage', required=True, type=float, help='Slippage')
parser.add_argument('--priority_fee', required=True, type=float, help='Priority Fee')
parser.add_argument('--chatid', required=False, default='', help='Telegram Chat ID')
parser.add_argument('--discord', required=False, help='Discord Webhook URL')
parser.add_argument('--session_string', required=False, help='Telegram Session String')
parser.add_argument('--private_key', required=True, help='Private Key for Solana Wallet')
parser.add_argument('--api_key', required=True, help='API Key for Validation')

args = parser.parse_args()

api_id = args.api_id
api_hash = args.api_hash
phone_number = args.phone_number
AMOUNT_TO_SWAP = args.amount_to_swap
SLIPPAGE = args.slippage
PRIORITY_FEE = args.priority_fee
CHAT_ID = args.chatid
DISCORD_WEBHOOK_URL = args.discord
PRIVATE_KEY = args.private_key
api_key = args.api_key

PAIR_TOKEN_PATTERN = re.compile(r'[a-z0-9]{44}')  # Adjust the pattern if needed

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


async def perform_swap_with_jito(soltracker, swap_response: dict) -> str:
    try:
        serialized_transaction = base64.b64decode(swap_response["txn"])
        txn = Transaction.from_bytes(serialized_transaction)
        blockhash = soltracker.connection.get_latest_blockhash().value.blockhash

        txn.sign([soltracker.keypair], blockhash)
        print(txn)
        #response = soltracker.connection.send_raw_transaction(bytes(txn))
        #return soltracker.confirm_transaction(str(response.value))
    except Exception as e:
            return False

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

        txid = perform_swap_with_jito(solana_tracker, swap_response)
        print("Transaction ID:", txid)

        #txid = await solana_tracker.perform_swap(swap_response)

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
    session_string = client.session.save()
    print(f"Session String: {session_string}")
    sys.stdout.flush()
    await client.run_until_disconnected()

if __name__ == '__main__':
    api_key_validity_status = check_api_key_status(api_key)
    
    if not api_key_validity_status:
        print("Invalid API Key")
        sys.stdout.flush()
        exit(1)
    asyncio.run(main())
