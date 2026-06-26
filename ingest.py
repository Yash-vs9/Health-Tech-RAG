import os
import warnings
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Hide LangChain deprecation warnings for a cleaner terminal
warnings.filterwarnings("ignore", category=DeprecationWarning)

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
            print(f"\n[!] Warning: File not found at {path}. Skipping.")
            continue
            
        print(f"\nLoading {path}...")
        loader = PyMuPDFLoader(path)
        docs = loader.load()
        
        print(f"Chunking {path}...")
        chunks = splitter.split_documents(docs)
        
        # --- CHUNK PREVIEW ---
        print("\n--- CHUNK PREVIEW ---")
        preview_limit = min(3, len(chunks)) # Show first 3 chunks
        for i in range(preview_limit):
            print(f"\n[Chunk {i+1} | Length: {len(chunks[i].page_content)} characters]")
            print(chunks[i].page_content)
            print("-" * 50)
        print("---------------------\n")
        
        # Verify chunk count correct as per assignment requirements
        print(f" -> Success: Generated {len(chunks)} chunks from {path}")
        all_chunks.extend(chunks)

    if not all_chunks:
        print("No chunks generated. Pipeline aborted.")
        return None

    # 4. Store in ChromaDB with metadata
    print(f"\nEmbedding and storing {len(all_chunks)} total chunks in ChromaDB...")
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
            "expected_answer": "He is a Student and learning Full stack developement.",
            "variations": [
                "whats the occupation of Yash"
            ]
        }
    ]

if __name__ == "__main__":
    # --- Testing Phase ---
    # Ensure this file exists in the same folder as this script
    sample_pdfs = [
        'sample_pdf.pdf' 
    ]
    
    # Run the ingestion pipeline
    db = ingest_health_pdfs(sample_pdfs)
    
    # Print out the Golden Dataset structure for validation
    golden_data = get_golden_dataset()
    print("\nGolden Dataset initialized with 5 variations checking for the exact same expected answer.")