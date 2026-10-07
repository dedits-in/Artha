# retriever.py — queries the ChromaDB vector store for relevant chunks

from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VECTORSTORE_PATH = str(PROJECT_ROOT / "data" / "vectorstore")

# Safety net: raw NAV rows are price snapshots (and include matured schemes),
# so they are never used for planning even if re-ingested by mistake.
SKIP_SOURCES = {"navall.csv"}
PER_QUERY = 3      # passages kept from each search query
MAX_PASSAGES = 18  # overall cap; lower this if Groq complains about input tokens


def get_retriever():
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = Chroma(
        persist_directory=VECTORSTORE_PATH,
        embedding_function=embeddings,
    )
    return vectorstore.as_retriever(search_kwargs={"k": 10})


def retrieve(query: str) -> str:
    """Combine goal-specific matches, curated guidance, and fund detail cards."""
    retriever = get_retriever()
    normalized_query = query.lower()
    goal_queries = []
    goal_hints = [
        (("retire",), "MUTUAL FUND KNOWLEDGE BASE Retirement 10+ years Mid Cap Large Cap ELSS 50:30:20 examples"),
        (("education", "child"), "MUTUAL FUND KNOWLEDGE BASE Child Education 10-15 years Mid Cap Small Cap Large Cap examples"),
        (("tax", "80c"), "MUTUAL FUND KNOWLEDGE BASE Tax Saving ELSS 3 year lock-in examples"),
        (("emergency",), "MUTUAL FUND KNOWLEDGE BASE Emergency Fund Liquid funds short-term debt funds"),
        (("car", "home purchase", "house purchase"), "MUTUAL FUND KNOWLEDGE BASE Car Purchase 3-5 years Hybrid Large Cap examples"),
    ]
    for keywords, hint in goal_hints:
        if any(keyword in normalized_query for keyword in keywords):
            goal_queries.append(hint)
            break
    queries = [
        query,
        *goal_queries,
        "MUTUAL FUND KNOWLEDGE BASE GOAL BASED RECOMMENDATIONS categories examples time horizon risk",
        # One query per bucket so debt and hybrid cards are not crowded out by equity.
        "Fund Name Fund House Scheme Category Debt Scheme Short Duration Corporate Bond Fund",
        "Fund Name Fund House Scheme Category Hybrid Scheme Balanced Advantage Dynamic Asset Allocation",
        "Fund Name Fund House Scheme Category Equity Scheme Large Cap Mid Cap Flexi Cap",
    ]
    seen = set()
    passages = []
    for search_query in queries:
        kept = 0
        for doc in retriever.invoke(search_query):
            source_name = Path(doc.metadata.get("source", "local knowledge base")).name
            if source_name.lower() in SKIP_SOURCES:
                continue
            content = doc.page_content.strip()
            if not content or content in seen:
                continue
            seen.add(content)
            passages.append(f"[Source: {source_name}]\n{content}")
            kept += 1
            if kept >= PER_QUERY or len(passages) >= MAX_PASSAGES:
                break
        if len(passages) >= MAX_PASSAGES:
            break
    context = "\n\n--- Retrieved passage ---\n\n".join(passages)
    return context or "No relevant passages were found in the local knowledge base."