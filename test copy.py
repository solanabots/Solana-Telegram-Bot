import sys
from solanatracker import SolanaTracker
import base64
from solders.transaction import Transaction
from solders.keypair import Keypair


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
        keypair = Keypair.from_base58_string("")

        solana_tracker = SolanaTracker(keypair, "https://api.solanatracker.io/rpc")

        swap_response = await solana_tracker.get_swap_instructions(
            "So11111111111111111111111111111111111111112",  # From Token (SOL)
            to_token,  # To Token (found in tweet)
            0.001,  # Amount to swap from config.json
            25,  # Slippage from config.json
            str(keypair.pubkey()),  # Payer public key
            0.001,  # Priority fee from config.json (Recommended while network is congested)
            False,  # Force legacy transaction for Jupiter
        )

        txid = perform_swap_with_jito(solana_tracker, swap_response)
        print("Transaction ID:", txid)

        #txid = await solana_tracker.perform_swap(swap_response)

        print("Transaction ID:", txid)
        print("Transaction URL:", f"https://solscan.io/tx/{txid}")
        sys.stdout.flush()
        
    except Exception as e:
        print(f"Error performing swap: {e}")
        sys.stdout.flush()



        

   

if __name__ == '__main__':
     perform_swap("4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R")
