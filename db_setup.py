import chromadb

def create_collection():
    
    client = chromadb.PersistentClient(path="chroma_db")
    

    collection = client.get_or_create_collection(
        name="health_docs",
        metadata={"hnsw:space": "cosine"}
    )

    return client, collection  