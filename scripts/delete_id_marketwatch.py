# delete_id_marketwatch.py

import sys
#from chromadb import Client
import chromadb
from chromadb.config import Settings

# This script targets the "marketwatch" collection
# Setup Chroma
client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory="./chroma"))
collection = client.get_or_create_collection(name="marketwatch")
COLLECTION_NAME = "marketwatch"

def main():
    if len(sys.argv) != 2:
        print("Usage: python delete_id_marketwatch.py <document_id>")
        sys.exit(1)

    doc_id = sys.argv[1]

    try:
        # Initialize ChromaDB client
        #client = Client(Settings())
        collection = client.get_collection(name=COLLECTION_NAME)

        # Attempt to delete the provided ID
        collection.delete(ids=[doc_id])
        print(f"[INFO] Successfully deleted ID: {doc_id} from collection: {COLLECTION_NAME}")
    except Exception as e:
        print(f"[ERROR] Failed to delete ID {doc_id} from {COLLECTION_NAME}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
# This script deletes a specific document by ID from the "marketwatch" collection in ChromaDB.
# Usage: python delete_id_marketwatch.py <document_id>
# Ensure you have the necessary permissions and that the ID exists in the collection before running this script.
# This script is useful for cleaning up or managing specific entries in the "marketwatch" collection
# without affecting the entire dataset.
# Make sure to run this script in an environment where ChromaDB is properly configured and the
# "marketwatch" collection exists.