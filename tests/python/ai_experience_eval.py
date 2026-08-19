from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR))

import server  # noqa: E402


DEFAULT_CASES = PROJECT_DIR / "tests" / "evals" / "zh_ai_npc_cases.json"
IMPLEMENTATION_TERMS = ("白名单", "目标 ID", "目标id", "JSON", "系统提示", "prompt", "候选动作", "游戏中", "玩家")
PUZZLE_ANSWER_PHRASES = ("正确的是", "应该接", "答案是", "就接蓝", "就接红", "就接黄")


def _payload(case: dict[str, Any]) -> dict[str, Any]:
    state = {
        "room_id": "relay_control",
        "room_name": "中继控制室",
        "oxygen": 80,
        "stress": "tense",
        "physical_state": "左肩受伤，抬臂受限。",
        "trust": 50,
        "fear": 40,
    }
    state.update(case.get("state", {}))
    actions = case.get(
        "actions",
        [
            {"action": "inspect", "target": "telemetry_console", "label": "检查遥测台", "enabled": True, "dangerous": False},
            {"action": "take", "target": "phase_fuse", "label": "拾取相位保险芯", "enabled": True, "dangerous": False},
        ],
    )
    beliefs = case.get("beliefs", [])
    memories = case.get("memories", [])
    return {
        "player_text": case["prompt"],
        "state": state,
        "visible_observations": case.get("visible_observations", [f"当前位于{state['room_name']}。"]),
        "valid_actions": actions,
        "history": case.get("history", [{"role": "npc", "content": "调度，我还在线。"}]),
        "conversation_memory": {"player_name": "", "promises": []},
        "context_protocol": {
            "turn_id": f"eval:{case['id']}",
            "snapshot_version": 1,
            "character_core": {
                "id": "lin_lan",
                "name": "林岚",
                "role": "K-17 维护技术员",
                "long_term_goal": "活着离开设施，并让每一步维修都有证据。",
                "default_strategy": "先报告亲眼所见，再区分转述和事实。",
                "voice": "受伤、克制、具体；先回应，再补一个感官细节。",
                "stable_boundaries": ["不替调度员猜谜题", "不把转述当事实"],
            },
            "active_scene_mode": {
                "id": "field_maintenance",
                "trigger": "eval",
                "energy": "strained",
                "emotion": state.get("stress", "focused"),
                "behavior_rules": ["短句", "第一人称", "只说局部所见"],
            },
            "current_scene": {
                "room_id": state["room_id"],
                "room_name": state["room_name"],
                "local_observation": "设施受损，通讯仍可用。",
                "physical_state": state.get("physical_state", ""),
                "oxygen": state.get("oxygen", 80),
                "visible_observations": case.get("visible_observations", []),
            },
            "known_beliefs": beliefs,
            "relevant_memories": memories,
            "relationship_state": {"trust": state.get("trust", 50), "fear": state.get("fear", 40)},
            "director_intent": {
                "goal": "直接回应本轮问题，不泄露隐藏答案，不擅自动作。",
                "urgency": "eval",
                "priority": 50,
                "preconditions": ["mission_active"],
                "forbidden_moves": ["猜谜题答案", "使用界面术语"],
                "ttl_turns": 1,
                "max_mentions": 1,
                "cooldown_turns": 0,
            },
            "recent_dialogue": case.get("history", []),
        },
        "prompt_trace": {"trace_id": f"eval:{case['id']}", "template_version": "blindspot-context-v2", "snapshot_version": 1},
    }


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _bigrams(text: str) -> set[str]:
    compact = "".join(text.split())
    return {compact[index : index + 2] for index in range(max(0, len(compact) - 1))}


def _similarity(left: str, right: str) -> float:
    left_parts, right_parts = _bigrams(left), _bigrams(right)
    if not left_parts or not right_parts:
        return 0.0
    return len(left_parts & right_parts) / len(left_parts | right_parts)


