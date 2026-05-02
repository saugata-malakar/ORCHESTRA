"""
safety.py — Rule-based pre-screening for high-risk tickets.

Run BEFORE the LLM call so that dangerous cases are flagged
regardless of what the model decides.

Returns (should_escalate: bool, reason: str).
"""

import re
from typing import Tuple


# ── Universal high-risk patterns ──────────────────────────────────────────────
# Any of these triggers an immediate escalation regardless of company.

_UNIVERSAL_ESCALATION: list = [
    # Financial fraud / card security
    (r"\bfraud\b",                        "fraud mentioned"),
    (r"\bunauthorized\s+(?:charge|transaction|access|use)\b",
                                          "unauthorized activity"),
    (r"\bchargeback\b",                   "chargeback request"),
    (r"\bidentity\s+theft\b",            "identity theft"),
    (r"\bstolen\b",                       "stolen asset/card"),
    # Account security
    (r"\baccount\s+(?:\w+\s+){0,3}(?:hacked|compromised|taken\s+over|breached)\b",
                                          "account compromise"),
    (r"\b(?:got|been|was|were|is|am)\s+hacked\b",
                                          "hacked"),
    (r"\bpassword\s+(?:\w+\s+){0,2}(?:stolen|leaked|compromised)\b",
                                          "credential compromise"),
    (r"\bdata\s+breach\b",                "data breach"),
    (r"\bprivacy\s+violation\b",          "privacy violation"),
    (r"\bgdpr\b",                         "GDPR / data protection"),
    # Legal threats
    (r"\blegal\s+action\b",               "legal threat"),
    (r"\blawsuit\b",                      "lawsuit mentioned"),
    (r"\bsue\s+(?:you|hackerrank|visa|anthropic|claude)\b",
                                          "lawsuit threat"),
    (r"\bregulat(?:or|ory)\s+complaint\b","regulatory complaint"),
    # Safety / welfare
    (r"\bsuicid",                         "welfare concern"),
    (r"\bself[\s-]harm\b",               "welfare concern"),
    # Accessibility / discrimination
    (r"\bdiscrimination\b",              "discrimination claim"),
    (r"\bharassment\b",                  "harassment claim"),
    # Prompt injection / manipulation
    (r"(?:ignore|disregard|forget)\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|rules|prompts)",
                                          "prompt injection attempt"),
    (r"(?:reveal|show|display|output)\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions|rules)",
                                          "prompt extraction attempt"),
    (r"(?:affiche|montre|révèle).*(?:règles|logique|documents?\s+récupérés)",
                                          "prompt injection (French)"),
]

# ── Company-specific escalation boosters ──────────────────────────────────────

_COMPANY_PATTERNS: dict = {
    "Visa": [
        (r"\bcard\s+(?:stolen|lost|missing|blocked)\b", "lost/stolen card"),
        (r"\bdispute\b",                               "billing dispute"),
        (r"\brefund\s+(?:not\s+received|denied|failed)\b", "refund issue"),
        (r"\bpin\s+(?:blocked|incorrect|compromised)\b", "PIN security"),
        (r"\btransaction\s+(?:declined|failed)\b",     "transaction failure"),
        (r"\bidentity\b.*\bstolen\b",                  "identity theft"),
        (r"\bcarte\s+(?:bloquée|volée|perdue)\b",      "lost/stolen card (French)"),
    ],
    "HackerRank": [
        (r"\bcheating\b",                              "cheating accusation"),
        (r"\bplagiarism\b",                            "plagiarism claim"),
        (r"\btest\s+(?:tampered|hacked|leaked)\b",     "assessment integrity"),
        (r"\bcandidate\s+(?:impersonat|fraud)\w*\b",   "candidate fraud"),
    ],
    "Claude": [
        (r"\bjailbreak\b",                             "jailbreak attempt"),
        (r"\bbypass\s+(?:filter|safety|guardrail)\b",  "safety bypass attempt"),
        (r"\bgenerate\s+(?:illegal|harmful|weapon)\b", "harmful content request"),
        (r"\bsecurity\s+vulnerability\b",              "security vulnerability report"),
        (r"\bbug\s+bounty\b",                          "security vulnerability report"),
    ],
}

