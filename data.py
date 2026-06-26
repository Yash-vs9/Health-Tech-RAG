# data.py

class Chunk:
    def __init__(self, content, metadata):
        self.page_content = content
        self.metadata = metadata


def get_chunks():
    return [
        Chunk(
            "Diabetes is a chronic disease affecting blood sugar.",
            {"source": "doc1.pdf", "page_num": 1, "section": "intro", "doc_type": "medical"}
        ),
        Chunk(
            "Common symptoms include thirst and frequent urination.",
            {"source": "doc1.pdf", "page_num": 2, "section": "symptoms", "doc_type": "medical"}
        ),
        Chunk(
            "Treatment includes insulin and diet control.",
            {"source": "doc1.pdf", "page_num": 3, "section": "treatment", "doc_type": "medical"}
        )
    ]