def _score_case(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    decision = result.get("decision", {})
    reply = str(decision.get("reply", ""))
    references = set(decision.get("referenced_ids", []))
    checks: dict[str, bool] = {}
    expected_action = case.get("expected_action")
    if expected_action is not None:
        checks["action"] = str(decision.get("action", "none")) == expected_action
    if case.get("expected_target") is not None:
        checks["target"] = str(decision.get("target", "")) == case["expected_target"]
    required_any = case.get("required_any", [])
    if required_any:
        checks["required_any"] = any(fragment in reply for fragment in required_any)
    required_all = case.get("required_all", [])
    if required_all:
        checks["required_all"] = all(fragment in reply for fragment in required_all)
    forbidden = case.get("forbidden_any", [])
    if forbidden:
        checks["forbidden"] = not any(fragment.lower() in reply.lower() for fragment in forbidden)
    required_references = set(case.get("required_references", []))
    if required_references:
        checks["references"] = required_references <= references
    checks["terminology"] = not any(term.lower() in reply.lower() for term in IMPLEMENTATION_TERMS)
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "reply": reply,
        "intent": decision.get("intent", ""),
        "action": decision.get("action", "none"),
        "target": decision.get("target", ""),
        "mood": decision.get("mood", ""),
        "referenced_ids": sorted(references),
    }


