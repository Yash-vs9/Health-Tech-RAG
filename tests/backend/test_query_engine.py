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
