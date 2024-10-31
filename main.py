from telegram import Update
from telegram.ext import *
from handlerofmessages import *
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN')


def main() -> None:
    #Bot initialization
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    #Detects telegram._Update and sends it to corresponding method
    app.add_handler(CommandHandler('start', HandlerOfMessages.start_command, has_args=False))
    app.add_handler(CommandHandler('help', HandlerOfMessages.help_command, has_args=False))
    app.add_handler(CommandHandler('mode', HandlerOfMessages.mode_command))
    app.add_handler(MessageHandler(filters.TEXT, HandlerOfMessages.generate_message_response))

    #Bot starts to see messages
    print('Start polling...')
    app.run_polling()


if __name__ == '__main__':
    main()