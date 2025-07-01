import chromadb
from chromadb.config import Settings

def main():
    client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory="../chroma"))

    collection_name = input("Enter the name of the collection to count documents: ").strip()

    try:
        collection = client.get_collection(name=collection_name)
        count = collection.count()
        print(f"Collection '{collection_name}' contains {count} documents.")
    except Exception as e:
        print(f"Failed to access collection '{collection_name}': {e}")

if __name__ == "__main__":
    main()
# This script counts the number of documents in a specified ChromaDB collection.