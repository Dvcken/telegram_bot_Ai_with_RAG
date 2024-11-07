from os import getenv
from telegram import Update
from telegram.ext import *
import os
import glob
from sentence_transformers import SentenceTransformer
import tiktoken
from dotenv import load_dotenv
from testLLM import TestAI
from genai import GenAI
import sqlalchemy as sql
from sqlalchemy.orm import declarative_base, sessionmaker
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import BallTree

#heart of this bot, this file process all messages

load_dotenv()

#Initialization of database and query pull
Base = declarative_base()

class Data(Base):
    __tablename__ = 'data'

    id = sql.Column(sql.Integer(), primary_key=True)
    name = sql.Column(sql.String(100), nullable=True)
    data = sql.Column(sql.String, nullable=True)
    embedding = sql.Column(sql.ARRAY(sql.Float), nullable=True)

engine = sql.create_engine(getenv('ENGINE'))
engine.connect()
Session = sessionmaker(bind=engine)
session = Session()
data_query = session.query(Data)

class HandlerOfMessages:
    modes: list[str] = ['gemini', 'test']
    max_tokens: int = 512
    #Placeholder
    mode: str = 'test'

    #Commands

    async def start_command(update: Update, context):
        await update.message.reply_text('Write something and AI will answer your question')

    async def help_command(update: Update, context):
        await update.message.reply_text('/help - shows help message \n/mode - allows you to switch between models of AI')

    async def mode_command(update: Update, context):
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

    #Message handler

    # Load pre-trained sentence transformer model
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Initialize tiktoken encoder for counting tokens
    token_encoder = tiktoken.encoding_for_model('text-davinci-003')

    # Function to count tokens in a string
    def count_tokens(text: str) -> int:
        return len(HandlerOfMessages.token_encoder.encode(text))

    #Initialization of model with acquired vectors
    query_embedding = []
    for i in range(1, data_query.count() + 1):
        update_embeddings = data_query.filter(Data.id == i)

        for data in update_embeddings:
            vector_for_KNN = data.embedding
            query_embedding.append(vector_for_KNN)
        session.flush()

    ball_tree_model = BallTree(query_embedding, leaf_size=30)

    # Function to perform retrieval with token budget management
    def retrieve_docs(prompt, max_tokens=max_tokens, radius=2):
        prompt_embedding = HandlerOfMessages.model.encode([prompt])
        ind = HandlerOfMessages.ball_tree_model.query_radius(prompt_embedding, r=radius)
        retrieved_docs = []
        current_token_count = HandlerOfMessages.count_tokens(prompt)
        for idx in ind[0]:
            data_for_prompts = data_query.filter(Data.id == (idx.item() + 1))
            session.flush()
            for data in data_for_prompts:
                doc_token_count = HandlerOfMessages.count_tokens(data.data)
                if current_token_count + doc_token_count < max_tokens:
                    retrieved_docs.append(data.data)
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

        return augmented_prompt

    #Function that sends prompt to AI and send response to telegram bot API
    async def generate_message_response(update: Update, context):
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
