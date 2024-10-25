from telegram import Update
from telegram.ext import *
import genai
from sentence_transformers import SentenceTransformer
import tiktoken
from sklearn.neighbors import NearestNeighbors

#heart of this bot, this file process all messages



class Handler_of_messages:
    modes: list[str] = ['gemini', 'chatgpt']
    #Placeholder
    mode: str = 'chatgpt'

    #Commands

    async def start_command(update: Update, context):
        await update.message.reply_text('Write something and AI will answer your question')

    async def help_command(update: Update, context):
        await update.message.reply_text('/help - shows help message \n/mode - allows you to switch between models of AI')

    async def mode_command(update: Update, context):
        if len(context.args) != 0:
            mode = context.args[0].lower()
            if mode in Handler_of_messages.modes:
                Handler_of_messages.mode = mode
                await update.message.reply_text(f"Mode switched to {mode} mode.")
            else:
                #TBD
                await update.message.reply_text(f"Invalid mode. Choose between {', '.join(Handler_of_messages.modes)}")
        else:
            await update.message.reply_text("Type in one of available models of AI")

    #Message handler

    # Load pre-trained sentence transformer model
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Initialize tiktoken encoder for counting tokens
    token_encoder = tiktoken.encoding_for_model('text-davinci-003')

    # Example corpus
    # Strings are for example better to change them for text files with proper information
    corpus = [
        "What is artificial intelligence?",
        "How does machine learning work?",
        "What is RAG in the context of LLMs?",
        "Cat's favourite food",
        "Density of Rocks",
        "Ancestors of cats",
        "Which pet is better: cat or dog?",
        "Why cats are considered feline"
        # Add more documents...
    ]

    # Encode the corpus
    corpus_embeddings = model.encode(corpus)

    # Create a NearestNeighbors model using scikit-learn
    neighbors_model = NearestNeighbors(n_neighbors=3, metric='cosine').fit(corpus_embeddings)

    # Function to count tokens in a string
    def count_tokens(text: str) -> int:
        return len(Handler_of_messages.token_encoder.encode(text))

    # Function to perform retrieval with token budget management
    def retrieve_documents(query, max_tokens=512, top_k=3):
        query_embedding = Handler_of_messages.model.encode([query])

        # Find the nearest neighbors
        distances, indices = Handler_of_messages.neighbors_model.kneighbors(query_embedding, n_neighbors=top_k)

        retrieved_docs = []
        current_token_count = Handler_of_messages.count_tokens(query)

        # Add documents one by one while ensuring token budget is not exceeded
        for idx in indices[0]:
            doc = Handler_of_messages.corpus[idx]
            doc_token_count = Handler_of_messages.count_tokens(doc)
            if current_token_count + doc_token_count < max_tokens:
                retrieved_docs.append(doc)
                current_token_count += doc_token_count
            else:
                break

        return retrieved_docs

    # Function to generate a response using RAG with token management
    def generate_rag_response(query, max_tokens=512) -> str:
        # Step 1: Retrieve relevant documents within the token limit
        retrieved_docs = Handler_of_messages.retrieve_documents(query, max_tokens=max_tokens)

        # Step 2: Augment the prompt with retrieved documents
        augmented_prompt = f"User question: {query}\n\nRelevant information:\n"
        for doc in retrieved_docs:
            augmented_prompt += f"- {doc}\n"

        augmented_prompt += "\nProvide a detailed response based on the above information."
        #print(augmented_prompt)
        return augmented_prompt


    async def message_response(update: Update, context):
        user_message = update.message.text
        augmented_prompt = Handler_of_messages.generate_rag_response(user_message)
        match Handler_of_messages.mode:
            case 'gemini':
                response = genai.generate_genai_response(augmented_prompt)
            case 'chatgpt':
                response = 'CHATGPT_TEXT_GENERATION_METHOD'
            case _:
                response = 'Oops, i tried to generate response from non-existing AI model...'
        await update.message.reply_text(response)
