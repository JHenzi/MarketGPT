import random
import time
import requests
import re
import chromadb
from chromadb.config import Settings

# Setup Chroma client and collection
client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory="./chroma"))
collection = client.get_or_create_collection(name="marketwatch")

def clean_where_dict(where_dict):
    # Remove keys with None values because Chroma does not accept None in filters
    return {k: v for k, v in where_dict.items() if v is not None}

def summarize_article(article_text, model_endpoint):
    prompt = f"Summarize this news article clearly and briefly:\n\n{article_text}\n\nSummary:"
    messages = [
        {"role": "system", "content": "You are a helpful summarization assistant."},
        {"role": "user", "content": prompt},
    ]
    try:
        response = requests.post(
            model_endpoint,
            json={
                "messages": messages,
                "temperature": 0.3,
                # max_tokens removed intentionally
            },
            timeout=30
        )
        response.raise_for_status()
        response_json = response.json()
        summary = response_json["choices"][0]["message"]["content"]

        # Remove all <think>...</think> tags and their content
        summary_clean = re.sub(r"<think>.*?</think>", "", summary, flags=re.DOTALL).strip()

        return summary_clean
    except Exception as e:
        print(f"Error during summarization API call: {e}")
        raise

def sample_and_summarize(collection, model_endpoint, batch_size=5, delay=1.0):
    # Get documents where ai_summary field is empty string (using get instead of query)
    results = collection.get(
        where={"ai_summary": {"$eq": ""}},
        limit=100,
        include=["documents", "metadatas"]
    )
    docs = results["documents"]
    metas = results["metadatas"]
    
    if not docs:
        print("No documents to summarize.")
        return
    
    # Now get the ids for these docs via collection.get()
    # (Assuming 'link' is unique and in metadata, you can filter by these links)
    links = [meta["link"] for meta in metas]
    
    # Retrieve the ids matching these links - fixed to use $in operator
    get_results = collection.get(where={"link": {"$in": links}}, include=["ids"])
    ids = get_results["ids"]
    
    print(f"Found {len(docs)} unsummarized docs, sampling {batch_size}...")
    sampled_indices = random.sample(range(len(docs)), min(batch_size, len(docs)))
    
    for idx in sampled_indices:
        doc = docs[idx]
        meta = metas[idx]
        doc_id = ids[idx]
        
        try:
            print(f"Summarizing doc id {doc_id} titled '{meta.get('title', 'No Title')}'")
            summary = summarize_article(doc, model_endpoint)
            meta["ai_summary"] = summary
            
            collection.update(
                ids=[doc_id],
                metadatas=[meta]
            )
            print(f"Updated summary for doc id {doc_id}")
            time.sleep(delay)
        except Exception as e:
            print(f"Error summarizing doc id {doc_id}: {e}")

if __name__ == "__main__":
    MODEL_ENDPOINT = "http://192.168.1.220:1234/v1/chat/completions"
    sample_and_summarize(collection, MODEL_ENDPOINT)