def run_live(cases: list[dict[str, Any]], output_path: Path | None = None) -> dict[str, Any]:
    settings = server.load_settings()
    if not settings.configured:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    latencies: list[float] = []
    rows: list[dict[str, Any]] = []
    provider_counts: Counter[str] = Counter()
    session_counts: Counter[str] = Counter()
    session_costs: Counter[str] = Counter()
    input_tokens = 0
    output_tokens = 0
    online_failures = 0
    input_price_raw = os.getenv("BLINDSPOT_INPUT_USD_PER_M", "").strip()
    output_price_raw = os.getenv("BLINDSPOT_OUTPUT_USD_PER_M", "").strip()
    pricing_configured = bool(input_price_raw and output_price_raw)
    input_price = float(input_price_raw) if pricing_configured else 0.0
    output_price = float(output_price_raw) if pricing_configured else 0.0

    for case in cases:
        started = time.perf_counter()
        try:
            result = server.decide(_payload(case), settings)
        except Exception as exc:  # The report needs a failure row instead of aborting the session.
            latency = (time.perf_counter() - started) * 1000.0
            latencies.append(latency)
            online_failures += 1
            rows.append({"id": case["id"], "category": case["category"], "session": case["session"], "passed": False, "error": type(exc).__name__, "latency_ms": round(latency, 1)})
            continue
        latency = (time.perf_counter() - started) * 1000.0
        latencies.append(latency)
        provider = str(result.get("provider", "unknown"))
        provider_counts[provider] += 1
        usage = result.get("usage", {}) if isinstance(result.get("usage", {}), dict) else {}
        case_input = int(usage.get("input_tokens", 0))
        case_output = int(usage.get("output_tokens", 0))
        input_tokens += case_input
        output_tokens += case_output
        cost = case_input * input_price / 1_000_000.0 + case_output * output_price / 1_000_000.0
        session = str(case.get("session", "default"))
        session_counts[session] += 1
        session_costs[session] += cost
        scored = _score_case(case, result)
        scored.update({"id": case["id"], "category": case["category"], "session": session, "provider": provider, "latency_ms": round(latency, 1), "usage": usage, "estimated_cost_usd": round(cost, 6) if pricing_configured else None})
        rows.append(scored)

    successful_rows = [row for row in rows if "error" not in row]
    category_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in successful_rows:
        category_rows[str(row["category"])].append(row)
    repeat_groups: dict[str, list[str]] = defaultdict(list)
    by_id = {case["id"]: case for case in cases}
    for row in successful_rows:
        group = by_id[row["id"]].get("repeat_group")
        if group:
            repeat_groups[str(group)].append(str(row.get("reply", "")))
    repetition_pairs: list[float] = []
    for replies in repeat_groups.values():
        for index in range(1, len(replies)):
            repetition_pairs.append(_similarity(replies[index - 1], replies[index]))

    def pass_rate(categories: tuple[str, ...]) -> float:
        selected = [row for category in categories for row in category_rows.get(category, [])]
        return sum(bool(row.get("passed")) for row in selected) / len(selected) if selected else 0.0

    fact_rows = category_rows.get("fact_reference", [])
    puzzle_rows = category_rows.get("puzzle_leak", [])
    action_rows = category_rows.get("action", [])
    term_leaks = sum(any(term.lower() in str(row.get("reply", "")).lower() for term in IMPLEMENTATION_TERMS) for row in successful_rows)
    puzzle_leaks = sum(str(row.get("action", "none")) != "none" or any(phrase in str(row.get("reply", "")) for phrase in PUZZLE_ANSWER_PHRASES) for row in puzzle_rows)
    action_errors = sum(not bool(row.get("checks", {}).get("action", True)) for row in action_rows)
    fact_correct = sum(bool(row.get("checks", {}).get("references", False)) and bool(row.get("checks", {}).get("required_all", True)) for row in fact_rows)
    total_cost = input_tokens * input_price / 1_000_000.0 + output_tokens * output_price / 1_000_000.0
    report = {
        "model": settings.model,
        "case_count": len(cases),
        "passed": sum(bool(row.get("passed")) for row in rows),
        "metrics": {
            "persona_consistency_rate": round(pass_rate(("persona", "relationship", "memory")), 4),
            "fact_reference_accuracy": round(fact_correct / len(fact_rows), 4) if fact_rows else 0.0,
            "puzzle_leak_rate": round(puzzle_leaks / len(puzzle_rows), 4) if puzzle_rows else 0.0,
            "action_misproposal_rate": round(action_errors / len(action_rows), 4) if action_rows else 0.0,
            "repetition_rate": round(sum(value >= 0.78 for value in repetition_pairs) / len(repetition_pairs), 4) if repetition_pairs else 0.0,
            "repetition_similarity_mean": round(statistics.mean(repetition_pairs), 4) if repetition_pairs else 0.0,
            "terminology_leak_rate": round(term_leaks / len(successful_rows), 4) if successful_rows else 0.0,
            "latency_p50_ms": round(_percentile(latencies, 0.50), 1),
            "latency_p95_ms": round(_percentile(latencies, 0.95), 1),
            "average_requests_per_session": round(statistics.mean(session_counts.values()), 2) if session_counts else 0.0,
            "average_cost_per_session_usd": round(statistics.mean(session_costs.values()), 6) if pricing_configured and session_costs else None,
            "online_failure_rate": round(online_failures / len(cases), 4) if cases else 0.0,
            "local_fallback_ratio": round(sum(count for provider, count in provider_counts.items() if provider != "openai") / len(cases), 4) if cases else 0.0,
        },
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens, "estimated_cost_usd": round(total_cost, 6) if pricing_configured else None, "pricing_configured": pricing_configured},
        "providers": dict(provider_counts),
        "cases": rows,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Blindspot's live Chinese AI NPC experience evaluation")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--out", type=Path, default=PROJECT_DIR / "artifacts" / "ai_experience_eval.json")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--live", action="store_true", help="make real model requests; omitted mode only validates the dataset")
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise SystemExit("evaluation dataset must be a non-empty JSON array")
    if args.limit > 0:
        cases = cases[: args.limit]
    if not args.live:
        print(json.dumps({"ok": True, "case_count": len(cases), "message": "dataset valid; pass --live to spend model requests"}, ensure_ascii=False))
        return
    report = run_live(cases, args.out)
    print(json.dumps({"model": report["model"], "case_count": report["case_count"], "passed": report["passed"], "metrics": report["metrics"], "usage": report["usage"], "report": str(args.out)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
