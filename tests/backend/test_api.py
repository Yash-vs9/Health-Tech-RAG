from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get('/health')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_query_endpoint_returns_citations() -> None:
    response = client.post(
        '/query',
        json={'question': 'What are the symptoms of diabetes?', 'doc_ids': []},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload['answer']
    assert len(payload['generated_queries']) == 3
    assert len(payload['sources']) >= 1
    assert payload['sources'][0]['doc_id'] == 'who_health_guidelines.pdf'


def test_query_endpoint_refuses_unanswerable_question() -> None:
    response = client.post(
        '/query',
        json={'question': 'What is the capital of France?', 'doc_ids': []},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload['answer'] == "I don't have that information in the provided documents."
    assert payload['sources'] == []
