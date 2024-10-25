from telegram import Update
from telegram.ext import *
from handler_of_messages import *

# Can be changed
TELEGRAM_TOKEN: str = 'YOUR_TELEGRAM_TOKEN'


def main() -> None:
    #Bot initialization
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    #Detects telegram._Update and sends it to corresponding method
    app.add_handler(CommandHandler('start', Handler_of_messages.start_command, has_args=False))
    app.add_handler(CommandHandler('help', Handler_of_messages.help_command, has_args=False))
    app.add_handler(CommandHandler('mode', Handler_of_messages.mode_command))
    app.add_handler(MessageHandler(filters.TEXT, Handler_of_messages.message_response))

    #Bot starts to see messages
    app.run_polling()


if __name__ == '__main__':
    main()