"""Optional language-model fallback -- provider neutral.

The deterministic engine in :mod:`gaapai.ask` answers a fixed set of questions
exactly and refuses everything else. That refusal is right but unhelpful: "what
is ASC 606" or "why is June higher than May" are reasonable questions and
neither is a pattern match.

This module puts a model *behind* the deterministic layer, never in front:

1. deterministic first -- if :func:`gaapai.ask.answer` understands the question
   the model is never called and the figure stays reproducible;
2. the model receives **already-computed** figures, not the raw rows, so it
   composes an explanation rather than doing arithmetic;
3. replies are labelled as model-generated, because an answer that cannot be
   reproduced must not look like one that can.

**Any provider.** Nearly every vendor speaks one of three HTTP shapes, so three
transports cover the field:

``openai``
    ``POST {base}/chat/completions`` -- OpenAI, DeepSeek, Groq, OpenRouter,
    Together, vLLM, Ollama, LM Studio, llama.cpp, and most other local runners.
``anthropic``
    ``POST {base}/v1/messages`` -- Claude.
``gemini``
    ``POST {base}/models/{model}:generateContent`` -- Google.

Calls go out over :mod:`urllib` rather than a vendor SDK. That keeps the
dependency count at zero, and means a local model works with no network and no
account at all.

Nothing here is trusted with a number. If the endpoint, the key, or the model
name is wrong the failure is reported plainly rather than being allowed to
degrade an answer.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

__all__ = [
    "Provider", "PROVIDERS", "provider_for", "LLMConfig",
    "build_context", "ask_llm", "ask_planner", "planner_prompt",
    "list_models", "test_connection", "SYSTEM_PROMPT",
]


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Provider:
    """One endpoint family. ``base_url`` and ``model`` stay user-editable.

    Defaults are a starting point, not a promise: vendors rename models and move
    paths. Everything here can be overridden in the UI, and
    :func:`test_connection` exists so a wrong default is found in seconds
    instead of mid-question.
    """

    key: str
    label: str
    transport: str                 # "openai" | "anthropic" | "gemini"
    base_url: str
    suggested_models: List[str] = field(default_factory=list)
    needs_key: bool = True
    hint: str = ""


PROVIDERS: List[Provider] = [
    Provider(
        "anthropic", "Anthropic (Claude)", "anthropic", "https://api.anthropic.com",
        ["claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5-20251001"],
        hint="Key from console.anthropic.com."),
    Provider(
        "openai", "OpenAI", "openai", "https://api.openai.com/v1",
        ["gpt-4o", "gpt-4o-mini", "gpt-4.1"],
        hint="Key from platform.openai.com."),
    Provider(
        "gemini", "Google Gemini", "gemini",
        "https://generativelanguage.googleapis.com/v1beta",
        ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        hint="Key from aistudio.google.com."),
    Provider(
        "deepseek", "DeepSeek", "openai", "https://api.deepseek.com/v1",
        ["deepseek-chat", "deepseek-reasoner"],
        hint="Key from platform.deepseek.com."),
    Provider(
        "groq", "Groq", "openai", "https://api.groq.com/openai/v1",
        ["llama-3.3-70b-versatile"], hint="Key from console.groq.com."),
    Provider(
        "openrouter", "OpenRouter", "openai", "https://openrouter.ai/api/v1",
        ["anthropic/claude-sonnet-4.5", "openai/gpt-4o"],
        hint="One key, many models. Key from openrouter.ai."),
    Provider(
        "ollama", "Ollama (local)", "openai", "http://localhost:11434/v1",
        ["llama3.1", "qwen2.5", "mistral"], needs_key=False,
        hint="Run `ollama serve` first. No key, no network."),
    Provider(
        "lmstudio", "LM Studio (local)", "openai", "http://localhost:1234/v1",
        [], needs_key=False,
        hint="Start the local server in LM Studio. No key needed."),
    Provider(
        "custom", "Other (OpenAI-compatible)", "openai", "",
        [], needs_key=False,
        hint="Any endpoint exposing /chat/completions -- vLLM, llama.cpp, "
             "Together, a gateway, or an internal deployment."),
]

_BY_KEY = {p.key: p for p in PROVIDERS}


def provider_for(key: str) -> Provider:
    return _BY_KEY.get(key, PROVIDERS[0])


SYSTEM_PROMPT = """\
You are the explanation layer of Akshapatalika AI, a deterministic US GAAP
analysis tool. A separate, verified engine has already computed every figure in
the CONTEXT below from the user's data.

Rules you must follow:

1. NEVER compute, estimate, or adjust a monetary figure yourself. Use only the
   numbers given in the CONTEXT, exactly as written. If answering would need a
   figure the CONTEXT does not contain, say precisely which figure is missing
   and stop.
