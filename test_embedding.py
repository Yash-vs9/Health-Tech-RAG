import os
from dotenv import load_dotenv
from src.rag.embeddings import load_embeddings

load_dotenv()

def test_pipeline():
    print("Testing Hugging Face connection...")
    try:
        
        embed_model = load_embeddings()
        
        test_text = "Patient presenting with mild symptoms of seasonal allergies."
        vector = embed_model.embed_query(test_text)
        
        print("\n Success! Connection established.")
        print(f"Embedding vector generated successfully.")
        print(f"Vector dimensions (length): {len(vector)}")
        print(f"First 5 numbers of the vector: {vector[:5]}")
        
    except Exception as e:
        print(f"\n Error encountered: {e}")

if __name__ == "__main__":
    test_pipeline()