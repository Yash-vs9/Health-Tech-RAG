"""
RAGAS Evaluation Script for Mortgage RAG Pipeline.

Usage:
    python -m tests.evaluation.evaluate

Structure:
    tests/evaluation/
    ├── documents/        ← Upload PDFs/DOCXs here (mortgage docs to ingest)
    ├── golden_datasets/  ← Golden dataset JSONs from team members
    └── evaluate.py       ← This script

Flow:
    1. Ingest all documents from documents/
    2. Load all golden datasets from golden_datasets/
    3. Run RAG pipeline on each question
    4. Evaluate with RAGAS metrics
    5. Save report to docs/eval_report.md
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from ragas import evaluate
from ragas.metrics.collections import faithfulness, answer_relevancy, context_precision
from datasets import Dataset

from backend.services import ingestion, query_engine, vectorstore

RATE_LIMIT_DELAY = 7  # seconds between LLM calls (free tier: ~10 req/min)


EVAL_DIR = Path("tests/evaluation")
DOCS_DIR = EVAL_DIR / "documents"
GOLDEN_DIR = EVAL_DIR / "golden_datasets"
REPORT_DIR = Path("docs")


def ingest_documents():
    """Ingest all PDFs and DOCXs from documents/ folder."""
    print("\n[1/5] Ingesting documents from tests/evaluation/documents/...")

    files = list(DOCS_DIR.glob("*.pdf")) + list(DOCS_DIR.glob("*.docx"))
    if not files:
        print("  WARNING: No PDF or DOCX files found in documents/")
        print("  Upload mortgage documents to: tests/evaluation/documents/")
        return []

    ingested = []
    for f in files:
        print(f"  Ingesting: {f.name}")
        with open(f, "rb") as fh:
            file_bytes = fh.read()
        result = ingestion.ingest_document(file_bytes=file_bytes, filename=f.name)
        ingested.append(result)
        print(f"    → doc_id: {result['doc_id']}, chunks: {result['num_chunks']}")

    print(f"  Total: {len(ingested)} documents ingested")
    return ingested


def normalize_question(raw: dict) -> dict:
    """Normalize different golden dataset formats into a common schema."""
    q = (raw.get("question") or raw.get("query") or raw.get("Query")
         or raw.get("Question") or "")
    a = (raw.get("expected_answer") or raw.get("ground_truth_answer")
         or raw.get("Ground Truth Answer") or raw.get("expectedanswer")
         or raw.get("reference_answer_short") or raw.get("expected_answer_detailed")
         or raw.get("answer") or "")
    answerability = raw.get("answerability", "TRUE")
    if answerability is True:
        answerability = "TRUE"
    elif answerability is False:
        answerability = "FALSE"
    elif isinstance(answerability, str) and answerability.upper() in ("TRUE", "FALSE"):
        answerability = answerability.upper()
    else:
        answerability = "TRUE"
    return {
        "question": q,
        "expected_answer": a,
        "answerability": str(answerability),
        "question_type": (raw.get("question_type") or raw.get("Question Type")
                          or raw.get("category") or raw.get("tasktype") or ""),
        "source_doc": (raw.get("source_doc") or raw.get("Source Passage (Context)")
                       or raw.get("source_passage") or ""),
    }


def load_golden_datasets() -> list[dict]:
    """Load all golden dataset JSONs from golden_datasets/ folder."""
    print("\n[2/5] Loading golden datasets from tests/evaluation/golden_datasets/...")

    questions = []
    files = list(GOLDEN_DIR.glob("*.json"))
    if not files:
        print("  WARNING: No golden dataset JSON files found")
        return []

    for f in files:
        with open(f) as fh:
            data = json.load(fh)

            # Handle dict format with various keys
            if isinstance(data, dict):
                if "entries" in data:
                    data = data["entries"]
                elif "golden_dataset" in data:
                    data = data["golden_dataset"]
                else:
                    data = [data]

            if not isinstance(data, list):
                continue

            count = 0
            for item in data:
                if not isinstance(item, dict):
                    continue
                normalized = normalize_question(item)
                if normalized["question"]:
                    questions.append(normalized)
                    count += 1

            print(f"  Loaded: {f.name} ({count} questions)")

    print(f"  Total: {len(questions)} questions")
    return questions


def run_rag(question: str) -> dict:
    """Run the RAG pipeline and return answer + contexts."""
    result = query_engine.query_rag(question=question, doc_ids=None)
    contexts = [s["content"] for s in result["sources"]]
    return {
        "answer": result["answer"],
        "contexts": contexts,
    }


def build_dataset(questions: list[dict]) -> Dataset:
    """Run RAG on each answerable question and build RAGAS dataset."""
    print("\n[3/5] Running RAG pipeline on answerable questions...")

    data = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": [],
    }

    answerable = [q for q in questions if q.get("answerability") != "FALSE"]
    skipped = len(questions) - len(answerable)

    for i, q in enumerate(answerable):
        question = q["question"]
        ground_truth = q["expected_answer"]
        print(f"  [{i+1}/{len(answerable)}] Q: {question[:70]}...")

        rag_result = run_rag(question)

        data["question"].append(question)
        data["answer"].append(rag_result["answer"])
        data["contexts"].append(rag_result["contexts"])
        data["ground_truth"].append(ground_truth)

        if i < len(answerable) - 1:
            print(f"    waiting {RATE_LIMIT_DELAY}s (rate limit)...")
            time.sleep(RATE_LIMIT_DELAY)

    print(f"  Processed: {len(answerable)} answerable, skipped: {skipped} unanswerable")
    return Dataset.from_dict(data)


def run_evaluation():
    """Main evaluation pipeline."""
    print("=" * 60)
    print("Mortgage RAG — RAGAS Evaluation")
    print("=" * 60)

    # Step 1: Ingest documents
    ingested = ingest_documents()

    # Step 2: Load golden datasets
    questions = load_golden_datasets()

    if not questions:
        print("\nNo golden datasets found. Add JSON files to:")
        print("  tests/evaluation/golden_datasets/")
        return

    # Step 3: Build dataset by running RAG
    dataset = build_dataset(questions)

    if len(dataset) == 0:
        print("\nNo answerable questions to evaluate.")
        return

    # Step 4: Run RAGAS evaluation
    print("\n[4/5] Running RAGAS evaluation...")
    results = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision],
    )

    scores = {
        "faithfulness": results["faithfulness"],
        "answer_relevancy": results["answer_relevancy"],
        "context_precision": results["context_precision"],
    }

    print(f"\n  Faithfulness:      {scores['faithfulness']:.3f}")
    print(f"  Answer Relevancy:  {scores['answer_relevancy']:.3f}")
    print(f"  Context Precision: {scores['context_precision']:.3f}")

    # Step 5: Check targets and save report
    print("\n[5/5] Checking targets...")
    targets = {"faithfulness": 0.8, "answer_relevancy": 0.75, "context_precision": 0.7}
    all_pass = True
    for metric, target in targets.items():
        passed = scores[metric] >= target
        status = "PASS" if passed else "FAIL"
        print(f"  {metric}: {scores[metric]:.3f} >= {target} → {status}")
        if not passed:
            all_pass = False

    save_report(scores, targets, all_pass, questions, dataset, ingested)

    print(f"\n{'=' * 60}")
    print(f"Result: {'ALL TARGETS MET' if all_pass else 'SOME TARGETS MISSED'}")
    print(f"Report saved to docs/eval_report.md")
    print(f"{'=' * 60}")


def save_report(scores, targets, all_pass, questions, dataset, ingested):
    """Save evaluation report to docs/eval_report.md."""
    REPORT_DIR.mkdir(exist_ok=True)
    report_path = REPORT_DIR / "eval_report.md"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(questions)
    answerable = len(dataset)
    unanswerable = total - answerable

    lines = [
        "# Mortgage RAG — Evaluation Report",
        "",
        f"**Date:** {timestamp}",
        "",
        "## Ingested Documents",
        "",
    ]

    if ingested:
        for doc in ingested:
            lines.append(f"- **{doc['filename']}** — {doc['num_chunks']} chunks (ID: `{doc['doc_id']}`)")
    else:
        lines.append("- No documents were ingested")

    lines.extend([
        "",
        "## Dataset Summary",
        "",
        f"- **Total questions:** {total}",
        f"- **Answerable (evaluated):** {answerable}",
        f"- **Unanswerable (refusal test):** {unanswerable}",
        "",
        "## RAGAS Scores",
        "",
        "| Metric | Score | Target | Status |",
        "|--------|-------|--------|--------|",
    ])

    for metric in ["faithfulness", "answer_relevancy", "context_precision"]:
        score = scores[metric]
        target = targets[metric]
        status = "PASS" if score >= target else "FAIL"
        lines.append(f"| {metric} | {score:.3f} | {target} | {status} |")

    lines.extend([
        "",
        f"**Overall:** {'ALL TARGETS MET' if all_pass else 'SOME TARGETS MISSED'}",
        "",
        "## Per-Question Results",
        "",
        "| # | Question | Answer (truncated) |",
        "|---|----------|-------------------|",
    ])

    for i, q in enumerate(dataset["question"]):
        ans = dataset["answer"][i][:80] + "..." if len(dataset["answer"][i]) > 80 else dataset["answer"][i]
        lines.append(f"| {i+1} | {q} | {ans} |")

    lines.extend([
        "",
        "---",
        "*Generated by RAGAS evaluation script*",
    ])

    with open(report_path, "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    run_evaluation()