2. NEVER invent an ASC citation. Cite only paragraphs that appear in the
   CONTEXT. If you know a rule but its paragraph is not in the CONTEXT,
   describe the requirement without a citation and say it is uncited.
3. Judgements belong to the preparer. Whether a promise is distinct, whether a
   return is probable, what a standalone selling price is -- these are the
   entity's determinations. Explain what the decision depends on; never make it.
4. If items are awaiting the user's review, say so when it affects the answer.
   Figures marked excluded are already deducted; figures marked pending are not.
5. Be concise and concrete. An accountant or small-business owner is reading.
   Plain language over standard-setter phrasing, short paragraphs, no preamble.
6. If the question is not about accounting or this data set, say so briefly.
"""


def planner_prompt() -> str:
    """The planning instruction, generated from the op and chart registries.

    Generated rather than written out, so adding an operation or a chart kind
    makes it available to the model immediately. A hand-written menu drifts out
    of date silently, and the failure then looks like the model being stupid
    rather than the prompt being stale.
    """
    from . import charts
    from . import plan as plan_mod

    return f"""\
You are the planning layer of Akshapatalika AI, a deterministic US GAAP
analysis tool. You do NOT calculate. You decide what should be calculated and
emit a plan; a verified engine runs it against the user's data.

When the question can be answered by calculation, reply with EXACTLY ONE fenced
json block and nothing else:

```json
{{
  "title": "short title for the answer",
  "steps": [
    {{"id": "rev", "op": "revenue", "by": "month", "label": "Revenue"}},
    {{"id": "cost", "op": "formula", "expr": "rev * 0.5", "label": "Cost of goods"}},
    {{"id": "gp", "op": "formula", "expr": "rev - cost", "label": "Gross profit"}}
  ],
  "output": {{"kind": "chart", "chart": "line", "series": ["rev", "gp"],
              "table": ["rev", "cost", "gp"], "format": "money"}},
  "notes": "one sentence on any assumption used"
}}
```

OPERATIONS available to steps:
{plan_mod.describe_for_model()}

CHART types available to output.chart:
{charts.describe_for_model()}

Rules:
1. Never put a computed monetary amount in the plan. A rate the user stated
   (0.5 for 50%) belongs in a formula; a total never does.
2. Every "expr" may reference only ids of EARLIER steps, numbers, and the
   functions abs, min, max, round. No attributes, indexing, or other calls.
3. output.kind is "number" for a single figure, "table" for figures without a
   chart, "chart" to draw one. Use only a chart type listed above.
4. If the question needs a fact you have not been given -- a cost rate, a
   return window, which date counts as the sale -- do NOT guess. Reply in plain
   prose saying exactly what you need, with no json block.
5. If the question is about accounting meaning rather than the user's numbers
   ("what is ASC 606"), reply in plain prose with no json block.
6. Judgements belong to the preparer. Never decide whether a promise is
   distinct, whether a return is probable, or what a standalone selling price
   is; say what the decision depends on.
"""


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class LLMConfig:
    """Session-scoped settings. The key is never persisted to disk."""

    provider: str = "anthropic"
    api_key: str = ""
    model: str = ""
    base_url: str = ""
    max_tokens: int = 1200
    timeout: int = 90

    @property
    def spec(self) -> Provider:
        return provider_for(self.provider)

    @property
    def endpoint(self) -> str:
        return (self.base_url or self.spec.base_url).rstrip("/")

    @property
    def chosen_model(self) -> str:
        if self.model:
            return self.model
        return self.spec.suggested_models[0] if self.spec.suggested_models else ""

    @property
    def ready(self) -> bool:
        """Enough supplied to attempt a call.

        A local runner needs no key, so requiring one would lock out exactly the
        setup that needs no account.
        """
        if not self.endpoint or not self.chosen_model:
            return False
        return bool(self.api_key.strip()) or not self.spec.needs_key

    def why_not_ready(self) -> str:
        if not self.endpoint:
            return "No endpoint URL."
        if not self.chosen_model:
            return "No model name."
        if self.spec.needs_key and not self.api_key.strip():
            return f"{self.spec.label} needs an API key."
        return ""


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


def _post(url: str, payload: Dict[str, Any], headers: Dict[str, str],
          timeout: int) -> Dict[str, Any]:
    """POST JSON and return parsed JSON, with errors worth reading."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        if v:
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:600]
        except Exception:                          # pragma: no cover - defensive
            pass
        raise RuntimeError(
            f"{exc.code} {exc.reason} from {url}"
            + (f"\n{detail}" if detail else "")) from None
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach {url} ({exc.reason}). For a local model, check "
            "the server is running and the port is right.") from None
    except TimeoutError:
        raise RuntimeError(f"{url} did not respond within {timeout}s.") from None


