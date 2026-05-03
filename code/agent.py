"""
agent.py -- Advanced SupportTriageAgent orchestrator.
Features: TF-IDF Deduplication, Language Detection, Company Inference, 
Self-Critique, Confidence Scoring, and Prompt Injection Prevention.
"""
import json, re, time
from typing import Dict, Tuple, Optional
from langdetect import detect
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import (
    LLM_PROVIDER, MODEL_GEMINI, MODEL_ANTHROPIC,
    MAX_TOKENS, TEMPERATURE, ANTHROPIC_API_KEY, GEMINI_API_KEY,
    VALID_STATUSES, VALID_REQUEST_TYPES, REQUEST_DELAY_SECS,
)
from retriever import BM25Retriever
from safety import check_escalation, check_out_of_scope, check_malicious, injection_detector
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
        
        # State for Feature #4: Similarity Deduplication
        self.history_texts = []
        self.history_results = []
        self.vectorizer = TfidfVectorizer(stop_words="english")

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
        else:
            raise RuntimeError("Only Gemini provider is supported for advanced features.")

    def process(self, issue: str, subject: str, company: str) -> Dict[str, str]:
        try:
            return self._process_inner(issue, subject, company)
        except Exception as exc:
            print(f"    [error] {exc}")
            return {**_FALLBACK, "justification": f"Processing error: {str(exc)[:120]}", "confidence": 0.0, "audit_flags": ["error"]}

    def _infer_company(self, text: str) -> Tuple[str, float]:
        """Feature #8: Company Inference for None Tickets"""
        text_lower = text.lower()
        hr_kw = ["test", "assessment", "candidate", "recruiter", "score"]
        cl_kw = ["conversation", "api", "subscription", "model", "anthropic", "prompt"]
        vi_kw = ["card", "transaction", "payment", "merchant", "dispute"]
        
        hr_score = sum(1 for kw in hr_kw if kw in text_lower)
        cl_score = sum(1 for kw in cl_kw if kw in text_lower)
        vi_score = sum(1 for kw in vi_kw if kw in text_lower)
        
        scores = {"HackerRank": hr_score, "Claude": cl_score, "Visa": vi_score}
        best = max(scores, key=scores.get)
        
        if scores[best] > 0:
            return best, min(1.0, scores[best] * 0.3)
        return "", 0.0

    def _check_duplicate(self, text: str) -> Optional[Dict]:
        """Feature #4: Ticket Similarity Deduplication"""
        if not self.history_texts: return None
        
        tfidf_matrix = self.vectorizer.fit_transform(self.history_texts + [text])
        cosine_sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
        
        max_idx = cosine_sim.argmax()
        # Raised threshold to 0.98 because support tickets share too much boilerplate vocabulary,
        # which was causing the agent to falsely flag everything as a duplicate!
        if cosine_sim[max_idx] > 0.98:
            res = dict(self.history_results[max_idx])
            res["justification"] = f"Resolved as duplicate of a previous ticket. Original logic: {res['justification']}"
            res["confidence"] = round(float(cosine_sim[max_idx]), 2)
            res["audit_flags"] = ["deduplicated"]
            return res
        return None

    def _process_inner(self, issue: str, subject: str, company: str) -> Dict:
        full_text = f"{subject} {issue}".strip()
        audit_flags = []
        
        # 1. Deduplication (Feature #4)
        dup_res = self._check_duplicate(full_text)
        if dup_res:
            return dup_res
            
        company = company.strip() if company and str(company).lower() not in {"none", "n/a", ""} else ""
        
        # 2. Company Inference (Feature #8)
        if not company:
            company, conf = self._infer_company(full_text)
            if company: audit_flags.append(f"inferred_company:{company}")

        # 3. Language Detection (Feature #2)
        lang = "en"
        english_text = full_text
        try:
            lang = detect(full_text)
            if lang != "en":
                audit_flags.append(f"translated_from:{lang}")
                self._throttle()
                # Use Gemini to translate to English for BM25 retrieval
                english_text = self._call_gemini(f"Translate the following ticket to English. Only output the translation, nothing else.\n\n{full_text}")
        except: pass

        # 4. Advanced Safety & Injection Detection (Feature #3, #7)
        is_injection, inj_reason = injection_detector(issue, subject)
        force_escalate, esc_reason = check_escalation(issue, subject, company)
        is_oos, oos_reason = check_out_of_scope(issue, subject)
        is_malicious, mal_reason = check_malicious(issue, subject)

        if is_injection:
            force_escalate = True
            esc_reason = inj_reason
            audit_flags.append("injection_detected")

        # 5. BM25 Retrieval
        ctx_docs = self.retriever.retrieve(english_text, company=company or None)
        bm25_confidence = 0.85 if ctx_docs else 0.4  # Proxy for Feature #1
        
        # 6. LLM Generation
        prompt = build_user_prompt(
            issue=english_text, subject=subject, company=company,
            context_docs=ctx_docs,
            force_escalate=force_escalate, escalation_reason=esc_reason,
            is_oos=is_oos, oos_reason=oos_reason,
            is_malicious=is_malicious, malicious_reason=mal_reason,
        )
        
        if lang != "en":
            prompt += f"\n\nIMPORTANT: You must write your final 'response' field in the {lang} language, but keep the JSON keys in English."

        self._throttle()
        raw = self._call_gemini(prompt)
        result = self._parse(raw)
        
        # 7. Self-Critique (Feature #9)
        if not force_escalate and not is_oos and not is_malicious:
            critique_prompt = f"Does this response make any claims NOT supported by the context? Reply strictly YES or NO.\nContext: {ctx_docs}\nResponse: {result.get('response', '')}"
            self._throttle()
            critique = self._call_gemini(critique_prompt).strip().upper()
            if "YES" in critique:
                audit_flags.append("self_critique_failed_regenerated")
                prompt += "\n\nCRITICAL: Your previous response contained hallucinations. Rely ONLY on the provided context."
                self._throttle()
                raw = self._call_gemini(prompt)
                result = self._parse(raw)
                bm25_confidence -= 0.2

        result = self._validate(result)

        if force_escalate:
            result["status"] = "escalated"
        if is_malicious and not force_escalate:
            result["status"] = "replied"
            result["request_type"] = "invalid"

        result["confidence"] = round(bm25_confidence, 2)
        result["audit_flags"] = audit_flags
        
        # Save to history for deduplication
        self.history_texts.append(full_text)
        self.history_results.append(result)
        
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
                    time.sleep(wait)
                    continue
                raise
        raise Exception("Gemini rate limit exceeded after 3 retries")

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
