"""
Input and output guardrails — regex-based + NeMo Guardrails integration.

Two layers of safety:
    1. Regex guardrails (fast, no LLM call)
       - InputGuardrails: prompt injection, jailbreak, harmful content
       - OutputGuardrails: prompt leakage, response length

    2. NeMo Guardrails (LLM-based, mortgage domain restriction)
       - Uses NVIDIA NIM + rails.co config
       - Blocks non-mortgage queries, detects injection/jailbreak

Classes:
    InputGuardrails
        check(user_input) -> GuardrailResult

    OutputGuardrails
        check(llm_output) -> GuardrailResult
        sanitize(llm_output) -> str

    NemoGuardrails
        async check_input(user_input) -> str | None  (blocked message or None)

Functions:
    get_input_guardrails() -> InputGuardrails     (singleton)
    get_output_guardrails() -> OutputGuardrails    (singleton)
    get_nemo_guardrails() -> NemoGuardrails        (singleton)

Env vars used:
    INPUT_GUARDRAILS_ENABLED  - Enable regex input checks (default: true)
    OUTPUT_GUARDRAILS_ENABLED - Enable regex output checks (default: true)
    NEMO_GUARDRAILS_ENABLED   - Enable NeMo Guardrails (default: true)
    NVIDIA_API_KEY            - For NeMo (extracted from NVIDIA_API_KEYS if needed)
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from backend.logging_config import get_logger

logger = get_logger("backend.guardrails")


@dataclass
class GuardrailResult:
    """Result of a guardrail check."""
    passed: bool
    reason: str = ""
    severity: str = "info"  # info, warning, blocked


class InputGuardrails:
    """
    Guardrails for user input before it reaches the LLM.

    Checks for:
    1. Prompt injection attempts
    2. Harmful / malicious content
    3. Input length limits
    4. System prompt extraction attempts
    5. Role-play / jailbreak attempts
    """

    # Prompt injection patterns
    INJECTION_PATTERNS = [
        # Direct instruction override
        r"ignore\s+(all\s+)?(previous|above|prior|earlier|preceding)\s+(instructions?|prompts?|rules?|guidelines?)",
        r"disregard\s+(all\s+)?(previous|above|prior|earlier)\s+(instructions?|prompts?)",
        r"forget\s+(everything|all|what)\s+(you|I)\s+(told|said|were told)",
        r"override\s+(your|the)\s+(previous|current|existing)\s+(instructions?|programming)",
        # System prompt extraction
        r"(show|reveal|print|display|output|repeat|tell me)\s+(me\s+)?(your|the)\s+(system\s+prompt|instructions?|rules?|guidelines?)",
        r"what\s+(are|is)\s+your\s+(system\s+prompt|instructions?|initial\s+prompt)",
        r"copy\s+(and\s+paste|paste)\s+(your|the)\s+(system\s+prompt|instructions?)",
        # Role manipulation
        r"you\s+are\s+now\s+(a|an|the)\s+",
        r"act\s+as\s+if\s+you\s+(have|don.t|do\s+not|have\s+no)\s+(any\s+)?(rules?|restrictions?|limits?|guidelines?)",
        r"pretend\s+(you\s+are|to\s+be)\s+(a|an)\s+",
        r"roleplay\s+as\s+",
        r"enter\s+(debug|developer|admin|sudo)\s+mode",
        # Encoding / obfuscation attempts
        r"(base64|rot13|hex)\s*(decode|encode)",
        r"translate\s+(this|the\s+following)\s+(to|into)\s+",
        # Data exfiltration
        r"(send|email|post|upload)\s+(all|every|the)\s+(your|this)\s+(data|info|information|history)",
        r"(what|tell me)\s+(is|are)\s+the\s+(contents?\s+of|value\s+of)\s+(your|the)\s+(api.?key|token|secret)",
    ]

    # Harmful content patterns
    HARMFUL_PATTERNS = [
        r"(how\s+to\s+)?(make|build|create|construct)\s+(a\s+)?(bomb|explosive|weapon|drug|virus|malware)",
        r"(hack|exploit|compromise|breach)\s+(into|a|the|some|any)\s+",
        r"(steal|phish|scam|fraud)\s+",
        r"(kill|murder|assault|attack)\s+(someone|a\s+person|people|him|her|them)",
        r"(self[- ]?harm|suicide|cut\s+myself)",
    ]

    # Jailbreak patterns
    JAILBREAK_PATTERNS = [
        r"dan\s+mode",
        r"do\s+anything\s+now",
        r"jailbreak",
        r"unrestricted\s+(ai|mode|version)",
        r"(no|without)\s+(filters?|restrictions?|limits?|rules?|censorship)",
        r"bypass\s+(all\s+)?(safety|content|filter|moderation)",
    ]

    MAX_INPUT_LENGTH = 2000  # Maximum characters for a single question

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._compiled_injection = [re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS]
        self._compiled_harmful = [re.compile(p, re.IGNORECASE) for p in self.HARMFUL_PATTERNS]
        self._compiled_jailbreak = [re.compile(p, re.IGNORECASE) for p in self.JAILBREAK_PATTERNS]

    def check(self, user_input: str) -> GuardrailResult:
        """Run all input guardrail checks. Returns the first failure or success."""
        if not self.enabled:
            return GuardrailResult(passed=True)

        # 1. Length check
        if len(user_input) > self.MAX_INPUT_LENGTH:
            logger.warning("Input exceeds max length — %d > %d", len(user_input), self.MAX_INPUT_LENGTH)
            return GuardrailResult(
                passed=False,
                reason=f"Input too long ({len(user_input)} characters). Maximum is {self.MAX_INPUT_LENGTH}.",
                severity="warning",
            )

        # 2. Empty check
        if not user_input.strip():
            return GuardrailResult(
                passed=False,
                reason="Input is empty.",
                severity="warning",
            )

        # 3. Prompt injection check
        for pattern in self._compiled_injection:
            match = pattern.search(user_input)
            if match:
                logger.warning(
                    "Prompt injection detected — pattern=%s, input=%s",
                    pattern.pattern[:50], user_input[:100],
                )
                return GuardrailResult(
                    passed=False,
                    reason="Your request was blocked due to suspected prompt injection.",
                    severity="blocked",
                )

        # 4. Harmful content check
        for pattern in self._compiled_harmful:
            match = pattern.search(user_input)
            if match:
                logger.warning(
                    "Harmful content detected — pattern=%s, input=%s",
                    pattern.pattern[:50], user_input[:100],
                )
                return GuardrailResult(
                    passed=False,
                    reason="Your request contains content that cannot be processed.",
                    severity="blocked",
                )

        # 5. Jailbreak check
        for pattern in self._compiled_jailbreak:
            match = pattern.search(user_input)
            if match:
                logger.warning(
                    "Jailbreak attempt detected — pattern=%s, input=%s",
                    pattern.pattern[:50], user_input[:100],
                )
                return GuardrailResult(
                    passed=False,
                    reason="Your request was blocked. Please ask a mortgage-related question.",
                    severity="blocked",
                )

        return GuardrailResult(passed=True)


class OutputGuardrails:
    """
    Guardrails for LLM output before it reaches the user.

    Checks for:
    1. Response length limits
    2. Known unsafe content patterns
    3. Prompt echo / leakage
    """

    MAX_OUTPUT_LENGTH = 4000  # Maximum characters in response

    # Patterns that suggest the LLM echoed its system prompt
    PROMPT_LEAKAGE_PATTERNS = [
        r"you\s+are\s+a\s+mortgage\s+document\s+assistant",
        r"rules:\s*\n\s*1\.\s*answer\s+only",
        r"few[- ]shot\s+examples?:",
    ]

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._compiled_leakage = [re.compile(p, re.IGNORECASE) for p in self.PROMPT_LEAKAGE_PATTERNS]

    def check(self, llm_output: str) -> GuardrailResult:
        """Run all output guardrail checks."""
        if not self.enabled:
            return GuardrailResult(passed=True)

        # 1. Length check
        if len(llm_output) > self.MAX_OUTPUT_LENGTH:
            logger.warning(
                "LLM output truncated — %d > %d chars",
                len(llm_output), self.MAX_OUTPUT_LENGTH,
            )
            return GuardrailResult(
                passed=True,  # Truncate but don't block
                reason=f"Response truncated from {len(llm_output)} to {self.MAX_OUTPUT_LENGTH} characters.",
                severity="warning",
            )

        # 2. Prompt leakage check
        for pattern in self._compiled_leakage:
            match = pattern.search(llm_output)
            if match:
                logger.warning(
                    "Prompt leakage detected in output — pattern=%s",
                    pattern.pattern[:50],
                )
                return GuardrailResult(
                    passed=False,
                    reason="Response filtered due to content policy.",
                    severity="blocked",
                )

        return GuardrailResult(passed=True)

    def sanitize(self, llm_output: str) -> str:
        """Apply output sanitization (truncation, etc.)."""
        if not self.enabled:
            return llm_output

        if len(llm_output) > self.MAX_OUTPUT_LENGTH:
            # Try to truncate at a sentence boundary
            truncated = llm_output[:self.MAX_OUTPUT_LENGTH]
            last_period = truncated.rfind(".")
            last_newline = truncated.rfind("\n")
            cut_at = max(last_period, last_newline)
            if cut_at > self.MAX_OUTPUT_LENGTH * 0.5:
                truncated = truncated[:cut_at + 1]
            return truncated

        return llm_output


# ── Singleton instances ──────────────────────────────────────────────────

_input_guardrails: InputGuardrails | None = None
_output_guardrails: OutputGuardrails | None = None


def get_input_guardrails() -> InputGuardrails:
    global _input_guardrails
    if _input_guardrails is None:
        enabled = os.getenv("INPUT_GUARDRAILS_ENABLED", "true").lower() == "true"
        _input_guardrails = InputGuardrails(enabled=enabled)
        logger.info("Input guardrails initialized — enabled=%s", enabled)
    return _input_guardrails


def get_output_guardrails() -> OutputGuardrails:
    global _output_guardrails
    if _output_guardrails is None:
        enabled = os.getenv("OUTPUT_GUARDRAILS_ENABLED", "true").lower() == "true"
        _output_guardrails = OutputGuardrails(enabled=enabled)
        logger.info("Output guardrails initialized — enabled=%s", enabled)
    return _output_guardrails


# ── NeMo Guardrails ─────────────────────────────────────────────────────


class NemoGuardrails:
    """
    NeMo Guardrails wrapper for domain restriction and safety.

    Uses NVIDIA NIM + rails.co config to enforce:
    - Mortgage/finance domain only
    - Refusal for non-domain queries
    - Safety checks (fraud, illegal activity)
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._rails = None
        if enabled:
            try:
                # NeMo needs a single NVIDIA_API_KEY — extract one from load-balanced keys
                api_key = os.getenv("NVIDIA_API_KEY")
                if not api_key:
                    keys_raw = os.getenv("NVIDIA_API_KEYS", "")
                    keys = [k.strip() for k in keys_raw.split(",") if k.strip()]
                    if keys:
                        api_key = keys[0]
                        os.environ["NVIDIA_API_KEY"] = api_key

                # NeMo downloads HF models internally — set HF_TOKEN to suppress warning
                if not os.getenv("HF_TOKEN"):
                    hf_keys = os.getenv("HF_API_KEYS", "")
                    first_key = [k.strip() for k in hf_keys.split(",") if k.strip()]
                    if first_key:
                        os.environ["HF_TOKEN"] = first_key[0]

                from nemoguardrails import LLMRails, RailsConfig
                config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config")
                config = RailsConfig.from_path(config_path)
                self._rails = LLMRails(config)
                logger.info("NeMo Guardrails initialized — config=%s", config_path)
            except Exception as e:
                logger.warning("NeMo Guardrails init failed — falling back to regex: %s", e)
                self._rails = None

    async def check_input(self, user_input: str) -> str | None:
        """
        Check user input for safety issues (injection, jailbreak).
        Returns blocked message or None if safe.
        """
        if not self.enabled or self._rails is None:
            return None

        try:
            messages = [{"role": "user", "content": user_input}]

            start = time.time()
            response = await self._rails.generate_async(messages=messages)
            elapsed = time.time() - start
            logger.info("NeMo Guardrails input check — elapsed=%.2fs", elapsed)

            if isinstance(response, dict):
                response_text = response.get("content", str(response))
            else:
                response_text = str(response)

            # If NeMo refused the question, return the refusal
            refusal_keywords = [
                "i'm designed to answer",
                "i cannot assist",
                "i cannot help",
                "not able to assist",
                "mortgage and home loan related questions only",
            ]
            if any(kw in response_text.lower() for kw in refusal_keywords):
                logger.info("NeMo Guardrails blocked input — question rejected as non-mortgage")
                return response_text

            return None
        except Exception as e:
            logger.warning("NeMo Guardrails input check failed — %s", e)
            return None


_nemo_guardrails: NemoGuardrails | None = None


def get_nemo_guardrails() -> NemoGuardrails:
    global _nemo_guardrails
    if _nemo_guardrails is None:
        enabled = os.getenv("NEMO_GUARDRAILS_ENABLED", "true").lower() == "true"
        _nemo_guardrails = NemoGuardrails(enabled=enabled)
    return _nemo_guardrails
