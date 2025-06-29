import chromadb
from chromadb.config import Settings

client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory="./chroma"))

# Drop the collection by name
client.delete_collection(name="marketwatch")

print("Collection 'marketwatch' deleted.")
