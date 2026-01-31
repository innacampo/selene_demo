import json
import chromadb
from chromadb.utils import embedding_functions


def import_to_local_db(json_file):
    # Setup User's Local DB
    client = chromadb.PersistentClient(path="./user_med_db")
    embedding_model = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    collection = client.get_or_create_collection(
        name="medical_docs", embedding_function=embedding_model
    )

    # Load the pre-processed chunks
    with open(json_file, "r") as f:
        data = json.load(f)

    # Batch add to Chroma
    collection.add(
        documents=[item["text"] for item in data],
        metadatas=[item["metadata"] for item in data],
        ids=[item["id"] for item in data],
    )
    print(f"Success! {len(data)} chunks added to your individual knowledge base.")


# Usage
import_to_local_db("ingest_me.json")
