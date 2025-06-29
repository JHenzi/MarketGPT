# scrape_article.py
import trafilatura
import sys

def fetch_article_trafilatura(url):
    downloaded = trafilatura.fetch_url(url)
    if downloaded:
        result = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
        return result
    return "Failed to extract article."

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scrape_article.py <URL>")
    else:
        url = sys.argv[1]
        print(fetch_article_trafilatura(url))
