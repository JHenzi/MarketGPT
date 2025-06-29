import chromadb
from chromadb.config import Settings

# === Configuration ===
CHROMA_DB_PATH = "./chroma"  # Update if different
COLLECTION_NAME = "marketwatch"  # Changed to marketwatch

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

# # === Step 1: Fetch All Records (ids are always included)
# print("[INFO] Fetching all records...")
# all_items = collection.get(include=["documents", "embeddings", "metadatas"])
# ids = all_items["ids"]
# total = len(ids)
# print(f"[INFO] Fetched {total} records.")

# if total == 0:
#     print("[WARN] No records to reindex. Exiting.")
#     exit(0)

# # === Step 2: Delete and Re-Add All Records ===
# try:
#     print("[INFO] Deleting records to refresh index...")
#     collection.delete(ids=ids)

#     print("[INFO] Re-adding records to rebuild index...")
#     collection.add(
#         documents=all_items["documents"],
#         embeddings=all_items["embeddings"],
#         metadatas=all_items["metadatas"],
#         ids=ids
#     )

#     print("[SUCCESS] Index successfully rebuilt for collection 'marketwatch'.")
# except Exception as e:
#     print(f"[ERROR] Failed to rebuild index: {e}")

corrupt_id = 'cb255b3dcc37487bb49e42c0975c7018'

try:
    print(f"[INFO] Deleting corrupt ID: {corrupt_id}")
    collection.delete(ids=[corrupt_id])
except Exception as e:
    print(f"[WARN] Could not delete corrupt ID: {e}")

# Fetch everything except the corrupt ID
all_items = collection.get(include=["documents", "embeddings", "metadatas", "ids"])

# Filter out the corrupt ID
filtered_ids = []
filtered_docs = []
filtered_embeds = []
filtered_metas = []

for i, id_ in enumerate(all_items["ids"]):
    if id_ == corrupt_id:
        continue
    filtered_ids.append(id_)
    filtered_docs.append(all_items["documents"][i])
    filtered_embeds.append(all_items["embeddings"][i])
    filtered_metas.append(all_items["metadatas"][i])

print(f"[INFO] Re-adding {len(filtered_ids)} records without corrupt ID...")
collection.add(
    documents=filtered_docs,
    embeddings=filtered_embeds,
    metadatas=filtered_metas,
    ids=filtered_ids
)
print("[SUCCESS] Rebuild complete without corrupt ID.")
