import chromadb
from chromadb.config import Settings

# Configure ChromaDB client and collection
client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory="./chroma"))
collection = client.get_or_create_collection(name="marketwatch")


def query_by_ticker(ticker: str, n_results: int = 10):
    print(f"[query_by_ticker] Searching for articles mentioning ticker: {ticker.upper()}")

    results = collection.query(
        query_texts=[ticker.upper()],
        n_results=n_results,
        include=["documents", "metadatas"]
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    if not docs:
        print(f"No articles found for ticker: {ticker}")
        return

    for i, (doc, meta) in enumerate(zip(docs, metas), 1):
        title = meta.get("title", "No title")
        link = meta.get("link", "#")
        date = meta.get("published_date", "Unknown")
        print(f"\n{i}. {title} ({date})\n   {link}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Query ChromaDB for articles related to a stock ticker.")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g., NVDA, TSLA, AAPL)")
    parser.add_argument("--n", type=int, default=10, help="Number of results to show (default: 10)")

    args = parser.parse_args()

    query_by_ticker(args.ticker, n_results=args.n)
