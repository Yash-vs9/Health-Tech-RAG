from langchain_groq import ChatGroq
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain.chains import RetrievalQA
from dotenv import load_dotenv
import os

load_dotenv()

def load_llm():
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model_name="llama-3.3-70b-versatile",
        temperature=0.0
    )

def load_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

def load_vectorstore(persist_dir="data/chroma_db"):
    embeddings = load_embeddings()
    vectorstore = Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings
    )
    return vectorstore

def build_retriever(vectorstore):
    return vectorstore.as_retriever(
        search_kwargs={
            "k": 5,
            "score_threshold": 0.7
        }
    )

def build_qa_chain(retriever):
    llm = load_llm()
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key="result"
    )
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        memory=memory
    )
    return qa_chain

def ask(qa_chain, question: str):
    response = qa_chain.invoke({"query": question})
    answer = response["result"]
    sources = response["source_documents"]

    print(f"\nQuestion: {question}")
    print(f"Answer: {answer}")
    print("\nSources:")
    for i, doc in enumerate(sources):
        print(f"  [{i+1}] {doc.metadata.get('source', 'Unknown')} — Page {doc.metadata.get('page', 'N/A')}")

    return answer, sources
