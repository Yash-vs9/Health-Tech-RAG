import os
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain.memory import ConversationBufferMemory
from . import vectorstore

_llm = None
_qa_chain = None

SYSTEM_PROMPT = """You are a health information assistant.
Answer only from the provided medical documents.
Always cite the source document and page number.
Think step by step before answering.
If the answer is not found in the provided context,
respond with: 'I don't have that information in the provided documents.'
Do not make up medical information.
Do not provide personal medical advice.

Context:
{context}

Question: {question}
Answer:"""


def get_llm():
    global _llm
    if _llm is None:
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))
        _llm = Ollama(model="llama3.2", temperature=temperature)
    return _llm


def get_qa_chain(retriever):
    global _qa_chain
    if _qa_chain is None:
        llm = get_llm()
        prompt = PromptTemplate(template=SYSTEM_PROMPT, input_variables=["context", "question"])
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        _qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            return_source_documents=True,
            memory=memory,
            chain_type_kwargs={"prompt": prompt},
        )
    return _qa_chain


def query_rag(question: str, doc_ids: list[str] | None = None) -> dict:
    results = vectorstore.query_documents(query_text=question, n_results=5, doc_ids=doc_ids or None)

    if not results["documents"][0]:
        return {
            "answer": "I don't have that information in the provided documents.",
            "sources": [],
        }

    sources = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        sources.append({
            "content": doc,
            "metadata": meta,
            "distance": dist,
        })

    context = "\n\n".join(results["documents"][0])
    llm = get_llm()
    prompt = PromptTemplate(template=SYSTEM_PROMPT, input_variables=["context", "question"])
    response = prompt.format(context=context, question=question)
    answer = llm.invoke(response)

    return {
        "answer": answer,
        "sources": sources,
    }
