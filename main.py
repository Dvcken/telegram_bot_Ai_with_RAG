from messagehandler import *
from commandhandler import *
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN')


def main() -> None:
    #Bot initialization
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    #Detects telegram._Update and sends it to corresponding method
    app.add_handler(CommandHandler('start', Commands.start_command, has_args=False))
    app.add_handler(CommandHandler('help', Commands.help_command, has_args=False))
    app.add_handler(CommandHandler('modeai', Commands.mode_ai_command))
    app.add_handler(CommandHandler('modedb', Commands.mode_db_command))
    app.add_handler(Commands.conv_handler)
    app.add_handler(MessageHandler(filters.TEXT, HandlerOfMessages.generate_message_response))


    #Bot starts to see messages
    print('Start polling...')
    app.run_polling()


if __name__ == '__main__':
    main()