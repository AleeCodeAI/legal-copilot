def generate_markdown_report(execution_results: list[dict]) -> str:
    """
    Generate a Markdown report summarizing Answer Synthesizer evaluation results.

    Args:
        execution_results: List of evaluation results.

    Returns:
        Markdown report as a string.
    """
    total = len(execution_results)

    normalized_results = []

    for r in execution_results:
        normalized_results.append(
            {
                "query": r.get("query", ""),
                "faithfulness": float(r.get("faithfulness", 0.0)),
                "completeness": float(r.get("completeness", 0.0)),
                "source_attribution": float(r.get("source_attribution", 0.0)),
                "verdict": str(r.get("final_verdict", "")).strip().upper(),
                "confidence": float(r.get("confidence", 0.0)),
                "reasoning": r.get("reasoning", ""),
            }
        )

    good_verdicts = sum(
        1 for r in normalized_results if r["verdict"] == "GOOD"
    )

    bad_verdicts = sum(
        1 for r in normalized_results if r["verdict"] == "BAD"
    )

    success_rate = (
        good_verdicts / total * 100
        if total
        else 0
    )

    avg_faithfulness = (
        sum(r["faithfulness"] for r in normalized_results) / total
        if total
        else 0
    )

    avg_completeness = (
        sum(r["completeness"] for r in normalized_results) / total
        if total
        else 0
    )

    avg_source_attribution = (
        sum(r["source_attribution"] for r in normalized_results) / total
        if total
        else 0
    )

    avg_confidence = (
        sum(r["confidence"] for r in normalized_results) / total
        if total
        else 0
    )

    report = [
        "# Answer Synthesizer Evaluation Report",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Total Test Cases | {total} |",
        f"| GOOD Verdicts | {good_verdicts} |",
        f"| BAD Verdicts | {bad_verdicts} |",
        f"| Success Rate | {success_rate:.2f}% |",
        f"| Average Faithfulness | {avg_faithfulness:.2f} |",
        f"| Average Completeness | {avg_completeness:.2f} |",
        f"| Average Source Attribution | {avg_source_attribution:.2f} |",
        f"| Average Confidence | {avg_confidence:.2f} |",
        "",
        "---",
        "",
        "## Individual Results",
        "",
        "| # | Verdict | Faithfulness | Completeness | Source Attribution | Confidence | Query |",
        "|--:|:-------:|-------------:|-------------:|-------------------:|-----------:|-------|",
    ]

    bad_cases = []

    for i, result in enumerate(normalized_results, start=1):
        report.append(
            f"| {i} | "
            f"{result['verdict']} | "
            f"{result['faithfulness']:.2f} | "
            f"{result['completeness']:.2f} | "
            f"{result['source_attribution']:.2f} | "
            f"{result['confidence']:.2f} | "
            f"{result['query']} |"
        )

        if result["verdict"] == "BAD":
            bad_cases.append(result)

    if bad_cases:
        report.extend(
            [
                "",
                "---",
                "",
                "## Bad Evaluations (Failed Cases)",
                "",
                "| Query | Faithfulness | Completeness | Source Attribution | Reasoning |",
                "|-------|-------------:|-------------:|-------------------:|-----------|",
            ]
        )

        for result in bad_cases:
            safe_reasoning = result["reasoning"].replace("\n", "<br>")

            report.append(
                f"| {result['query']} | "
                f"{result['faithfulness']:.2f} | "
                f"{result['completeness']:.2f} | "
                f"{result['source_attribution']:.2f} | "
                f"{safe_reasoning} |"
            )

    return "\n".join(report)