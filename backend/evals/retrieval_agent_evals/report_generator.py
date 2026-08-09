def generate_markdown_report(execution_results: list[dict]) -> str:
    """
    Generate a Markdown report summarizing Retrieval Agent evaluation results.

    Args:
        execution_results: List of evaluation results.

    Returns:
        Markdown report as a string.
    """
    total = len(execution_results)

    # Normalize fields to boolean/float to prevent type errors from LLM string outputs
    normalized_results = []
    for r in execution_results:
        sufficient_val = r["sufficient"] if isinstance(r["sufficient"], bool) else str(r["sufficient"]).lower() == "true"
        focused_val = r["focused"] if isinstance(r["focused"], bool) else str(r["focused"]).lower() == "true"
        confidence_val = float(r.get("confidence", 0.0))

        normalized_results.append({
            "query": r.get("query", ""),
            "sufficient": sufficient_val,
            "focused": focused_val,
            "confidence": confidence_val,
            "reasoning": r.get("reasoning", "")
        })

    sufficient = sum(1 for r in normalized_results if r["sufficient"])
    focused = sum(1 for r in normalized_results if r["focused"])
    sufficient_and_focused = sum(1 for r in normalized_results if r["sufficient"] and r["focused"])

    insufficient = total - sufficient
    unfocused = total - focused

    sufficiency_rate = (sufficient / total * 100) if total else 0
    focus_rate = (focused / total * 100) if total else 0
    sufficient_and_focused_rate = (sufficient_and_focused / total * 100) if total else 0

    avg_confidence = (
        sum(r["confidence"] for r in normalized_results) / total
        if total else 0
    )

    report = [
        "# Retrieval Agent Evaluation Report",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Total Test Cases | {total} |",
        f"| Sufficient | {sufficient} |",
        f"| Insufficient | {insufficient} |",
        f"| Sufficiency Rate | {sufficiency_rate:.2f}% |",
        f"| Focused | {focused} |",
        f"| Unfocused | {unfocused} |",
        f"| Focus Rate | {focus_rate:.2f}% |",
        f"| Sufficient & Focused | {sufficient_and_focused} |",
        f"| Sufficient & Focused Rate | {sufficient_and_focused_rate:.2f}% |",
        f"| Average Confidence | {avg_confidence:.2f} |",
        "",
        "---",
        "",
        "## Individual Results",
        "",
        "| # | Sufficient | Focused | Confidence | Query |",
        "|--:|:----------:|:-------:|-----------:|-------|",
    ]

    insufficient_cases = []
    unfocused_cases = []

    for i, result in enumerate(normalized_results, start=1):
        report.append(
            f"| {i} | "
            f"{result['sufficient']} | "
            f"{result['focused']} | "
            f"{result['confidence']:.2f} | "
            f"{result['query']} |"
        )

        if not result["sufficient"]:
            insufficient_cases.append(result)

        if not result["focused"]:
            unfocused_cases.append(result)

    if insufficient_cases:
        report.extend([
            "",
            "---",
            "",
            "## Insufficient Evaluations",
            "",
            "| Query | Confidence | Reasoning |",
            "|-------|-----------:|-----------|",
        ])

        for result in insufficient_cases:
            report.append(
                f"| {result['query']} | "
                f"{result['confidence']:.2f} | "
                f"{result['reasoning']} |"
            )

    if unfocused_cases:
        report.extend([
            "",
            "---",
            "",
            "## Unfocused Evaluations",
            "",
            "| Query | Confidence | Reasoning |",
            "|-------|-----------:|-----------|",
        ])

        for result in unfocused_cases:
            report.append(
                f"| {result['query']} | "
                f"{result['confidence']:.2f} | "
                f"{result['reasoning']} |"
            )

    return "\n".join(report)

