# retriever.py — queries the ChromaDB vector store for relevant chunks

from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VECTORSTORE_PATH = str(PROJECT_ROOT / "data" / "vectorstore")

def get_retriever():
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )
    vectorstore = Chroma(
        persist_directory=VECTORSTORE_PATH,
        embedding_function=embeddings
    )
    return vectorstore.as_retriever(search_kwargs={"k": 5})

def retrieve(query: str) -> str:
    """Combine goal-specific NAV matches with curated fund guidance passages.

    A query such as "retirement in ten years" often retrieves AMFI NAV rows but
    misses the separate category guidance file. A second, fixed semantic query
    retrieves that guidance so the analyst has both scheme records and context.
    """
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
    queries = [query, *goal_queries,
               "MUTUAL FUND KNOWLEDGE BASE GOAL BASED RECOMMENDATIONS categories examples time horizon risk"]
    seen = set()
    passages = []
    for search_query in queries:
        for doc in retriever.invoke(search_query):
            content = doc.page_content.strip()
            if not content or content in seen:
                continue
            seen.add(content)
            source = doc.metadata.get("source", "local knowledge base")
            passages.append(f"[Source: {Path(source).name}]\n{content}")
    context = "\n\n--- Retrieved passage ---\n\n".join(passages)
    return context or "No relevant passages were found in the local knowledge base."
