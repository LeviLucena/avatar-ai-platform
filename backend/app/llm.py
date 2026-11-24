"""Provider-agnostic LLM wrapper: NVIDIA Nemotron (OpenAI-compatible NIM API) or Anthropic.

Every agent calls this wrapper and has a deterministic fallback, so the platform keeps
working (in "heuristic" mode) when no key is configured or the API fails.
Tool schemas are written once in Anthropic style ({name, description, input_schema}) and
converted for OpenAI-compatible providers here.
"""
import json
import logging
import re
from typing import Any, Callable

from .config import settings

log = logging.getLogger("llm")


class LLMUnavailable(RuntimeError):
    pass


_clients: dict[str, Any] = {}
_THINK = re.compile(r"<think>.*?</think>", re.S | re.I)


def is_live() -> bool:
    return settings.llm_live


def engine_name() -> str:
    return settings.engine_name


def _client():
    p = settings.provider
    if not p:
        raise LLMUnavailable("No LLM key configured (demo/heuristic mode)")
    if p not in _clients:
        if p == "nvidia":
            from openai import OpenAI

            _clients[p] = OpenAI(api_key=settings.nvidia_api_key, base_url=settings.nvidia_base_url,
                                 timeout=settings.nvidia_timeout, max_retries=2)
        else:
            import anthropic

            _clients[p] = anthropic.Anthropic(api_key=settings.anthropic_api_key, max_retries=2, timeout=60)
    return _clients[p]


def _clean(text: str | None) -> str:
    return _THINK.sub("", text or "").strip()


def _oa_tools(tools: list[dict]) -> list[dict]:
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}} for t in tools]


def _json_from_text(text: str) -> dict | None:
    text = _clean(text)
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    cand = fence.group(1) if fence else None
    if not cand:
        start, end = text.find("{"), text.rfind("}")
        cand = text[start:end + 1] if start != -1 and end > start else None
    try:
        return json.loads(cand) if cand else None
    except json.JSONDecodeError:
        return None


# ------------------------------------------------------------------ OpenAI-compatible (NVIDIA)
def _oa_chat(**kw):
    """chat.completions.create with thinking disabled when the server supports it."""
    c = _client()
    try:
        return c.chat.completions.create(extra_body={"chat_template_kwargs": {"enable_thinking": False}}, **kw)
    except Exception as exc:  # some deployments reject unknown template kwargs
        if "chat_template_kwargs" in str(exc) or "extra" in str(exc).lower():
            return c.chat.completions.create(**kw)
        raise


def _oa_structured(system: str, user: str, name: str, description: str, schema: dict, model: str, max_tokens: int) -> dict:
    tool = {"type": "function", "function": {"name": name, "description": description, "parameters": schema}}
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    for choice in ({"type": "function", "function": {"name": name}}, "auto"):
        try:
            resp = _oa_chat(model=model, messages=msgs, tools=[tool], tool_choice=choice, max_tokens=max_tokens, temperature=0)
        except Exception as exc:
            log.info("structured call with tool_choice=%s failed: %s", choice if isinstance(choice, str) else "forced", exc)
            continue
        m = resp.choices[0].message
        for tc in m.tool_calls or []:
            if tc.function.name == name:
                try:
                    return json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    pass
        parsed = _json_from_text(m.content or "")
        if parsed:
            return parsed
    # last resort: ask for plain JSON
    resp = _oa_chat(
        model=model, max_tokens=max_tokens, temperature=0,
        messages=[{"role": "system", "content": f"{system}\n\nReply with ONLY a JSON object matching this JSON schema:\n{json.dumps(schema)}"},
                  {"role": "user", "content": user}],
    )
    parsed = _json_from_text(resp.choices[0].message.content or "")
    if parsed:
        return parsed
    raise LLMUnavailable("Model returned no structured output")


def _oa_run_agent(system, messages, tools, call_tool, model, max_turns, max_tokens):
    msgs: list[dict] = [{"role": "system", "content": system}, *messages]
    trace: list[dict] = []
    oa = _oa_tools(tools)
    for _ in range(max_turns):
        resp = _oa_chat(model=model, messages=msgs, tools=oa, tool_choice="auto", max_tokens=max_tokens, temperature=0.2)
        m = resp.choices[0].message
        if not m.tool_calls:
            return _clean(m.content), trace
        msgs.append({"role": "assistant", "content": m.content or "",
                     "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in m.tool_calls]})
        for tc in m.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            try:
                out = call_tool(tc.function.name, args)
                trace.append({"tool": tc.function.name, "input": args, "ok": True, "rows": _size(out)})
                content = _to_text(out)
            except Exception as exc:  # permission errors are fed back to the model
                trace.append({"tool": tc.function.name, "input": args, "ok": False, "error": str(exc)})
                content = f"ERROR: {exc}"
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": content})
    return "I could not finish within the allowed number of steps.", trace


# ------------------------------------------------------------------ public API
def structured(*, system: str, user: str, name: str, description: str, schema: dict,
               model: str | None = None, max_tokens: int = 1024) -> dict:
    """Structured output via a forced tool call, validated against `schema` by the caller."""
    model = model or settings.model_fast
    if settings.provider == "nvidia":
        return _oa_structured(system, user, name, description, schema, model, max_tokens)
    resp = _client().messages.create(
        model=model, max_tokens=max_tokens, system=system, messages=[{"role": "user", "content": user}],
        tools=[{"name": name, "description": description, "input_schema": schema}],
        tool_choice={"type": "tool", "name": name},
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == name:
            return dict(block.input)
    raise LLMUnavailable("Model returned no structured output")


def complete(*, system: str, user: str, model: str | None = None, max_tokens: int = 1500) -> str:
    model = model or settings.model_smart
    if settings.provider == "nvidia":
        resp = _oa_chat(model=model, max_tokens=max_tokens, temperature=0.3,
                        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        text = _clean(resp.choices[0].message.content)
        if not text:
            raise LLMUnavailable("Empty completion")
        return text
    resp = _client().messages.create(model=model, max_tokens=max_tokens, system=system, messages=[{"role": "user", "content": user}])
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def run_agent(*, system: str, messages: list[dict], tools: list[dict], call_tool: Callable[[str, dict], Any],
              model: str | None = None, max_turns: int = 6, max_tokens: int = 1500) -> tuple[str, list[dict]]:
    """Tool-use loop. Returns (final_text, trace). `call_tool` must enforce permissions itself."""
    model = model or settings.model_smart
    if settings.provider == "nvidia":
        return _oa_run_agent(system, messages, tools, call_tool, model, max_turns, max_tokens)
    client = _client()
    msgs = list(messages)
    trace: list[dict] = []
    for _ in range(max_turns):
        resp = client.messages.create(model=model, max_tokens=max_tokens, system=system, messages=msgs, tools=tools)
        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text").strip(), trace
        msgs.append({"role": "assistant", "content": resp.content})
        results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            try:
                out = call_tool(block.name, dict(block.input))
                trace.append({"tool": block.name, "input": dict(block.input), "ok": True, "rows": _size(out)})
                content, is_error = _to_text(out), False
            except Exception as exc:
                trace.append({"tool": block.name, "input": dict(block.input), "ok": False, "error": str(exc)})
                content, is_error = f"ERROR: {exc}", True
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": content, "is_error": is_error})
        msgs.append({"role": "user", "content": results})
    return "I could not finish within the allowed number of steps.", trace


def _size(out: Any) -> int:
    return len(out) if isinstance(out, (list, dict)) else 1


def _to_text(out: Any) -> str:
    return json.dumps(out, default=str)[:12000]
