import chromadb
from chromadb.config import Settings

def main():
    client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory="../chroma"))

    collection_name = input("Enter the name of the collection to delete: ").strip()

    try:
        client.delete_collection(name=collection_name)
        print(f"Collection '{collection_name}' deleted.")
    except Exception as e:
        print(f"Failed to delete collection '{collection_name}': {e}")

if __name__ == "__main__":
    main()
