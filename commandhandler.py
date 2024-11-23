from telegram import Update
from telegram.ext import *
import os
from dotenv import load_dotenv
load_dotenv()


class Commands:
    modes_ai: list[str] = ['gemini', 'test']
    modes_db: list[str] = ['postgres', 'qdrant']
    mode_ai: str = 'test'
    mode_db: str = 'qdrant'

    # Commands

    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('Write something and AI will answer your question')

    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            '/help - shows help message \n/mode - allows you to switch between models of AI')

    async def mode_ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) != 0:
            mode = context.args[0].lower()
            if mode in Commands.modes_ai:
                Commands.mode_ai = mode
                await update.message.reply_text(f"Mode switched to {mode} mode of AI.")
            else:
                await update.message.reply_text(f"Invalid mode. Choose between {', '.join(Commands.modes_ai)}")
        else:
            await update.message.reply_text("Type in one of available models of AI")

    async def mode_db_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) != 0:
            mode = context.args[0].lower()
            if mode in Commands.modes_db:
                Commands.mode_db = mode
                await update.message.reply_text(f"Mode switched to {mode} mode of database.")
            else:
                await update.message.reply_text(f"Invalid mode. Choose between {', '.join(Commands.modes_db)}")
        else:
            await update.message.reply_text("Type in one of available models of database")

    PASSWORD, ARTICLE_NAME, ARTICLE_CONTENT = range(3)
    password = ''
    database_article_name = ''
    database_article_content = ''

    # This function will also start the conversation for the /database command
    async def database(update: Update, context: ContextTypes.DEFAULT_TYPE):

        await update.message.reply_text("Accessing database mode. Please enter the password to continue.")

        return Commands.PASSWORD

    async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text == os.getenv('CORRECT_PASSWORD'):

            await update.message.reply_text("Password correct! Now, please enter the name of the article.")

            return Commands.ARTICLE_NAME
        else:

            await update.message.reply_text("Incorrect password. Please try again.")

            return Commands.PASSWORD

    async def article_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
        Commands.database_article_name = update.message.text

        await update.message.reply_text("Got it! Now, please enter the content of the article.")

        return Commands.ARTICLE_CONTENT

    async def article_content(update: Update, context: ContextTypes.DEFAULT_TYPE):

        Commands.database_article_content = update.message.text
        Commands.add_to_database(Commands.database_article_name, Commands.database_article_content)

        await update.message.reply_text(f"Article saved successfully!")

        return ConversationHandler.END

    async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

        await update.message.reply_text("Operation cancelled. Type /start or /database to try again.")

        return ConversationHandler.END

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("database", database)],
        # Start with /database
        states={
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_password)],
            ARTICLE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, article_name)],
            ARTICLE_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, article_content)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],  # Handle cancellation with /cancel
    )