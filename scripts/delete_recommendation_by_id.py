# delete_id_recommendations.py

import sys
import chromadb
from chromadb.config import Settings

# Setup ChromaDB client with your config
client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory="./chroma"))
COLLECTION_NAME = "recommendations"
collection = client.get_or_create_collection(name=COLLECTION_NAME)

def main():
    if len(sys.argv) != 2:
        print("Usage: python delete_id_recommendations.py <document_id>")
        sys.exit(1)

    doc_id = sys.argv[1]

    try:
        # Get collection again to be sure
        collection = client.get_collection(name=COLLECTION_NAME)

        # Delete the document by ID
        collection.delete(ids=[doc_id])
        print(f"[INFO] Successfully deleted ID: {doc_id} from collection: {COLLECTION_NAME}")
    except Exception as e:
        print(f"[ERROR] Failed to delete ID {doc_id} from {COLLECTION_NAME}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

# Usage:
# python delete_id_recommendations.py <document_id>
# Ensure you have the necessary permissions and that the ID exists in the collection before running this
# script. This script is useful for cleaning up or managing specific entries in the "recommendations" collection
# without affecting the entire dataset. Make sure to run this script in an environment where ChromaDB is properly configured and the
# "recommendations" collection exists.