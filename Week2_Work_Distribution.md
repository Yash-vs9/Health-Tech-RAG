

AIforAll Global — International AI Internship
Week 2: Build the Core System
Health Tech RAG Chatbot — Team Work Distribution
## June 2026
## Project Overview
Project: GenAI-based AI Chatbot for Document Q&A (Health Tech Domain)
Week: 2 of 5 — Build the Core System
Goal: Build end-to-end RAG pipeline with LangChain, ChromaDB, FastAPI backend, and React/Streamlit
frontend.
Total Team Members: 10  |  Golden Dataset Target: 50 Q&A pairs (5 per member)
## Team Dependency Order
Tasks must be completed in this order to avoid blockers:
Aakanksha (Docs) → Soojal (Store) → Yash (Embed) → Aryan (Retriever) → Tejasva (Multi-
query) → ~...... (UI) → Lakshya (API) → Nua (Evaluate) → ~   (Prompts)
## Quick Summary
MemberVoted SkillsCode TaskGolden Dataset
AryanPython + RAGLangChain RetrievalQA +
ChromaDB retriever
5 multi-hop pairs
TejasvaPython + RAG +
## React
Multi-query retrieval + UI bridge5 citation-grounded pairs
YashPython + RAG +
## React
PDF ingestion pipeline5 query variation pairs
LakshyaPython + RAG +
FastAPI
FastAPI 3 endpoints5 edge case pairs
IshaPython + ReactEmbedding model testing + chunk 5 factual direct pairs

