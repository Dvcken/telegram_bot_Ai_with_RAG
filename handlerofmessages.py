from os import getenv
from telegram import Update
from telegram.ext import *
import os
import tiktoken
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from testLLM import TestAI
from genai import GenAI
from sentence_transformers import SentenceTransformer
from qdrant_client.models import VectorParams, Distance
from qdrant_client.http import models
import uuid
import logging
#heart of this bot, this file process all messages

load_dotenv()
logging.basicConfig(level=logging.INFO)


client = QdrantClient(path=getenv('PATH_TO_QDRANT'))
collection_name ='1_collection'

if not client.collection_exists(collection_name):
   client.create_collection(
      collection_name=collection_name,
      vectors_config=VectorParams(size=384, distance=models.Distance.COSINE),
   )

class HandlerOfMessages:
    modes: list[str] = ['gemini', 'test']
    max_tokens: int = 65536
    num_neighbors: int = 3
    #Placeholder
    mode: str = 'test'

    #Commands

    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('Write something and AI will answer your question')

    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('/help - shows help message \n/mode - allows you to switch between models of AI')

    async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) != 0:
            mode = context.args[0].lower()
            if mode in HandlerOfMessages.modes:
                HandlerOfMessages.mode = mode
                await update.message.reply_text(f"Mode switched to {mode} mode.")
            else:
                #TBD
                await update.message.reply_text(f"Invalid mode. Choose between {', '.join(HandlerOfMessages.modes)}")
        else:
            await update.message.reply_text("Type in one of available models of AI")

    # Load pre-trained sentence transformer model
    model = SentenceTransformer('all-MiniLM-L6-v2')

    PASSWORD,ARTICLE_NAME,ARTICLE_CONTENT = range(3)
    password = ''
    database_article_name = ''
    database_article_content = ''

    # This function will also start the conversation for the /database command
    async def database(update: Update, context: ContextTypes.DEFAULT_TYPE):

        await update.message.reply_text("Accessing database mode. Please enter the password to continue.")

        return HandlerOfMessages.PASSWORD

    async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text == os.getenv('CORRECT_PASSWORD'):

            await update.message.reply_text("Password correct! Now, please enter the name of the article.")

            return HandlerOfMessages.ARTICLE_NAME
        else:

            await update.message.reply_text("Incorrect password. Please try again.")

            return HandlerOfMessages.PASSWORD

    async def article_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
        HandlerOfMessages.database_article_name = update.message.text

        await update.message.reply_text("Got it! Now, please enter the content of the article.")

        return HandlerOfMessages.ARTICLE_CONTENT

    async def article_content(update: Update, context: ContextTypes.DEFAULT_TYPE):

        HandlerOfMessages.database_article_content = update.message.text
        HandlerOfMessages.add_to_database(HandlerOfMessages.database_article_name,HandlerOfMessages.database_article_content)

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

    def get_embedding_from_text(text: str) -> list:
        return HandlerOfMessages.model.encode(text).tolist()

    #Adding data to database
    def add_to_database(article_name: str , article_content: str):
        vector = HandlerOfMessages.get_embedding_from_text(article_content)
        point_id = str(uuid.uuid4())
        payload = {"text": article_content, "name": article_name}
        try:
            client.upsert(
                collection_name=collection_name,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            logging.info(f"Text successfully added to Qdrant with ID: {point_id}")
        except Exception as e:
            logging.info(f"An error occurred while adding text: {e}")

    #Message handler

    # Initialize tiktoken encoder for counting tokens
    token_encoder = tiktoken.encoding_for_model('text-davinci-003')

    # Function to count tokens in a string
    def count_tokens(text: str) -> int:
        return len(HandlerOfMessages.token_encoder.encode(text))

    # Function to perform retrieval with token budget management
    def retrieve_docs(prompt, max_tokens=max_tokens, radius=1):
        query_vector = HandlerOfMessages.get_embedding_from_text(prompt)  # Convert text to vector
        search_result = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=None,
            limit=HandlerOfMessages.num_neighbors
        )
        query_embedding = []
        for point in search_result:
            query_embedding.append(point.payload.get("text", "Not found"))
            logging.info(query_embedding)

        retrieved_docs = []
        current_token_count = HandlerOfMessages.count_tokens(prompt)
        for data in query_embedding:
            doc_token_count = HandlerOfMessages.count_tokens(data)
            if current_token_count + doc_token_count < max_tokens:
                retrieved_docs.append(data)
                current_token_count += doc_token_count
            else:
                break


        return retrieved_docs

    #Function to generate prompt for AI with retrieved documents from database
    def generate_rag_prompt(prompt, max_tokens=max_tokens):
        retrieved_docs = HandlerOfMessages.retrieve_docs(prompt, max_tokens)
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
        match HandlerOfMessages.mode:
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
