import os
from langchain_huggingface import HuggingFaceEndpointEmbeddings


def load_embeddings() -> HuggingFaceEndpointEmbeddings:
    """
    Initializes the Qwen3 Embedding 8B model via the Hugging Face API.

    Returns:
        HuggingFaceEndpointEmbeddings: The configured embeddings object for LangChain.
    """
    hf_api_token = os.environ.get("HUGGINGFACEHUB_API_TOKEN")

    if not hf_api_token:
        raise ValueError("Please set the HUGGINGFACEHUB_API_TOKEN environment variable.")

    embeddings = HuggingFaceEndpointEmbeddings(
        model="Qwen/Qwen3-Embedding-8B",
        task="feature-extraction",
        huggingfacehub_api_token=hf_api_token,
    )

    return embeddings
