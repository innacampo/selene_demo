import chromadb
from chromadb.utils import embedding_functions


def search_medical_knowledge(query_text):
    # 1. Connect to the existing local DB
    client = chromadb.PersistentClient(path="./user_med_db")

    # 2. Use the EXACT same embedding model as ingestion
    embedding_model = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    collection = client.get_collection(
        name="medical_docs", embedding_function=embedding_model
    )

    # 3. Search for the top 3 most relevant chunks
    results = collection.query(query_texts=[query_text], n_results=3)

    # 4. Format the output for MedGemma
    context = "\n---\n".join(results["documents"][0])
    return context


# Test it out
user_question = "I feel like I'm losing my mind at work because of 'brain fog.' What does the latest research say about managing this?"
retrieved_context = search_medical_knowledge(user_question)

print("FOUND CONTEXT:")
print(retrieved_context)