def _get(url: str, headers: Dict[str, str], timeout: int) -> Dict[str, Any]:
    req = urllib.request.Request(url, method="GET")
    for k, v in headers.items():
        if v:
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Could not list models from {url}: {exc}") from None


# ---------------------------------------------------------------------------
# Transports
# ---------------------------------------------------------------------------


def _call_openai(question: str, context: str, cfg: LLMConfig,
                 history: List[Dict[str, str]], system: str) -> str:
    messages = [{"role": "system", "content": system}]
    messages += history
    messages.append({"role": "user",
                     "content": f"{context}\n\n=== QUESTION ===\n{question}"})
    payload = {"model": cfg.chosen_model, "messages": messages,
               "max_tokens": cfg.max_tokens}
    headers = {"Authorization": f"Bearer {cfg.api_key.strip()}"
               if cfg.api_key.strip() else ""}
    url = f"{cfg.endpoint}/chat/completions"
    try:
        data = _post(url, payload, headers, cfg.timeout)
    except RuntimeError as exc:
        # Newer OpenAI models reject max_tokens and want max_completion_tokens.
        if "max_completion_tokens" in str(exc) or "max_tokens" in str(exc):
            payload.pop("max_tokens", None)
            payload["max_completion_tokens"] = cfg.max_tokens
            data = _post(url, payload, headers, cfg.timeout)
        else:
            raise
    try:
        return (data["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(
            f"Unexpected reply shape from {url}: {json.dumps(data)[:400]}"
        ) from None


def _call_anthropic(question: str, context: str, cfg: LLMConfig,
                    history: List[Dict[str, str]], system: str) -> str:
    messages = list(history)
    messages.append({"role": "user",
                     "content": f"{context}\n\n=== QUESTION ===\n{question}"})
    payload = {"model": cfg.chosen_model, "max_tokens": cfg.max_tokens,
               "system": system, "messages": messages}
    headers = {"x-api-key": cfg.api_key.strip(),
               "anthropic-version": "2023-06-01"}
    url = f"{cfg.endpoint}/v1/messages"
    data = _post(url, payload, headers, cfg.timeout)
    try:
        return "".join(b.get("text", "") for b in data["content"]
                       if b.get("type") == "text").strip()
    except (KeyError, TypeError):
        raise RuntimeError(
            f"Unexpected reply shape from {url}: {json.dumps(data)[:400]}"
        ) from None


def _call_gemini(question: str, context: str, cfg: LLMConfig,
                 history: List[Dict[str, str]], system: str) -> str:
    contents = [{"role": ("model" if m["role"] == "assistant" else "user"),
                 "parts": [{"text": m["content"]}]} for m in history]
    contents.append({"role": "user",
                     "parts": [{"text": f"{context}\n\n=== QUESTION ===\n{question}"}]})
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": cfg.max_tokens},
    }
    url = (f"{cfg.endpoint}/models/{cfg.chosen_model}:generateContent"
           f"?key={cfg.api_key.strip()}")
    data = _post(url, payload, {}, cfg.timeout)
    try:
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts).strip()
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(
            f"Unexpected reply shape from Gemini: {json.dumps(data)[:400]}"
        ) from None


_TRANSPORTS = {"openai": _call_openai, "anthropic": _call_anthropic,
               "gemini": _call_gemini}


def ask_llm(question: str, context: str, config: LLMConfig,
            history: Optional[List[Dict[str, str]]] = None,
            system: Optional[str] = None) -> str:
    """Ask the configured model, with the explaining prompt unless told otherwise."""
    reason = config.why_not_ready()
    if reason:
        raise RuntimeError(reason)
    fn = _TRANSPORTS.get(config.spec.transport)
    if fn is None:                                 # pragma: no cover - guarded by data
        raise RuntimeError(f"Unknown transport {config.spec.transport!r}")
    return fn(question, context, config, list(history or []),
              system or SYSTEM_PROMPT)


def ask_planner(question: str, context: str, config: LLMConfig,
                history: Optional[List[Dict[str, str]]] = None):
    """Ask for a plan. Returns ``(plan_or_None, raw_reply)``.

    A ``None`` plan is not a failure: the planning prompt tells the model to
    answer in prose when the question is about meaning rather than arithmetic,
    or when a fact it would need is missing. The caller shows the prose.
    """
    from . import plan as plan_mod

    reply = ask_llm(question, context, config, history=history,
                    system=planner_prompt())
    return plan_mod.extract_plan(reply), reply


