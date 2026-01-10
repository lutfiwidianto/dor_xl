# DOR_XL (Forked/Modified Project)

![banner](bnr.png)

CLI client for a certain Indonesian mobile internet service provider.

# API Key
Set your API key in `api.key` (one line) or enter it when prompted on first run.

# Quick Start (Termux)
1. Update & install dependencies
```
pkg update && pkg upgrade -y
pkg install git python -y
```
2. Clone this repo
```
git clone https://github.com/lutfiwidianto/dor_xl
cd dor_xl
```
3. Install & setup alias
```
bash install.sh
```
4. Run
```
dor
```

# Telegram OTP Setup
App registration uses Telegram OTP. Create a bot and set env vars before running:
```
export DORXL_TG_BOT_TOKEN="123456:ABCDEF"
export DORXL_TG_BOT_USERNAME="your_bot_username"
```
User must open the bot in Telegram and send `/start` first.

# Quick Start (Windows)
1. Clone this repo
```
git clone https://github.com/lutfiwidianto/dor_xl
cd dor_xl
```
2. Install & setup
```
install.bat
```
3. Run
```
dor
```
4. Optional: use `dor` from any folder
   - Add the project folder to PATH
     - Press Win+R, type `sysdm.cpl`, press Enter
     - Advanced tab -> Environment Variables
     - Under "User variables", select "Path" -> Edit -> New
     - Add: the full path to this folder (example: `C:\DOR_XL\online`)
     - OK -> OK, then reopen your terminal
   - Or create a global shortcut
     - Copy `dor.cmd` to a folder already in PATH (example: `C:\Windows`)

# Info

## Attribution
This project is a derivative of an existing CLI client (me-cli). I only modify and extend it; I am not the original author.

## Dependencies (Network)
This app connects only to these services:
- XL/MyXL official APIs
- Firebase (Auth + Database)
- Telegram Bot API (OTP)
- GitHub (update only if you use the update menu)

## PS for Certain Indonesian mobile internet service provider

Instead of just delisting the package from the app, ensure the user cannot purchase it.
What's the point of strong client side security when the server don't enforce it?

## Terms of Service
By using this tool, the user agrees to comply with all applicable laws and regulations and to release the developer from any and all claims arising from its use.

## Original Contact

contact@mashu.lol
# Proyek dor_xl
