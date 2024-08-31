# Telegram Sniper for Solana Tokens

This project implements a Telegram bot that monitors specified chats for Solana token addresses and automatically performs token swaps using the PredatorSDK.

## Features

- GUI for easy configuration and bot management
- Monitors Telegram chats for Solana token addresses
- Automatically performs token swaps when a valid address is detected
- Supports both public keys and pair tokens
- Optional Discord webhook integration for notifications
- Buys from multiples wallets

## Requirements

- Python 3.7+
- Telegram API credentials (API ID and API Hash)
- Solana wallet private key

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/telegram-solana-sniper.git
   cd telegram-solana-sniper
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up your Telegram API credentials and Solana wallet.

## Usage

1. Run the GUI:
   ```
   python gui.py
   ```

2. Fill in the required fields in the GUI.
3. Click "Run Bot" to start the bot.

Or you can start ```telegram.py``` using arguments.

## Configuration

You can save and load your configuration using the "Save Config" and "Load Config" buttons in the GUI.

## Disclaimer

This software is for educational purposes only. Use at your own risk. Always do your own research before making any cryptocurrency transactions.

## License

[MIT License](https://opensource.org/licenses/MIT)
