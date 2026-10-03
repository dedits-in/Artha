import os
from langchain_community.document_loaders import PyPDFLoader, CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

RAW_DATA_PATH = "data/raw"
VECTORSTORE_PATH = "data/vectorstore"

def load_documents():
    docs = []
    for filename in os.listdir(RAW_DATA_PATH):
        filepath = os.path.join(RAW_DATA_PATH, filename)
        if filename.endswith(".pdf"):
            loader = PyPDFLoader(filepath)
            docs.extend(loader.load())
        elif filename.endswith(".csv"):
            loader = CSVLoader(filepath)
            docs.extend(loader.load())
        elif filename.endswith(".txt"):
            from langchain_community.document_loaders import TextLoader
            loader = TextLoader(filepath, encoding="utf-8")
            docs.extend(loader.load())
    print(f"Loaded {len(docs)} documents")
    return docs

def chunk_documents(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(docs)
    print(f"Created {len(chunks)} chunks")
    return chunks

def embed_and_store(chunks):
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=VECTORSTORE_PATH
    )
    print(f"Vector store saved to {VECTORSTORE_PATH}")
    return vectorstore

if __name__ == "__main__":
    docs = load_documents()
    if not docs:
        print("No documents found in data/raw/ — add a PDF or CSV file first.")
    else:
        chunks = chunk_documents(docs)
        embed_and_store(chunks)
        print("Ingestion complete!")