# ── Out-of-scope patterns ─────────────────────────────────────────────────────
# These indicate the ticket has nothing to do with HackerRank/Claude/Visa.

_OOS_PATTERNS: list = [
    (r"\bweather\b(?!\s+(?:related|issue|problem))",  "weather query"),
    (r"\brecipe\s+for\b",                             "recipe request"),
    (r"\bstock\s+(?:price|market|ticker)\b",          "stock market query"),
    (r"\bcrypto(?:currency)?\s+price\b",              "crypto price query"),
    (r"\bmedical\s+(?:advice|diagnosis|symptom)\b",   "medical advice"),
    (r"\bhoroscope\b",                                "horoscope"),
    (r"\bsports?\s+(?:score|result|match)\b",         "sports score"),
    (r"\bwhat(?:'?s| is)\s+(?:the\s+)?(?:capital|population)\s+of\b",
                                                      "geography/trivia query"),
    (r"\bactor\s+in\b",                               "entertainment trivia"),
    (r"\bname\s+of\s+the\s+actor\b",                  "entertainment trivia"),
    (r"\bIron\s+Man\b",                               "entertainment trivia"),
]

# ── Malicious intent patterns ─────────────────────────────────────────────────
_MALICIOUS_PATTERNS: list = [
    (r"\bdelete\s+all\s+files\b",                     "destructive command request"),
    (r"\bformat\s+(?:the\s+)?(?:hard\s+)?(?:drive|disk)\b",
                                                      "destructive command request"),
    (r"\brm\s+-rf\b",                                 "destructive command request"),
    (r"\bgive\s+me\s+(?:the\s+)?code\s+to\s+delete\b","destructive code request"),
]


# ── Public API ────────────────────────────────────────────────────────────────

def check_escalation(issue: str, subject: str, company: str) -> Tuple[bool, str]:
    """
    Returns (should_escalate, reason_string).
    Checks universal patterns first, then company-specific boosters.
    """
    haystack = f"{subject} {issue}".lower()

    for pattern, label in _UNIVERSAL_ESCALATION:
        if re.search(pattern, haystack, re.IGNORECASE):
            return True, label

    if company in _COMPANY_PATTERNS:
        for pattern, label in _COMPANY_PATTERNS[company]:
            if re.search(pattern, haystack, re.IGNORECASE):
                return True, f"[{company}] {label}"

    return False, ""


def check_out_of_scope(issue: str, subject: str) -> Tuple[bool, str]:
    """
    Returns (is_oos, reason_string).
    Does NOT auto-escalate — let the LLM decide reply vs escalate.
    """
    haystack = f"{subject} {issue}".lower()
    for pattern, label in _OOS_PATTERNS:
        if re.search(pattern, haystack, re.IGNORECASE):
            return True, label
    return False, ""


def check_malicious(issue: str, subject: str) -> Tuple[bool, str]:
    """
    Returns (is_malicious, reason_string).
    Detects requests for destructive actions.
    """
    haystack = f"{subject} {issue}".lower()
    for pattern, label in _MALICIOUS_PATTERNS:
        if re.search(pattern, haystack, re.IGNORECASE):
            return True, label
    return False, ""

def injection_detector(issue: str, subject: str) -> Tuple[bool, str]:
    """
    Feature #3: Dedicated Prompt Injection Detector
    Scores how likely a ticket is to be a prompt injection or jailbreak attempt.
    """
    haystack = f"{subject} {issue}".lower()
    score = 0
    reasons = []
    
    # 1. Instruction-like phrases
    if re.search(r"(?:ignore|disregard|forget)\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|rules|prompts)", haystack):
        score += 5
        reasons.append("instruction_override")
        
    # 2. System extraction
    if re.search(r"(?:reveal|show|display|output|print)\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions|rules|logic|documents)", haystack):
        score += 5
        reasons.append("system_extraction")
        
    # 3. Role-play setups
    if re.search(r"(?:pretend you are|act as|you are now)\b", haystack):
        score += 3
        reasons.append("roleplay_setup")
        
    # 4. Base64 or obfuscation detection (basic heuristic)
    if re.search(r"^[A-Za-z0-9+/]{40,}={0,2}$", haystack):
        score += 4
        reasons.append("base64_obfuscation")
        
    if score >= 5:
        return True, "prompt_injection"
    return False, ""
