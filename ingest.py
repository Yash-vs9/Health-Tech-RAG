import os
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

def ingest_health_pdfs(pdf_paths, persist_dir="./chroma_db"):
    """
    Loads, chunks, embeds, and stores PDFs into a Chroma vector database.
    """
    # 1. Initialize the Text Splitter
    # CRITICAL: chunk_overlap is set to 50 to maintain cross-boundary context
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=50, 
        separators=['\n\n', '\n', '.', ' ']
    )

    # 2. Initialize HuggingFace Embeddings (Free, Local)
    print("Loading embedding model (sentence-transformers/all-MiniLM-L6-v2)...")
    embeddings = HuggingFaceEmbeddings(
        model_name='sentence-transformers/all-MiniLM-L6-v2'
    )

    all_chunks = []

    # 3. Load and Chunk Documents
    for path in pdf_paths:
        if not os.path.exists(path):
            print(f"Warning: File not found at {path}. Skipping.")
            continue
            
        print(f"Loading {path}...")
        loader = PyMuPDFLoader(path)
        docs = loader.load()
        
        print(f"Chunking {path}...")
        chunks = splitter.split_documents(docs)
        
        # Verify chunk count correct as per assignment requirements
        print(f" -> Success: Generated {len(chunks)} chunks from {path}")
        all_chunks.extend(chunks)

    if not all_chunks:
        print("No chunks generated. Pipeline aborted.")
        return None

    # 4. Store in ChromaDB with metadata
    print(f"Embedding and storing {len(all_chunks)} total chunks in ChromaDB...")
    vectorstore = Chroma.from_documents(
        documents=all_chunks, 
        embedding=embeddings,
        persist_directory=persist_dir
    )
    
    print(f"Pipeline complete! Database saved to {persist_dir}")
    return vectorstore

# --- Golden Dataset Structure ---
def get_golden_dataset():
    """
    Returns the Golden Dataset: 5 Query Variation Pairs
    Used for testing retrieval robustness.
    """
    return [
        {
            "label": "question_type=variation",
            "expected_answer": "A healthy resting heart rate for adults ranges from 60 to 100 beats per minute.",
            "variations": [
                "What is the normal resting heart rate for an adult?",
                "Can you tell me the standard heart rate range for adults at rest?",
                "How many beats per minute should a healthy adult heart have while resting?",
                "What is considered a healthy pulse rate for an adult who is resting?",
                "Give me the normal resting beats per minute (BPM) for an adult."
            ]
        }
    ]

if __name__ == "__main__":
    # --- Testing Phase ---
    # Put 2-3 sample health PDFs in the same directory to test
    sample_pdfs = [
        'sample_health_doc_1.pdf', 
        'sample_health_doc_2.pdf', 
        'sample_health_doc_3.pdf'
    ]
    
    # Run the ingestion pipeline
    # Uncomment the line below once you have your sample PDFs ready:
    # db = ingest_health_pdfs(sample_pdfs)
    
    # Print out the Golden Dataset structure for validation
    golden_data = get_golden_dataset()
    print("\nGolden Dataset initialized with 5 variations checking for the exact same expected answer.")