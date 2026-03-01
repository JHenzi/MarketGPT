import os
from typing import List
from fastmcp import FastMCP
from neo4j import GraphDatabase
import instructor
from openai import OpenAI
from models import MarketSignal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("MarketGPT-KG")

# Neo4j connection details
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Initialize LLM client for extraction
# Using OpenAI as a fallback if API key is in environment
try:
    client = instructor.from_openai(OpenAI())
except Exception:
    # If no API key, client won't work but we still expose tools
    client = None

def get_neo4j_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

@mcp.tool()
def ingest_news_article(text: str, url: str) -> str:
    """
    Parses article text into MarketSignal objects and upserts into Neo4j.
    Uses LLM to extract signals and Cypher MERGE to upsert Ticker and Signal nodes.
    """
    if client is None:
        return "Error: OpenAI client not initialized. Check your OPENAI_API_KEY."

    try:
        # 1. Extract signals from text using LLM
        signals: List[MarketSignal] = client.chat.completions.create(
            model="gpt-4o",
            response_model=List[MarketSignal],
            messages=[
                {"role": "system", "content": "Extract financial signals (headwinds/tailwinds) from the provided news article text. For each signal, include ticker, company name, type, summary, impact score, and source info."},
                {"role": "user", "content": f"URL: {url}\nText: {text}"}
            ]
        )

        if not signals:
            return "No signals extracted from the article."

        # 2. Persist to Neo4j
        with get_neo4j_driver() as driver:
            with driver.session() as session:
                for signal in signals:
                    # Cypher query to upsert nodes and relationships
                    # Using MERGE for Signal by creating a deterministic ID based on ticker and summary
                    # For simplicity, here we MERGE based on ticker, type and description to avoid duplicates
                    query = """
                    MERGE (t:Ticker {symbol: $ticker})
                    SET t.company_name = $company_name

                    MERGE (src:Source {url: $source_url})
                    ON CREATE SET src.title = $source_title, src.published_at = timestamp()

                    MERGE (s:Signal {
                        type: $signal_type,
                        description: $description,
                        ticker: $ticker
                    })
                    ON CREATE SET s.impact_score = $impact_score, s.timestamp = timestamp()
                    ON MATCH SET s.impact_score = $impact_score

                    MERGE (t)-[:HAS_SIGNAL]->(s)
                    MERGE (s)-[:PROVENANCE]->(src)
                    """
                    session.run(query,
                        ticker=signal.ticker.upper(),
                        company_name=signal.company_name,
                        source_url=signal.source_info.get("url", url),
                        source_title=signal.source_info.get("title", "Market News"),
                        signal_type=signal.signal_type,
                        description=signal.summary,
                        impact_score=signal.impact_score
                    )

        return f"Successfully ingested {len(signals)} signals."
    except Exception as e:
        return f"Error ingesting news article: {str(e)}"

@mcp.tool()
def query_signals(ticker: str) -> List[dict]:
    """
    Returns all recent headwinds/tailwinds for a specific ticker symbol.
    """
    try:
        with get_neo4j_driver() as driver:
            with driver.session() as session:
                query = """
                MATCH (t:Ticker {symbol: $ticker})-[:HAS_SIGNAL]->(s:Signal)
                RETURN s.type as type, s.description as description, s.impact_score as impact_score, s.timestamp as timestamp
                ORDER BY s.timestamp DESC
                """
                result = session.run(query, ticker=ticker.upper())
                return [record.data() for record in result]
    except Exception as e:
        return [{"error": f"Error querying signals: {str(e)}"}]

@mcp.tool()
def find_connected_impacts(ticker: str) -> List[dict]:
    """
    Finds other companies mentioned in the same news sources to detect contagion or sector-wide trends.
    """
    try:
        with get_neo4j_driver() as driver:
            with driver.session() as session:
                query = """
                MATCH (t:Ticker {symbol: $ticker})-[:HAS_SIGNAL]->(s:Signal)-[:PROVENANCE]->(src:Source)
                MATCH (other_t:Ticker)-[:HAS_SIGNAL]->(other_s:Signal)-[:PROVENANCE]->(src)
                WHERE other_t.symbol <> $ticker
                RETURN DISTINCT other_t.symbol as connected_ticker, other_s.type as signal_type, other_s.description as description
                """
                result = session.run(query, ticker=ticker.upper())
                return [record.data() for record in result]
    except Exception as e:
        return [{"error": f"Error finding connected impacts: {str(e)}"}]

if __name__ == "__main__":
    mcp.run()