def list_models(config: LLMConfig) -> List[str]:
    """Model ids the endpoint reports, where it supports ``GET /models``.

    Mostly for local runners: whatever you have pulled in Ollama or loaded in
    LM Studio is impossible to guess and tedious to type.
    """
    if config.spec.transport != "openai":
        return list(config.spec.suggested_models)
    data = _get(f"{config.endpoint}/models",
                {"Authorization": f"Bearer {config.api_key.strip()}"
                 if config.api_key.strip() else ""}, config.timeout)
    items = data.get("data") or data.get("models") or []
    out = []
    for it in items:
        name = it.get("id") or it.get("name") if isinstance(it, dict) else str(it)
        if name:
            out.append(str(name))
    return sorted(out)


def test_connection(config: LLMConfig) -> str:
    """Send a trivial prompt so a bad URL, key, or model surfaces immediately."""
    reply = ask_llm("Reply with the single word: ready.",
                    "=== CONTEXT ===\n(none -- this is a connection test)",
                    config)
    return reply or "(empty reply)"


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------


def _fmt_money(v: Any) -> str:
    try:
        return f"{float(v):,.2f}"
    except (TypeError, ValueError):
        return str(v)


def build_context(
    *,
    business: str,
    industry_name: str,
    industry_asc: str,
    df: Any = None,
    plan: Any = None,
    result: Any = None,
    impacts: Optional[List[Any]] = None,
    unanswered: Optional[Dict[str, str]] = None,
    citations: Optional[Dict[str, str]] = None,
    assumptions: Optional[List[str]] = None,
) -> str:
    """A compact factual brief: computed figures, bindings, rules, open questions.

    Deliberately excludes the raw rows. The model's job is to explain a computed
    result; handing it the underlying data invites arithmetic the deterministic
    layer has already done correctly.
    """
    lines: List[str] = ["=== CONTEXT (all figures already computed) ===", ""]
    lines.append(f"Business: {business}")
    lines.append(f"Industry regime: {industry_name} (ASC {industry_asc})")

    if df is not None:
        lines.append(f"Data: {len(df):,} rows, {len(df.columns)} columns")

    if result is not None:
        lines += [
            "",
            "REVENUE (computed deterministically):",
            f"  Before accounting adjustments: {_fmt_money(result.unadjusted)}",
            f"  Excluded by approved rules:    {_fmt_money(result.deducted)}",
            f"  Reported revenue:              {_fmt_money(result.adjusted)}",
            f"  Read from column:              {result.revenue_column}",
            f"  Dated by column:               {result.period_column or 'n/a'}",
        ]
        if result.tax_columns:
            lines.append("  Sales tax columns excluded:    "
                         f"{', '.join(result.tax_columns)}")
        if result.contra_columns:
            lines.append("  Contra-revenue columns:        "
                         f"{', '.join(result.contra_columns)}")
        try:
            lines.append("")
            lines.append("BY PERIOD (before adjustments / excluded / reported):")
            for idx, row in result.by_period.iterrows():
                lines.append(
                    f"  {idx}: {_fmt_money(row['revenue'])} / "
                    f"{_fmt_money(row['excluded'])} / {_fmt_money(row['reported'])}")
        except Exception:                          # pragma: no cover - defensive
            pass

    if impacts:
        lines.append("")
        lines.append("ACCOUNTING RULES EVALUATED AGAINST THIS DATA:")
        for im in impacts:
            state = {"ratified": "APPROVED - already deducted",
                     "candidate": "PENDING the user's decision - NOT deducted",
                     "rejected": "REJECTED by the user - kept in revenue"}.get(
                         im.status, im.status)
            lines.append(
                f"  - {im.rule.name}: {_fmt_money(im.amount or 0)} across "
                f"{im.row_count} line(s). {state}. "
                f"ASC {im.rule.citation}. {im.rule.requirement}")

    if plan is not None:
        try:
            lines.append("")
            lines.append("COLUMN MEANINGS:")
            for b in plan.bindings:
                if b.concept not in ("unknown", "label"):
                    lines.append(f"  {b.column} -> {b.concept}")
        except Exception:                          # pragma: no cover - defensive
            pass

    if citations:
        lines.append("")
        lines.append("ASC PARAGRAPHS AVAILABLE TO CITE (cite no others):")
        for key, requirement in citations.items():
            lines.append(f"  ASC {key}: {requirement}")

    if assumptions:
        lines.append("")
        lines.append("ASSUMPTIONS THE USER HAS SUPPLIED IN THIS CONVERSATION:")
        for item in assumptions:
            lines.append(f"  - {item}")
        lines.append("  The deterministic engine can already compute revenue, "
                     "cost, gross profit and margin by period from these — "
                     "tell the user to ask for 'profitability by month' rather "
                     "than working the figures out yourself.")

    if unanswered:
        lines.append("")
        lines.append("FACTS THE USER HAS NOT YET SUPPLIED (do not assume these):")
        for key, question in unanswered.items():
            lines.append(f"  - {key}: {question}")

    return "\n".join(lines)
