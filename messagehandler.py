
from telegram import Update
from telegram.ext import *

from testLLM import TestAI
from genai import GenAI

from databasehandler import *
from commandhandler import *

import logging

class HandlerOfMessages:

    #Function to generate prompt for AI with retrieved documents from database
    def generate_rag_prompt(prompt):
        match Commands.mode_db:
            case 'postgres':
                db = Postgres()
                retrieved_docs = db.retrieve_docs(prompt)
            case 'qdrant':
                db = Qdrant()
                retrieved_docs = db.retrieve_docs(prompt)
            case _:
                retrieved_docs = []

        augmented_prompt = f"User question: {prompt}\n\nRelevant information:\n"
        if len(retrieved_docs) != 0:
            for docs in retrieved_docs:
                augmented_prompt += f"- {docs}\n"
            augmented_prompt += "\nProvide a detailed response based on the above information."
        else:
            augmented_prompt += f"Try answering this question as short as you can"
        logging.info(augmented_prompt)
        return augmented_prompt

    #Function that sends prompt to AI and send response to telegram bot API
    async def generate_message_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_message = update.message.text
        augmented_prompt: str = HandlerOfMessages.generate_rag_prompt(user_message)
        match Commands.mode_ai:
            case 'gemini':
                ai = GenAI()
                ai.prompt = augmented_prompt
                response = ai.generate_response()
            case 'test':
                ai = TestAI()
                ai.prompt = augmented_prompt
                response = ai.generate_response()
            case _:
                response = "This response can't be seen"

        await update.message.reply_text(response)
