"""
RAGAS Evaluation Script for Mortgage RAG Pipeline.

Usage:
    python -m tests.evaluation.evaluate

Loads golden dataset, runs RAG pipeline, evaluates with RAGAS metrics.
Saves report to docs/eval_report.md
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision
from datasets import Dataset

from backend.services import query_engine, vectorstore


GOLDEN_DIR = Path("tests/evaluation")
REPORT_DIR = Path("docs")


def load_golden_datasets() -> list[dict]:
    """Load all golden_set_*.json files from tests/evaluation/."""
    questions = []
    for f in GOLDEN_DIR.glob("golden_set_*.json"):
        with open(f) as fh:
            data = json.load(fh)
            questions.extend(data)
    for f in GOLDEN_DIR.glob("*_golden_set.json"):
        with open(f) as fh:
            data = json.load(fh)
            questions.extend(data)
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
    """Run RAG on each question and build RAGAS dataset."""
    data = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": [],
    }

    for q in questions:
        if q.get("answerability") == "FALSE":
            continue

        question = q["question"]
        ground_truth = q["expected_answer"]
        print(f"  Running: {question[:60]}...")

        rag_result = run_rag(question)

        data["question"].append(question)
        data["answer"].append(rag_result["answer"])
        data["contexts"].append(rag_result["contexts"])
        data["ground_truth"].append(ground_truth)

    return Dataset.from_dict(data)


def run_evaluation():
    """Main evaluation pipeline."""
    print("=" * 60)
    print("Mortgage RAG — RAGAS Evaluation")
    print("=" * 60)

    # Load golden datasets
    print("\n[1/4] Loading golden datasets...")
    questions = load_golden_datasets()
    total = len(questions)
    answerable = sum(1 for q in questions if q.get("answerability") != "FALSE")
    print(f"  Total questions: {total}")
    print(f"  Answerable (for RAGAS): {answerable}")
    print(f"  Unanswerable (refusal test): {total - answerable}")

    # Run RAG pipeline
    print("\n[2/4] Running RAG pipeline on answerable questions...")
    dataset = build_dataset(questions)
    print(f"  Collected {len(dataset)} question-answer pairs")

    if len(dataset) == 0:
        print("\n  No answerable questions found. Check golden dataset format.")
        return

    # Run RAGAS evaluation
    print("\n[3/4] Running RAGAS evaluation...")
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

    # Check targets
    print("\n[4/4] Checking targets...")
    targets = {"faithfulness": 0.8, "answer_relevancy": 0.75, "context_precision": 0.7}
    all_pass = True
    for metric, target in targets.items():
        passed = scores[metric] >= target
        status = "PASS" if passed else "FAIL"
        print(f"  {metric}: {scores[metric]:.3f} >= {target} → {status}")
        if not passed:
            all_pass = False

    # Save report
    save_report(scores, targets, all_pass, questions, dataset)

    print(f"\n{'=' * 60}")
    print(f"Result: {'ALL TARGETS MET' if all_pass else 'SOME TARGETS MISSED'}")
    print(f"Report saved to docs/eval_report.md")
    print(f"{'=' * 60}")


def save_report(scores: dict, targets: dict, all_pass: bool, questions: list, dataset):
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
        f"**Total Questions:** {total}",
        f"**Answerable:** {answerable}",
        f"**Unanswerable (refusal test):** {unanswerable}",
        "",
        "## RAGAS Scores",
        "",
        "| Metric | Score | Target | Status |",
        "|--------|-------|--------|--------|",
    ]

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
