def generate_markdown_report(execution_results: list[dict]) -> str:
    """
    Generate a Markdown report summarizing the complete search evaluation results.

    Args:
        execution_results: List of evaluation results.

    Returns:
        Markdown report as a string.
    """
    total = len(execution_results)
    sufficient = sum(result["sufficient"] for result in execution_results)
    insufficient = total - sufficient
    sufficiency_rate = (sufficient / total * 100) if total else 0

    avg_confidence = (
        sum(result["confidence"] for result in execution_results) / total
        if total else 0
    )

    report = [
        "# Complete Search Evaluation Report",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Total Test Cases | {total} |",
        f"| Sufficient | {sufficient} |",
        f"| Insufficient | {insufficient} |",
        f"| Sufficiency Rate | {sufficiency_rate:.2f}% |",
        f"| Average Confidence | {avg_confidence:.2f} |",
        "",
        "---",
        "",
        "## Individual Results",
        "",
        "| # | Sufficient | Confidence | Query |",
        "|--:|:----------:|-----------:|-------|",
    ]

    insufficient_cases = []

    for i, result in enumerate(execution_results, start=1):
        report.append(
            f"| {i} | "
            f"{result['sufficient']} | "
            f"{result['confidence']:.2f} | "
            f"{result['query']} |"
        )

        if not result["sufficient"]:
            insufficient_cases.append(result)

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

    return "\n".join(report)