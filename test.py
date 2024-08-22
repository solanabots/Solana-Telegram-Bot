from solanatracker import SolanaTracker
import base64
from solders.keypair import Keypair
from solders.transaction import Transaction
from solders.signature import Signature
from solana.rpc.api import Client

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

async def swap():
    keypair = Keypair.from_base58_string("")

    solana_tracker = SolanaTracker(keypair, "https://api.solanatracker.io/rpc")

    swap_response = await solana_tracker.get_swap_instructions(
        "So11111111111111111111111111111111111111112",  # From Token
        "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # To Token
        0.0005,  # Amount to swap
        30,  # Slippage
        str(keypair.pubkey()),  # Payer public key
    )

    #txid = await solana_tracker.perform_swap(swap_response)
    txid = await perform_swap_with_jito(solana_tracker, swap_response)
     

    # Returns txid when the swap is successful or raises an exception if the swap fails
    print("Transaction ID:", txid)
    print("Transaction URL:", f"https://explorer.solana.com/tx/{txid}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(swap())