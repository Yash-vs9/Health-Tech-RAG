from langchain_core.documents import Document

from backend.services.query_engine import MultiQueryService


def test_generate_queries_creates_three_variants() -> None:
    service = MultiQueryService()
    queries = service.generate_queries('What are the symptoms of diabetes?')

    assert len(queries) == 3
    assert queries[0] == 'What are the symptoms of diabetes?'


def test_answer_question_returns_sources() -> None:
    service = MultiQueryService()
    result = service.answer_question('What are the symptoms of diabetes?', [])

    assert 'answer' in result
    assert len(result['generated_queries']) == 3
    assert len(result['sources']) >= 1


def test_retrieve_keeps_multiple_chunks_same_doc() -> None:
    service = MultiQueryService()

    class StubRetriever:
        def invoke(self, _: str):
            return [
                Document(
                    page_content="Early diagnosis helps reduce complications.",
                    metadata={"doc_id": "who_health_guidelines.pdf", "page": 13, "section": "Complications"},
                ),
                Document(
                    page_content="Follow-up care is important after abnormal test results.",
                    metadata={"doc_id": "who_health_guidelines.pdf", "page": 13, "section": "Complications"},
                ),
            ]

    service._multi_query_retriever = StubRetriever()
    generated_queries = service.generate_queries('What complications are noted and how is follow-up handled?')
    sources = service.retrieve(generated_queries, [])

    assert len(sources) == 2
    assert all(source.doc_id == 'who_health_guidelines.pdf' for source in sources)
