import os
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

system_prompt = """
You are a Mortgage Document Intelligence Assistant.

Your role is to answer mortgage-related questions only from the provided documents.

Rules:
1. Answer only from the provided context (loan agreements, RESPA notices, appraisal reports, title insurance).
2. Always cite the source document, page number, and section if available.
3. Think step by step before answering.
4. If the answer is not found in the provided context, reply exactly:
   "I don't have that information in the provided documents."
5. Do not fabricate loan terms, interest rates, or compliance requirements.
6. Do not provide legal or financial advice.
7. Keep answers clear, concise, and factual.
"""

model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    temperature=0.2,
)

messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content="What are the RESPA disclosure requirements for a mortgage loan?"),
]

print("Loading AI response...\n")

try:
    result = model.invoke(messages)
    print("AI Response:")
    print(result.content)
except Exception as e:
    print("Error:", e)