MemberVoted SkillsCode TaskGolden Dataset
tuning
AakankshaReactDocument cleaning + chunking5 factual direct pairs
SoojalPythonChromaDB collection + metadata5 simple direct pairs
NuaPythonRAGAS evaluation setup5 simple direct pairs
~PythonSystem prompt engineering5 simple direct pairs
~......ReactStreamlit/React UI components5 simple direct pairs
## Detailed Task Breakdown
## 1. Aryan
Voted: Python + RAG concepts
Why this assignment: Voted for both Python and RAG concepts. Assigned retriever configuration
— sits between Python scripting and RAG knowledge. Not too deep architecturally, but critical for
pipeline to work.
Code Task: LangChain RetrievalQA + ChromaDB Retriever Config
•Install dependencies: pip install chromadb langchain
•Setup LangChain RetrievalQA chain with ChromaDB vectorstore
•Configure retriever with k=5 and score_threshold=0.7
•Add ConversationBufferMemory for multi-turn conversation
•Enable source_documents=True to surface citations in every response
•Test retriever returns correct chunks for 3 sample health queries
from langchain.chains import RetrievalQA
from langchain.memory import ConversationBufferMemory
retriever = vectorstore.as_retriever(
search_kwargs={'k': 5, 'score_threshold': 0.7}
## )
memory = ConversationBufferMemory(
memory_key='chat_history',
return_messages=True
## )
qa_chain = RetrievalQA.from_chain_type(
llm=llm,
retriever=retriever,
return_source_documents=True,
memory=memory
## )
Golden Dataset: 5 Multi-hop Reasoning Q&A Pairs

Questions that require information from 2 or more document chunks to answer correctly. Label each:
question_type=multi_hop, hallucination_risk=MEDIUM
## 2. Tejasva Chadha
Voted: Python + RAG concepts + Frontend (React)
Why this assignment: Only member who voted all three skills — Python, RAG, and React. Best
suited to bridge backend retrieval with frontend. Multi-query retrieval needs RAG understanding AND
ability to pass output to React components.
Code Task: Multi-Query Retrieval + React UI Bridge
•Implement MultiQueryRetriever from LangChain
•Generates 3 query variants from 1 user question → merges results
•Connect retriever output to React frontend via API response
•Build React chat interface component with message bubbles
•Build source citation display component below each answer
•Test: same question 3 ways → verify merged results better than single query
from langchain.retrievers import MultiQueryRetriever
retriever = MultiQueryRetriever.from_llm(
retriever=vectorstore.as_retriever(),
llm=llm
## )
# React component (JSX)
const ChatMessage = ({ message, sources }) => (
<div className='message'>
## <p>{message}</p>
<CitationPanel sources={sources} />
## </div>
## );
Golden Dataset: 5 Citation-Grounded Q&A Pairs
Every answer must cite exact document section and page number. Label: answerability=TRUE, source_doc +
source_page mandatory.
## 3. Yash
Voted: Python + RAG concepts + Frontend (React)
Why this assignment: Voted Python + RAG + React. Assigned ingestion pipeline as it is the most
Python-heavy RAG task. React file upload complements the ingestion work he owns on backend
side.
Code Task: Full PDF Ingestion Pipeline (Load → Chunk → Embed → Store)

•Load health PDFs using PyMuPDFLoader
•Chunk with RecursiveCharacterTextSplitter: chunk_size=512, chunk_overlap=50
•NEVER set chunk_overlap=0 — kills cross-boundary context
•Embed using sentence-transformers/all-MiniLM-L6-v2 (free, local)
•Store chunks in ChromaDB with full metadata
•Build React file upload component with drag-and-drop
•Build ingestion progress bar in React
•Test with 2-3 sample health PDFs — verify chunk count correct
from langchain.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
loader = PyMuPDFLoader('health_doc.pdf')
docs = loader.load()
splitter = RecursiveCharacterTextSplitter(
chunk_size=512,
chunk_overlap=50,   # Never set to 0
separators=['\n\n', '\n', '.', ' ']
## )
chunks = splitter.split_documents(docs)
embeddings = HuggingFaceEmbeddings(
model_name='sentence-transformers/all-MiniLM-L6-v2'
## )
vectorstore = Chroma.from_documents(chunks, embeddings)
## Golden Dataset: 5 Query Variation Pairs
Same question phrased 5 different ways. All 5 must return same expected_answer. Tests retrieval robustness.
Label: question_type=variation
## 4. Lakshya
Voted: Python + RAG concepts + Backend (FastAPI)
Why this assignment: Only member who voted FastAPI. Clear ownership — nobody else has
backend knowledge. Also voted RAG so understands what the API needs to serve. Natural fit for API
layer connecting RAG pipeline to frontend.
Code Task: FastAPI Backend — 3 Core Endpoints
•POST /ingest — accept health PDF upload → parse → embed → return doc_id
•POST /query — accept question + doc_ids → run RAG → return answer + sources
•GET /health — health check endpoint for deployment monitoring
•Add Pydantic schemas for all request/response validation
•Run: uvicorn main:app --reload --port 8000
•Test all 3 endpoints via Swagger UI at localhost:8000/docs
from fastapi import FastAPI, UploadFile

from pydantic import BaseModel
from typing import List
app = FastAPI(title='Health RAG API')
class QueryRequest(BaseModel):
question: str
doc_ids: List[str]
class QueryResponse(BaseModel):
answer: str
sources: List[dict]
## @app.post('/ingest')
async def ingest(file: UploadFile):
# parse PDF → chunk → embed → store → return doc_id
pass
@app.post('/query', response_model=QueryResponse)
async def query(request: QueryRequest):
# RAG retriever → answer + sources
pass
## @app.get('/health')
async def health_check():
return {'status': 'ok'}
## Golden Dataset: 5 Edge Case / Unanswerable Pairs
Questions that cannot be answered from health documents. Label: answerability=FALSE,
hallucination_risk=HIGH. Tests system refusal behavior.
## 5. Isha Bhargava
Voted: Python + Frontend (React)
Why this assignment: Voted Python and React but NOT RAG concepts. Assigned embedding
testing because it is Python-heavy but does not require deep RAG architecture knowledge — just
running models and comparing results. React dashboard uses frontend skills.
## Code Task: Embedding Model Testing + Chunk Size Tuning
•Test 2 embedding models: MiniLM-L6-v2 vs BAAI/bge-large-en-v1.5
•Run same 10 test health queries on both models
•Test 3 chunk sizes: 256 / 512 / 1024 tokens
•Record: retrieval accuracy, response speed, chunk relevance for each
•CRITICAL: use same model for indexing AND querying — never mix
•Build React results dashboard showing RAGAS scores and benchmarks
•Document findings in docs/embedding_comparison.md
# Option 1 — Free, fast, good quality
from langchain.embeddings import HuggingFaceEmbeddings
model1 = HuggingFaceEmbeddings(
model_name='sentence-transformers/all-MiniLM-L6-v2'

## )
# Option 2 — Better quality for medical text
model2 = HuggingFaceEmbeddings(
model_name='BAAI/bge-large-en-v1.5'
## )
# Test both with same 10 queries
# Record: top-k results, relevance score, latency
# Choose best → use for ALL indexing and querying
Golden Dataset: 5 Factual Direct Q&A Pairs
Single-chunk answerable questions. No cross-document reasoning needed. Label: question_type=factual,
answerability=TRUE, hallucination_risk=LOW
## 6. Aakanksha
Voted: Frontend (React)
Why this assignment: Voted only React — no RAG or backend knowledge. Assigned pure frontend
tasks plus document cleaning which is straightforward file handling. No deep RAG architecture
involvement required.
Code Task: Document Cleaning + Chunking + React Upload UI
•Collect 3-5 health domain PDFs (WHO guidelines, medical reports)
•Clean text: remove headers/footers, fix encoding, normalize whitespace
•Apply chunking with mandatory overlap (chunk_overlap=50, never 0)
•Add metadata to every chunk: source, page_num, section, doc_type
•Deliver clean chunks to Soojal for ChromaDB storage
•Build React document upload panel with drag-and-drop
•Build React chat history component with user/assistant message bubbles
# Chunking with metadata
splitter = RecursiveCharacterTextSplitter(
chunk_size=512,
chunk_overlap=50
## )
chunks = splitter.split_documents(docs)
# Add metadata to every chunk
for chunk in chunks:
chunk.metadata.update({
## 'source': 'who_guidelines.pdf',
'page': chunk.metadata.get('page', 0),
'section': 'Nutrition',
## 'doc_type': 'guideline'
## })
Golden Dataset: 5 Factual Direct Q&A Pairs

From different health documents than Isha. Label: question_type=factual, answerability=TRUE,
hallucination_risk=LOW
## 7. Soojal
Voted: Python only
Why this assignment: Voted only Python — no RAG or frontend knowledge. ChromaDB setup is
essentially Python scripting with a database. Does not require deep RAG understanding, just correct
API usage and metadata structuring. Perfect Python-only task.
Code Task: ChromaDB Collection Setup + Metadata Schema
•Initialize ChromaDB client and create health_docs collection
•Set cosine similarity as distance metric (hnsw:space = cosine)
•Receive clean chunks from Aakanksha and store with full metadata
•Store: document text + metadata {source, page_num, section, doc_type}
•Test: verify similarity search returns correct top-5 results
•Log chunk IDs and metadata for every stored document
import chromadb
client = chromadb.Client()
collection = client.create_collection(
name='health_docs',
metadata={'hnsw:space': 'cosine'}
## )
# Store chunks from Aakanksha
collection.add(
documents=[chunk.page_content for chunk in chunks],
metadatas=[chunk.metadata for chunk in chunks],
ids=[f'chunk_{i}' for i in range(len(chunks))]
## )
# Test similarity search
results = collection.query(
query_texts=['symptoms of diabetes'],
n_results=5
## )
print(results)
Golden Dataset: 5 Simple Direct Q&A Pairs
Basic questions answerable from a single chunk. No reasoning required. Label: question_type=simple,
answerability=TRUE, hallucination_risk=LOW
## 8. Nua 
Voted: Python only

Why this assignment: Voted only Python. RAGAS evaluation is Python scripting — install library,
load dataset, run evaluate function, save results. No RAG architecture knowledge needed, just
Python comfort. Also responsible for merging all team Q&A pairs.
Code Task: RAGAS Evaluation Setup + Golden Dataset Merge
•Collect all 50 Q&A pairs from all 10 team members
•Merge into single file: tests/evaluation/golden_set.json
•Install RAGAS: pip install ragas
•Run evaluation on 3 metrics: faithfulness, answer_relevancy, context_precision
•Target scores: faithfulness > 0.8, answer_relevancy > 0.75, context_precision > 0.7
•Save results to docs/eval_report.md
from ragas import evaluate
from ragas.metrics import (
faithfulness,
answer_relevancy,
context_precision
## )
from datasets import Dataset
import json
# Load merged golden set
with open('tests/evaluation/golden_set.json') as f:
data = json.load(f)
dataset = Dataset.from_list(data)
results = evaluate(
dataset=dataset,
metrics=[faithfulness, answer_relevancy, context_precision]
## )
print(results)  # Save to eval_report.md
Golden Dataset: 5 Simple Direct Q&A Pairs
Basic health questions from documents. Label: question_type=simple, answerability=TRUE,
hallucination_risk=LOW
- ~   (Unknown)
Voted: Python only
Why this assignment: Voted only Python. Prompt engineering is pure text + Python — writing
system prompts, testing temperature values, saving prompt files. No RAG or frontend knowledge
needed. Directly impacts output quality of the entire system.
Code Task: System Prompt Engineering for Health Domain
•Write health-specific system prompt defining persona and constraints
•Add explicit refusal: 'If answer not in context, say I don't have that information'

•Test temperature=0.0 for factual Q&A, 0.2 for summaries
•Test prompt on 10 sample health questions — identify failure modes
•Fix each failure by adding targeted constraints to prompt
•Version control all prompts in prompts/ directory as .txt files
# prompts/health_system_prompt.txt
You are a health information assistant.
Answer only from the provided medical documents.
Always cite the source document and page number.
Think step by step before answering.
If the answer is not found in the provided context,
respond with: 'I don't have that information in
the provided documents.'
Do not make up medical information.
Do not provide personal medical advice.
Golden Dataset: 5 Simple Direct Q&A Pairs
Basic health questions. Label: question_type=simple, answerability=TRUE, hallucination_risk=LOW
- ~...... (Unknown)
Voted: Frontend (React)
Why this assignment: Voted only React/Frontend. Assigned UI components that require no
backend knowledge. Citations panel, loading states, and error handling are pure React tasks. Axios
API calls are simple fetch requests any React developer can handle.
Code Task: Streamlit/React UI Components
•Build source citations expandable panel showing retrieved chunks per answer
•Build loading states and spinner while RAG pipeline processes query
•Build error handling UI with user-friendly error messages
•Connect frontend to FastAPI backend via axios or fetch
•Handle async streaming responses
•Show loading spinner during processing
# Streamlit version
import streamlit as st
import requests
st.title('Health Document Q&A')
if prompt := st.chat_input('Ask a health question'):
with st.chat_message('user'):
st.write(prompt)
with st.spinner('Thinking...'):
response = requests.post(
## 'http://localhost:8000/query',
json={'question': prompt, 'doc_ids': ['all']}

## ).json()
with st.chat_message('assistant'):
st.write(response['answer'])
with st.expander('Sources'):
st.write(response['sources'])
Golden Dataset: 5 Simple Direct Q&A Pairs
Basic health questions. Label: question_type=simple, answerability=TRUE, hallucination_risk=LOW
Golden Dataset — Shared Format (All Members)
Every member submits exactly 5 Q&A pairs in this format. Nua merges all into golden_set.json.
## {
'question_id': 'Q001',
'question': 'What are symptoms of Type 2 diabetes?',
'expected_answer': 'Common symptoms include...',
## 'source_doc': 'who_health_guidelines.pdf',
## 'source_page': 12,
'question_type': 'factual',   // factual/multi_hop/unanswerable/edge_case/variation
'answerability': 'TRUE',      // TRUE or FALSE
'hallucination_risk': 'LOW'   // LOW / MEDIUM / HIGH
## }
MemberDataset TypeQuestion StyleTarget Count
AryanMulti-hop ReasoningNeeds 2+ chunks to answer5 pairs
TejasvaCitation-GroundedMust cite doc + page5 pairs
YashQuery VariationsSame Q, 5 phrasings5 pairs
LakshyaEdge CasesUnanswerable / ambiguous5 pairs
IshaFactual DirectSingle-chunk answerable5 pairs
AakankshaFactual DirectSingle-chunk answerable5 pairs
SoojalSimple DirectBasic retrieval5 pairs
NuaSimple DirectBasic retrieval5 pairs
~Simple DirectBasic retrieval5 pairs
~......Simple DirectBasic retrieval5 pairs
## Important Notes
•Never mix embedding models — use same model for indexing AND querying
•Always set chunk_overlap=50 — never 0, kills cross-boundary context

•Never hardcode API keys — use .env files with python-dotenv
•Commit code daily to GitHub — no version control = risk
•Test retrieval quality BEFORE building generation on top
•Target RAGAS faithfulness > 0.8 before Week 3
AIforAll Global — Health Tech Team — Week 2 — June 2026