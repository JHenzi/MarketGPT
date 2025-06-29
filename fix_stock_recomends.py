import chromadb
from chromadb.config import Settings

# === Configuration ===
CHROMA_DB_PATH = "./chroma"  # Update if different
COLLECTION_NAME = "stock_recommendations"

# === Connect to ChromaDB ===
client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory=CHROMA_DB_PATH
))

# === Access the Collection ===
try:
    collection = client.get_collection(name=COLLECTION_NAME)
    print(f"[INFO] Connected to collection: {COLLECTION_NAME}")
except Exception as e:
    print(f"[ERROR] Could not load collection '{COLLECTION_NAME}': {e}")
    exit(1)

# === Step 1: Fetch All Records (ids are always included)
print("[INFO] Fetching all records...")
all_items = collection.get(include=["documents", "embeddings", "metadatas"])
ids = all_items["ids"]
total = len(ids)
print(f"[INFO] Fetched {total} records.")

if total == 0:
    print("[WARN] No records to reindex. Exiting.")
    exit(0)

# === Step 2: Delete and Re-Add All Records ===
try:
    print("[INFO] Deleting records to refresh index...")
    collection.delete(ids=ids)

    print("[INFO] Re-adding records to rebuild index...")
    collection.add(
        documents=all_items["documents"],
        embeddings=all_items["embeddings"],
        metadatas=all_items["metadatas"],
        ids=ids
    )

    print("[SUCCESS] Index successfully rebuilt for collection 'stock_recommendations'.")
except Exception as e:
    print(f"[ERROR] Failed to rebuild index: {e}")
