import os
import warnings
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv()

# Hide LangChain deprecation warnings for a cleaner terminal
warnings.filterwarnings("ignore", category=DeprecationWarning)


def ingest_health_pdfs(pdf_paths, persist_dir="./chroma_db"):
    """
    Loads, chunks, embeds, and stores PDFs into a Chroma vector database.
    Embeddings are generated via Hugging Face's hosted Inference API,
    routed through the Scaleway provider, running Qwen3-Embedding-8B.
    Nothing is downloaded or run locally.
    """

    # 1. Initialize the Text Splitter
    # CRITICAL: chunk_overlap is set to 50 to maintain cross-boundary context
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=50,
        separators=['\n\n', '\n', '.', ' ']
    )

    # 2. Initialize Qwen3-Embedding-8B via Hugging Face's Scaleway provider
    print("Connecting to Hugging Face Inference API (Qwen3-Embedding-8B via Scaleway)...")
    HF_TOKEN = os.getenv("HF_TOKEN")
    if not HF_TOKEN:
        print("[!] Warning: HF_TOKEN environment variable is not set.")
        print("    Get a token at https://huggingface.co/settings/tokens")
        print("    and run: export HF_TOKEN=your_token_here")
        print("    (You'll also need Inference Providers billing/credits set up")
        print("     on your HF account, since Scaleway is a paid provider.)")

    embeddings = HuggingFaceEndpointEmbeddings(
        model="Qwen/Qwen3-Embedding-8B",
        task="feature-extraction",
        provider="scaleway",          # the only provider currently serving this 8B model
        huggingfacehub_api_token=HF_TOKEN,
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
        preview_limit = min(3, len(chunks))  # Show first 3 chunks
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
    print(f"\nSending {len(all_chunks)} chunks to Hugging Face API for embedding and storing locally...")
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
                "whats the occupation of Yash",
                "What does Yash do for a living?",
                "Is Yash currently a student or a working professional?",
                "Tell me about Yash's career and educational background.",
                "What field of study or work is Yash involved in?"
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