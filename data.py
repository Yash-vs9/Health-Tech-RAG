# data.py

class Chunk:
    def __init__(self, content, metadata):
        self.page_content = content
        self.metadata = metadata


def get_chunks():
    return [
        Chunk(
            "A mortgage is a loan used to purchase a property. The borrower repays the loan through monthly installments over an agreed period.",
            {
                "source": "mortgage_guide.pdf",
                "page_num": 1,
                "section": "introduction",
                "doc_type": "mortgage"
            }
        ),
        Chunk(
            "EMI (Equated Monthly Installment) is the fixed monthly payment made by a borrower to repay both the principal amount and the interest on a home loan.",
            {
                "source": "mortgage_guide.pdf",
                "page_num": 2,
                "section": "emi",
                "doc_type": "mortgage"
            }
        ),
        Chunk(
            "Mortgage eligibility depends on factors such as income, credit score, employment history, existing debts, and the value of the property.",
            {
                "source": "mortgage_guide.pdf",
                "page_num": 3,
                "section": "eligibility",
                "doc_type": "mortgage"
            }
        ),
        Chunk(
            "A fixed-rate mortgage has an interest rate that remains constant throughout the loan tenure, while a floating-rate mortgage has an interest rate that changes based on market conditions.",
            {
                "source": "mortgage_guide.pdf",
                "page_num": 4,
                "section": "interest_rates",
                "doc_type": "mortgage"
            }
        ),
        Chunk(
            "Making additional payments toward the principal amount can reduce the total interest paid and shorten the loan tenure.",
            {
                "source": "mortgage_guide.pdf",
                "page_num": 5,
                "section": "repayment",
                "doc_type": "mortgage"
            }
        )
    ]