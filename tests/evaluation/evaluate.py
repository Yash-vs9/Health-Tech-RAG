"""
RAGAS Evaluation Script for Mortgage RAG Pipeline.

Usage:
    # Full run (ingestion + RAG + evaluation)
    python -m tests.evaluation.evaluate

    # Resume from step 4 only (skips ingestion and RAG pipeline)
    python -m tests.evaluation.evaluate --resume

Structure:
    tests/evaluation/
    ├── documents/        ← Upload PDFs/DOCXs here (mortgage docs to ingest)
    ├── golden_datasets/  ← Golden dataset JSONs from team members
    └── evaluate.py       ← This script

Flow:
    1. Ingest all documents from documents/
    2. Load all golden datasets from golden_datasets/
    3. Run RAG pipeline on each question (saved to checkpoint)
    4. Evaluate with RAGAS metrics
    5. Save report to docs/eval_report.md
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from backend.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger("evaluation")

from ragas.metrics.collections import Faithfulness, AnswerRelevancy, ContextPrecision
from datasets import Dataset

from backend.services import ingestion, query_engine, vectorstore
from backend.services.llm import get_llm

RATE_LIMIT_DELAY = 7  # seconds between LLM calls (free tier: ~10 req/min)

EVAL_DIR = Path("tests/evaluation")
DOCS_DIR = EVAL_DIR / "documents"
GOLDEN_DIR = EVAL_DIR / "golden_datasets"
REPORT_DIR = Path("docs")
CHECKPOINT_FILE = EVAL_DIR / "checkpoint_dataset.json"


def ingest_documents():
    """Ingest only new PDFs/DOCXs. Skips files already in ChromaDB."""
    logger.info("Step 1/5 — Checking documents...")

    files = list(DOCS_DIR.glob("*.pdf")) + list(DOCS_DIR.glob("*.docx"))
    if not files:
        logger.warning("No PDF or DOCX files found in %s", DOCS_DIR)
        return []

    collection = vectorstore.get_collection()
    existing_meta = collection.get(include=["metadatas"])
    existing_files = set()
    for meta in existing_meta["metadatas"]:
        fn = meta.get("filename")
        if fn:
            existing_files.add(fn)

    new_files = [f for f in files if f.name not in existing_files]

    if not new_files:
        logger.info("All %d files already ingested — skipping", len(files))
        return []

    logger.info("Found %d files, %d new to ingest", len(files), len(new_files))
    ingested = []
    for f in new_files:
        logger.info("Ingesting: %s", f.name)
        with open(f, "rb") as fh:
            file_bytes = fh.read()
        result = ingestion.ingest_document(file_bytes=file_bytes, filename=f.name)
        ingested.append(result)
        logger.info("  -> doc_id=%s, chunks=%d", result["doc_id"], result["num_chunks"])

    total_chunks = sum(i["num_chunks"] for i in ingested)
    logger.info("Ingested %d new docs (%d chunks)", len(ingested), total_chunks)
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
    logger.info("Step 2/5 — Loading golden datasets...")

    questions = []
    files = list(GOLDEN_DIR.glob("*.json"))
    if not files:
        logger.warning("No golden dataset JSON files found in %s", GOLDEN_DIR)
        return []

    for f in files:
        with open(f, encoding="utf-8") as fh:
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

            logger.info("Loaded %s — %d questions", f.name, count)

    logger.info("Total questions: %d", len(questions))
    return questions


def run_rag(question: str) -> dict:
    """Run the RAG pipeline and return answer + contexts."""
    result = query_engine.query_rag(question=question, doc_ids=None)
    contexts = [s["content"] for s in result["sources"]]
    return {
        "answer": result["answer"],
        "contexts": contexts,
    }


def _save_checkpoint(data: dict) -> None:
    """Save the RAG dataset to a checkpoint file for resume."""
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    logger.info("Checkpoint saved — %d questions", len(data["question"]))


def _load_checkpoint() -> dict | None:
    """Load a previously saved checkpoint."""
    if not CHECKPOINT_FILE.exists():
        return None
    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info("Checkpoint loaded — %d questions", len(data["question"]))
    return data


def build_dataset(questions: list[dict]) -> Dataset:
    """Run RAG on each answerable question and build RAGAS dataset."""
    logger.info("Step 3/5 — Running RAG pipeline on answerable questions...")

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
        logger.info("[%d/%d] Q: %s", i + 1, len(answerable), question[:70])

        try:
            rag_start = time.time()
            rag_result = run_rag(question)
            rag_elapsed = time.time() - rag_start

            logger.debug(
                "  RAG done — answer_len=%d, contexts=%d, elapsed=%.1fs",
                len(rag_result["answer"]), len(rag_result["contexts"]), rag_elapsed,
            )

            data["question"].append(question)
            data["answer"].append(rag_result["answer"])
            data["contexts"].append(rag_result["contexts"])
            data["ground_truth"].append(ground_truth)
        except Exception as e:
            logger.error("[%d/%d] RAG failed for '%s': %s", i + 1, len(answerable), question[:50], e)
            continue

        # Save checkpoint after each question to allow partial resume
        _save_checkpoint(data)

        if i < len(answerable) - 1:
            logger.debug("Rate limit wait — %ds", RATE_LIMIT_DELAY)
            time.sleep(RATE_LIMIT_DELAY)

    logger.info(
        "RAG complete — answerable=%d, skipped=%d (unanswerable)",
        len(answerable), skipped,
    )
    return Dataset.from_dict(data)


def _build_ragas_llm():
    """Build a RAGAS-compatible NVIDIA LLM via llm_factory (OpenAI-compatible)."""
    from openai import AsyncOpenAI
    import httpx

    api_keys_env = os.getenv("NVIDIA_API_KEYS", "") or os.getenv("NVIDIA_API_KEY", "")
    if "," in api_keys_env:
        api_key = api_keys_env.split(",")[0].strip().strip('"').strip("'")
    else:
        api_key = api_keys_env.strip()

    if not api_key:
        raise ValueError("NVIDIA_API_KEY or NVIDIA_API_KEYS not set in .env")

    model = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")

    client = AsyncOpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        timeout=httpx.Timeout(600.0, connect=10.0),
        max_retries=2,
    )

    from ragas.llms import llm_factory
    return llm_factory(
        model=model,
        provider="openai",
        client=client,
        temperature=0.0,
        max_tokens=4096,
    )


def _build_ragas_embeddings():
    """Build RAGAS-compatible embeddings using the app's load-balanced system."""
    from ragas.embeddings.base import BaseRagasEmbedding

    class LoadBalancedRagasEmbedding(BaseRagasEmbedding):
        """Wrap app's load-balanced HF embeddings for RAGAS."""
        PROVIDER_NAME = "huggingface"
        REQUIRES_MODEL = False

        def __init__(self):
            from backend.services.embeddings import get_embeddings
            self._inner = get_embeddings()
            super().__init__()

        def embed_text(self, text: str) -> list:
            return self._inner.embed_query(text)

        async def aembed_text(self, text: str) -> list:
            import asyncio
            return await asyncio.to_thread(self._inner.embed_query, text)

    return LoadBalancedRagasEmbedding()


