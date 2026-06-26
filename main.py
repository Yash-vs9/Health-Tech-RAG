import os
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables
load_dotenv()

# Health System Prompt
system_prompt = """
You are a Health Information Assistant.

Your role is to answer health-related questions only from the provided medical documents.

Rules:
1. Answer only from the provided context.
2. Always cite the source document and page number if available.
3. Think step by step before answering.
4. If the answer is not found in the provided context, reply exactly:
   "I don't have that information in the provided documents."
5. Do not make up medical facts.
6. Do not provide personal medical advice, diagnosis, or treatment.
7. Keep answers clear, concise, and factual.
"""

# Gemini Model
model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    temperature=0.2
)

# User Question
messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content="What is diabetes?")
]

print("Loading AI response...\n")

try:
    result = model.invoke(messages)
    print("AI Response:")
    print(result.content)
except Exception as e:
    print("Error:", e)