# Qazakqtan QA Bot

## Features

- Uses the T5 model fine-tuned for Qazaq question answering.
- Provides quick responses to user queries.

## Setup

1. Clone this repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your Telegram API token:
   ```
   TELEGRAM_API_TOKEN=your_telegram_api_token
   ```
4. Run the bot:
   ```
   python bot.py
   ```

## Usage

1. Start a chat with your bot on Telegram.
2. Send a questions.
3. The bot will respond with an answer.

## Credits

The bot uses the "Kyrmasch/t5-kazakh-qa" model. 