def run_evaluation(resume: bool = False):
    """Main evaluation pipeline."""
    logger.info("=" * 60)
    logger.info("Mortgage RAG — RAGAS Evaluation")
    if resume:
        logger.info("RESUME MODE — skipping steps 1-3")
    logger.info("=" * 60)

    eval_start = time.time()

    # Steps 1-3 (can be skipped with --resume)
    ingested = []
    questions = load_golden_datasets()
    if not questions:
        logger.warning("No golden datasets found — add JSON files to %s", GOLDEN_DIR)
        return

    if resume and CHECKPOINT_FILE.exists():
        checkpoint = _load_checkpoint()
        if checkpoint:
            dataset = Dataset.from_dict(checkpoint)
            logger.info("Resumed from checkpoint — %d questions loaded", len(dataset))
        else:
            logger.warning("Checkpoint file empty, running steps 1-3")
            ingest_documents()
            dataset = build_dataset(questions)
    else:
        # Step 1: Ingest documents
        ingested = ingest_documents()
        # Step 3: Build dataset by running RAG
        dataset = build_dataset(questions)

    if len(dataset) == 0:
        logger.warning("No answerable questions to evaluate")
        return

    # Step 4: Run RAGAS evaluation
    logger.info("Step 4/5 — Running RAGAS evaluation...")

    ragas_llm = _build_ragas_llm()
    ragas_embeddings = _build_ragas_embeddings()
    logger.info("RAGAS wrappers ready — using NVIDIA llm_factory + HF embeddings")

    faithfulness_metric = Faithfulness(llm=ragas_llm)
    relevancy_metric = AnswerRelevancy(llm=ragas_llm, embeddings=ragas_embeddings)
    precision_metric = ContextPrecision(llm=ragas_llm)

    ragas_start = time.time()
    total = len(dataset)
    logger.info("Starting RAGAS evaluation — %d questions...", total)

    faith_scores = []
    rel_scores = []
    prec_scores = []

    async def _score_all():
        for i in range(total):
            row = {
                "question": dataset["question"][i],
                "answer": dataset["answer"][i],
                "contexts": dataset["contexts"][i],
                "ground_truth": dataset["ground_truth"][i],
            }

            logger.info("[%d/%d] Scoring: %s", i + 1, total, row["question"][:60])

            try:
                faith = await faithfulness_metric.ascore(
                    user_input=row["question"],
                    response=row["answer"],
                    retrieved_contexts=row["contexts"],
                )
                faith_scores.append(faith.value if hasattr(faith, "value") else float(faith))
            except Exception as e:
                logger.warning("  Faithfulness failed: %s", e)
                faith_scores.append(None)

            try:
                rel = await relevancy_metric.ascore(
                    user_input=row["question"],
                    response=row["answer"],
                )
                rel_scores.append(rel.value if hasattr(rel, "value") else float(rel))
            except Exception as e:
                logger.warning("  AnswerRelevancy failed: %s", e)
                rel_scores.append(None)

            try:
                prec = await precision_metric.ascore(
                    user_input=row["question"],
                    reference=row["ground_truth"],
                    retrieved_contexts=row["contexts"],
                )
                prec_scores.append(prec.value if hasattr(prec, "value") else float(prec))
            except Exception as e:
                logger.warning("  ContextPrecision failed: %s", e)
                prec_scores.append(None)

            logger.info("  [%.1f%%] faith=%.3f rel=%.3f prec=%.3f",
                (i + 1) / total * 100,
                faith_scores[-1] if faith_scores[-1] is not None else 0,
                rel_scores[-1] if rel_scores[-1] is not None else 0,
                prec_scores[-1] if prec_scores[-1] is not None else 0,
            )

    import asyncio
    asyncio.run(_score_all())

    ragas_elapsed = time.time() - ragas_start

    def _safe_mean(vals):
        clean = [v for v in vals if v is not None]
        return sum(clean) / len(clean) if clean else float("nan")

    scores = {
        "faithfulness": _safe_mean(faith_scores),
        "answer_relevancy": _safe_mean(rel_scores),
        "context_precision": _safe_mean(prec_scores),
    }
    nan_count = sum(1 for v in faith_scores if v is None)

    logger.info("RAGAS scores computed — elapsed=%.1fs, failed=%d/%d", ragas_elapsed, nan_count, total)
    logger.info("  Faithfulness:      %.3f", scores["faithfulness"])
    logger.info("  Answer Relevancy:  %.3f", scores["answer_relevancy"])
    logger.info("  Context Precision: %.3f", scores["context_precision"])

    # Step 5: Check targets and save report
    logger.info("Step 5/5 — Checking targets...")
    targets = {"faithfulness": 0.8, "answer_relevancy": 0.75, "context_precision": 0.7}
    all_pass = True
    for metric, target in targets.items():
        passed = scores[metric] >= target
        status = "PASS" if passed else "FAIL"
        logger.info("  %s: %.3f >= %f → %s", metric, scores[metric], target, status)
        if not passed:
            all_pass = False

    save_report(scores, targets, all_pass, questions, dataset, ingested)

    total_elapsed = time.time() - eval_start
    logger.info("=" * 60)
    logger.info("Result: %s", "ALL TARGETS MET" if all_pass else "SOME TARGETS MISSED")
    logger.info("Total elapsed: %.1fs", total_elapsed)
    logger.info("Report saved to docs/eval_report.md")
    logger.info("=" * 60)


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
        lines.append("- No documents were ingested (previously ingested)")

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

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    import sys
    resume = "--resume" in sys.argv
    run_evaluation(resume=resume)
