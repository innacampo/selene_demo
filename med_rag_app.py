# curl -fsSL https://ollama.com/install.sh | sh
# ollama run medgemma

import chromadb
from chromadb.utils import embedding_functions
import requests  # We will use Ollama's local API


def get_context(query):
    client = chromadb.PersistentClient(path="./user_med_db")
    embedding_model = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    collection = client.get_collection(
        name="medical_docs", embedding_function=embedding_model
    )

    return collection.query(query_texts=[query], n_results=3)


def ask_medgemma(query):
    # Fetch top 3 chunks and their source metadata
    results = get_context(query)
    context = "\n".join(results["documents"][0])
    sources = list(
        set([m["source"] for m in results["metadatas"][0]])
    )  # Get unique filenames

    # The Prompt
    prompt = f"""
    You are MedGemma, a medical assistant. Use the provided context to answer the user's question.
    If the answer isn't in the context, tell the user you don't have enough specific data in your library.

    Context:
    {context}

    Question: {query}
    
    Answer:"""

    # Connect to local Ollama API
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "medgemma", "prompt": prompt, "stream": False},
    )
    final_answer = response.json()["response"]
    return f"{final_answer}\n\nSources used: {', '.join(sources)}"


# Try it out!
question = "How often should I visit a dentist based on the studies?"
print(f"\nAsking MedGemma: {question}...")
print("-" * 30)
print(ask_medgemma(question))
