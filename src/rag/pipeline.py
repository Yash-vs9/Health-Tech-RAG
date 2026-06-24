from src.rag.retriever import (
    load_vectorstore,
    build_retriever,
    build_qa_chain,
    ask
)

def run_pipeline(question: str):
    print("Loading vectorstore...")
    vectorstore = load_vectorstore()

    print("Building retriever...")
    retriever = build_retriever(vectorstore)

    print("Building QA chain...")
    qa_chain = build_qa_chain(retriever)

    print("Asking question...")
    answer, sources = ask(qa_chain, question)

    return answer, sources

if __name__ == "__main__":
    questions = [
        "What are the symptoms of Type 2 diabetes?",
        "What is the recommended daily water intake for adults?",
        "What are WHO guidelines for physical activity?"
    ]

    vectorstore = load_vectorstore()
    retriever = build_retriever(vectorstore)
    qa_chain = build_qa_chain(retriever)

    for q in questions:
        ask(qa_chain, q)
        print("-" * 50)