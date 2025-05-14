import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (ApplicationBuilder, CommandHandler, ContextTypes,
                          MessageHandler, filters)

# from app.api.endpoint import ask
# from pydantic import BaseModel
import json
import requests

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Қош келдіңіз!")

# class QuestionRequest(BaseModel):
#     question: str

# Define the echo handler to interact with the /ask endpoint
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get the user's question from the Telegram message
    question = update.message.text

    '''
    ######### With model: #########
    try:
        # Create a QuestionRequest object
        request = QuestionRequest(question=question)

        # Call the ask function and get the response
        response = await ask(request)
        answer = json.loads(response.content)["answer"]

        # Send the answer back to the user via Telegram
        await context.bot.send_message(chat_id=update.effective_chat.id, text=answer)
    except Exception as e:
        # Handle exceptions during the API request
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Қате: {str(e)}")
    '''

    
    ######### With url: #########

    # Define the API endpoint for the /ask route
    api_url = "http://localhost:8000/ask "

    try:
        # Make a POST request to the /ask endpoint with the question
        response = requests.post(api_url, json={"question": question})

        # Check if the response is successful
        if response.status_code == 200:
            # Extract the answer from the API response
            answer = response.json().get("answer", "Жауап табылмады.")  # Default to "No answer found" if "answer" key is missing
        else:
            # Handle errors from the API response
            answer = f"Қате: {response.text}"

    except Exception as e:
        # Handle exceptions during the API request
        answer = f"Қате: {str(e)}"

    # Send the answer back to the user via Telegram
    await context.bot.send_message(chat_id=update.effective_chat.id, text=answer)
    

if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_API_TOKEN).build()

    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    application.add_handler(start_handler)
    application.add_handler(echo_handler)

    application.run_polling()