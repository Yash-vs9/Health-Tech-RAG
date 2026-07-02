# main.py

import os
from dotenv import load_dotenv
load_dotenv()

print(os.getenv("MODEL_PROVIDER"))

from data import get_chunks
from db_setup import create_collection

# Step 1: Get chunks
chunks = get_chunks()

# Step 2: Create collection
client, collection = create_collection()
try:
    existing = collection.get()

    if existing["ids"]:
        collection.delete(ids=existing["ids"])
except:
    pass

# Step 3: Store data
collection.add(
    documents=[chunk.page_content for chunk in chunks],
    metadatas=[chunk.metadata for chunk in chunks],
    ids=[f"chunk_{i}" for i in range(len(chunks))]
)



# Step 6: Log stored data
stored = collection.get()

print("\n--- STORED DATA ---")

for i in range(len(stored["ids"])):
    print(f"ID: {stored['ids'][i]}")
    print(f"Metadata: {stored['metadatas'][i]}")
    print(f"Text: {stored['documents'][i]}")
    print("----------------------")



# Step 4: Query
results = collection.query(
    query_texts=["symptoms of diabetes"],
    n_results=5
)




# Step 5: Display results

print("\n--- SEARCH RESULTS ---")

for i in range(len(results['ids'][0])):
    print(f"\nID: {results['ids'][0][i]}")
    print(f"Text: {results['documents'][0][i]}")
    print(f"Metadata: {results['metadatas'][0][i]}")


# Step 7: LLM + Guardrails (NVIDIA)

print("\n--- ASK QUESTION TO LLM ---")





print("\n--- ASK QUESTION TO LLM ---")

print("\n--- ASK QUESTION TO LLM ---")

user_input = input("Enter your medical question: ")

llm_choice = os.getenv("MODEL_PROVIDER")

if llm_choice == "nvidia":
    from guardrails_module.nvidia_guardrails import get_guardrails_response

    response = get_guardrails_response(user_input)

    print("\n--- LLM RESPONSE ---")
    print(response["content"])
else:
    print(f"Unsupported LLM Provider: {llm_choice}")