"""
agent.py -- SupportTriageAgent orchestrator.
Supports both Google Gemini (free) and Anthropic Claude.
"""
import json, re, time
from typing import Dict

from config import (
    LLM_PROVIDER, MODEL_GEMINI, MODEL_ANTHROPIC,
    MAX_TOKENS, TEMPERATURE, ANTHROPIC_API_KEY, GEMINI_API_KEY,
    VALID_STATUSES, VALID_REQUEST_TYPES, REQUEST_DELAY_SECS,
)
from retriever import BM25Retriever
from safety import check_escalation, check_out_of_scope, check_malicious
from prompts import SYSTEM_PROMPT, build_user_prompt

_FALLBACK = {
    "status": "escalated", "product_area": "general_support",
    "response": "Thank you for reaching out. A support specialist will review your request shortly.",
    "justification": "Defaulted to escalation due to an internal processing error.",
    "request_type": "product_issue",
}

class SupportTriageAgent:
    def __init__(self, retriever: BM25Retriever):
        self.retriever = retriever
        self.provider = LLM_PROVIDER
        self._last_call: float = 0.0

        if self.provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel(
                MODEL_GEMINI,
                system_instruction=SYSTEM_PROMPT,
                generation_config=genai.GenerationConfig(
                    temperature=TEMPERATURE,
                    max_output_tokens=MAX_TOKENS,
                ),
            )
            print(f"  [LLM] Using Gemini ({MODEL_GEMINI}) -- FREE TIER")
        elif self.provider == "anthropic":
            import anthropic
            self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            print(f"  [LLM] Using Anthropic ({MODEL_ANTHROPIC})")
        else:
            raise RuntimeError("No API key set! Set GEMINI_API_KEY or ANTHROPIC_API_KEY")

    def process(self, issue: str, subject: str, company: str) -> Dict[str, str]:
        try:
            return self._process_inner(issue, subject, company)
        except Exception as exc:
            print(f"    [error] {exc}")
            return {**_FALLBACK, "justification": f"Processing error: {str(exc)[:120]}"}

    def _process_inner(self, issue: str, subject: str, company: str) -> Dict[str, str]:
        company = company.strip() if company else ""
        if company.lower() in {"none", "n/a", ""}:
            company = ""

        force_escalate, esc_reason = check_escalation(issue, subject, company)
        is_oos, oos_reason = check_out_of_scope(issue, subject)
        is_malicious, mal_reason = check_malicious(issue, subject)

        query = f"{subject} {issue}"
        ctx_docs = self.retriever.retrieve(query, company=company or None)

        user_msg = build_user_prompt(
            issue=issue, subject=subject, company=company,
            context_docs=ctx_docs,
            force_escalate=force_escalate, escalation_reason=esc_reason,
            is_oos=is_oos, oos_reason=oos_reason,
            is_malicious=is_malicious, malicious_reason=mal_reason,
        )

        self._throttle()

        # LLM call
        if self.provider == "gemini":
            raw = self._call_gemini(user_msg)
        else:
            raw = self._call_anthropic(user_msg)

        result = self._parse(raw)
        result = self._validate(result)

        if force_escalate:
            result["status"] = "escalated"
        if is_malicious and not force_escalate:
            result["status"] = "replied"
            result["request_type"] = "invalid"

        return result

    def _call_gemini(self, user_msg: str) -> str:
        for attempt in range(3):
            try:
                resp = self.gemini_model.generate_content(user_msg)
                return resp.text.strip()
            except Exception as e:
                err = str(e).lower()
                if "rate" in err or "quota" in err or "resource" in err:
                    wait = 6 * (attempt + 1)
                    print(f"    [rate-limit] waiting {wait}s...")
                    time.sleep(wait)
                    continue
                raise
        raise Exception("Gemini rate limit exceeded after 3 retries")

    def _call_anthropic(self, user_msg: str) -> str:
        import anthropic
        response = self.client.messages.create(
            model=MODEL_ANTHROPIC, max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE, system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        return response.content[0].text.strip()

    def _parse(self, text: str) -> Dict:
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                try: return json.loads(m.group())
                except json.JSONDecodeError: pass
            raise ValueError(f"Could not parse JSON:\n{text[:300]}")

    def _validate(self, raw: Dict) -> Dict:
        status = raw.get("status", "escalated")
        if status not in VALID_STATUSES: status = "escalated"
        rt = raw.get("request_type", "product_issue")
        if rt not in VALID_REQUEST_TYPES: rt = "product_issue"
        return {
            "status": status,
            "product_area": (raw.get("product_area","general_support") or "general_support").strip(),
            "response": (raw.get("response", _FALLBACK["response"]) or _FALLBACK["response"]).strip(),
            "justification": (raw.get("justification",_FALLBACK["justification"]) or _FALLBACK["justification"]).strip(),
            "request_type": rt,
        }

    def _throttle(self):
        elapsed = time.time() - self._last_call
        if elapsed < REQUEST_DELAY_SECS:
            time.sleep(REQUEST_DELAY_SECS - elapsed)
        self._last_call = time.time()
