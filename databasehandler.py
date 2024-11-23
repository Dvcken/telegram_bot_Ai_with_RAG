import tiktoken
from dotenv import load_dotenv
from qdrant_client import QdrantClient
import sqlalchemy as sql
from sqlalchemy.orm import declarative_base, sessionmaker
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import BallTree
from qdrant_client.models import VectorParams, Distance
from qdrant_client.http import models
import uuid
import logging
import os
from sqlalchemy import inspect

load_dotenv()
logging.basicConfig(level=logging.INFO)
token_encoder = tiktoken.encoding_for_model('text-davinci-003')
model = SentenceTransformer('all-MiniLM-L6-v2')
Base = declarative_base()
max_tokens: int = 65536

#qdrant database
class Qdrant:
    collection_name = '1_collection'
    num_neighbors: int = 3

    client = QdrantClient(path=os.getenv('PATH_TO_QDRANT'))

    def add_to_database(article_name: str, article_content: str):
        if not Qdrant.client.collection_exists(Qdrant.collection_name):
            Qdrant.client.create_collection(
                collection_name=Qdrant.collection_name,
                vectors_config=VectorParams(size=384, distance=models.Distance.COSINE),
            )
        vector = model.encode(article_content).tolist()
        point_id = str(uuid.uuid4())
        payload = {"text": article_content, "name": article_name}
        try:
            Qdrant.client.upsert(
                collection_name=Qdrant.collection_name,
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

    def retrieve_docs(prompt, max_tokens=max_tokens):
        print(str(prompt))
        query_vector = model.encode(str(prompt)).tolist() # Convert text to vector
        query_embedding = []
        try:
            search_result = Qdrant.client.search(
                collection_name=Qdrant.collection_name,
                query_vector=query_vector,
                query_filter=None,
                limit=Qdrant.num_neighbors
            )
            for point in search_result:
                query_embedding.append(point.payload.get("text", "Not found"))
                logging.info(f'text added to query_embedding: {point.payload.get("text", "Not found")}')
        except Exception as e:
            logging.info(f"An error occurred while searching for text: {e}")

        retrieved_docs = []
        current_token_count = len(token_encoder.encode(str(prompt)))
        for data in query_embedding:
            doc_token_count = len(token_encoder.encode(data))
            if current_token_count + doc_token_count < max_tokens:
                retrieved_docs.append(data)
                current_token_count += doc_token_count
            else:
                break

        return retrieved_docs

#postgres

class Data(Base):
    __tablename__ = 'data'
    id = sql.Column(sql.Integer(), primary_key=True)
    name = sql.Column(sql.String(100), nullable=True)
    data = sql.Column(sql.String, nullable=True)
    embedding = sql.Column(sql.ARRAY(sql.Float), nullable=True)

class Postgres:
    engine = sql.create_engine(os.getenv('DATABASE_URL'))
    if not inspect(engine).has_table('Data'):
        Base.metadata.create_all(engine)
    engine.connect()
    Session = sessionmaker(bind=engine)
    session = Session()
    data_query = session.query(Data)

    def add_to_database(article_name: str, article_content: str):

        Session_add = sessionmaker(bind=Postgres.engine)
        session_add = Session_add()
        session_add_query = Postgres.session.query(Data)
        article = Data(
            id=session_add_query.count() + 1,
            name=article_name,
            data=article_content,
            embedding=sql.null()
        )
        session_add.add(article)
        session_add.commit()
        session_add.flush()
        Postgres.create_embedding(session_add_query.count())

    def create_embedding(id: int):
        print(id)
        update_embeddings = Postgres.data_query.filter(Data.id == id)
        for data in update_embeddings:
            data_to_embed = data.data
            embedded_data = model.encode(data_to_embed)
            embedded_data_float = []
            for number in embedded_data:
                embedded_data_float.append(float(number))
            update_embeddings.update({Data.embedding: embedded_data_float})
        Postgres.session.commit()
        Postgres.session.flush()

    def retrieve_docs(prompt, max_tokens=max_tokens, radius=1):
        prompt_embedding = model.encode([str(prompt)])
        query_embedding = []
        for i in range(1, Postgres.data_query.count() + 1):
            update_embeddings = Postgres.data_query.filter(Data.id == i)
            for data in update_embeddings:
                vector_for_KNN = data.embedding
                query_embedding.append(vector_for_KNN)
            Postgres.session.flush()
            ball_tree_model = BallTree(query_embedding, leaf_size=30)
            ind = ball_tree_model.query_radius(prompt_embedding, r=radius)
            retrieved_docs = []
            current_token_count = len(token_encoder.encode(str(prompt)))
            for idx in ind[0]:
                data_for_prompts = Postgres.data_query.filter(Data.id == (idx.item() + 1))
                Postgres.session.flush()
                for data in data_for_prompts:
                    doc_token_count = len(token_encoder.encode(data))
                    if current_token_count + doc_token_count < max_tokens:
                        retrieved_docs.append(data.data)
                        current_token_count += doc_token_count
                    else:
                        break

        return retrieved_docs