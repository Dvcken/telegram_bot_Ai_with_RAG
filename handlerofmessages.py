from telegram import Update
from telegram.ext import *
import os
import glob
from sentence_transformers import SentenceTransformer
import tiktoken
from sklearn.neighbors import NearestNeighbors
from dotenv import load_dotenv
from testLLM import TestAI
from genai import GenAI
#heart of this bot, this file process all messages
load_dotenv()



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

    path = os.getenv('PATH_TO_DATA')

    corpus = []

    for filename in glob.glob(os.path.join(path,'*.txt')):
        with open(os.path.join(os.getcwd(), filename), 'r') as file:
            data = file.read().rstrip()
            corpus.append(data)



    # Encode the corpus
    corpus_embeddings = model.encode(corpus)

    # Create a NearestNeighbors model using scikit-learn
    neighbors_model = NearestNeighbors(n_neighbors=3, metric='cosine').fit(corpus_embeddings)

    # Function to count tokens in a string
    def count_tokens(text: str) -> int:
        return len(HandlerOfMessages.token_encoder.encode(text))

    # Function to perform retrieval with token budget management
    def retrieve_documents(query, max_tokens=max_tokens, top_k=3):
        query_embedding = HandlerOfMessages.model.encode([query])

        # Find the nearest neighbors
        distances, indices = HandlerOfMessages.neighbors_model.kneighbors(query_embedding, n_neighbors=top_k)

        retrieved_docs = []
        current_token_count = HandlerOfMessages.count_tokens(query)

        # Add documents one by one while ensuring token budget is not exceeded
        for idx in indices[0]:
            doc = HandlerOfMessages.corpus[idx]
            doc_token_count = HandlerOfMessages.count_tokens(doc)
            if current_token_count + doc_token_count < max_tokens:
                retrieved_docs.append(doc)
                current_token_count += doc_token_count
            else:
                break

        return retrieved_docs

    # Function to generate a response using RAG with token management
    def generate_rag_prompt(query, max_tokens=max_tokens) -> str:
        # Step 1: Retrieve relevant documents within the token limit
        retrieved_docs = HandlerOfMessages.retrieve_documents(query, max_tokens=max_tokens)
        # Step 2: Augment the prompt with retrieved documents
        augmented_prompt = f"User question: {query}\n\nRelevant information:\n"
        for doc in retrieved_docs:
            augmented_prompt += f"- {doc}\n"

        augmented_prompt += "\nProvide a detailed response based on the above information."
        print(augmented_prompt)
        return augmented_prompt


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


"""
class LanguageModels:

    def __init__(self, prompt: str):

        self.prompt: str = prompt

    def generate_response(self, prompt: str) -> str:
        pass
"""
