# Evaluation Methodology: Answer Synthesizer Assessment

## Overview

The Answer Synthesizer is the final component of the legal research pipeline. Its responsibility is to transform the evidence selected by the Retrieval Agent into a coherent, professional, and legally appropriate response for the user.

Unlike the retrieval stage, which focuses on identifying relevant evidence, the Answer Synthesizer is responsible for generating the final natural language output. Because this component produces free-form text, traditional evaluation methods based on exact matching are insufficient.

To evaluate the quality of generated responses, an **LLM-as-a-Judge** evaluation framework was implemented.

The objective of this evaluation was to determine whether the Answer Synthesizer produces responses that are:

* Faithful to the retrieved evidence
* Complete with respect to the available information
* Properly attributed to the correct sources

---

## Answer Synthesizer Workflow

The evaluation begins after the Retrieval Agent has completed its execution.

The Retrieval Agent returns a structured `RetrievalResult` object containing:

* Whether the retrieved evidence is considered sufficient
* The selected chunk identifiers
* A confidence score
* A brief explanation of the retrieval decision
* An optional refined query for future retrieval iterations

```python
class RetrievalResult(BaseModel):
    sufficient: Literal["True", "False"]
    selected_chunks: List[str]
    confidence: float
    reasoning: str
    refined_query: str | None
```

The selected chunk IDs are then used to retrieve the corresponding documents from the database.

These retrieved chunks are passed to the Answer Synthesizer, which generates the final response.

The Answer Synthesizer returns the following output schema:

```python
class Answer(BaseModel):
    answer: str | None
    reasoning_summary: str
```

The generated answer is then passed to the evaluation pipeline.

---

## Evaluation Approach

The Answer Synthesizer was evaluated using an **LLM-as-a-Judge** approach.

The judge does not answer legal questions and does not provide legal advice. Its only responsibility is to evaluate the quality of the generated response.

The judge receives three inputs:

* The user's query
* The retrieved evidence
* The generated answer

The judge is explicitly restricted to these inputs and is prohibited from introducing any external legal knowledge during evaluation.

This restriction ensures that the evaluation measures only the quality of the Answer Synthesizer rather than the legal knowledge of the evaluation model itself.

---

## Judge Calibration

Because the evaluation process relies on one AI system to evaluate another AI system, a judge calibration step was performed before adopting the LLM-as-a-Judge methodology.

The purpose of judge calibration was to determine whether the AI judge produced evaluations that aligned with human judgment.

### Calibration Procedure

1. Twenty mock Answer Synthesizer outputs were manually created.
2. The dataset intentionally included both high-quality and low-quality examples.
3. Some examples deliberately contained errors, omissions, unsupported claims, and source attribution issues.
4. The same evaluation dataset was independently reviewed by:

   * A human evaluator
   * The LLM judge
5. Both sets of evaluations were recorded in an Excel spreadsheet.
6. The results were compared to measure the percentage of agreement between the human evaluator and the AI judge.

After achieving an acceptable level of alignment, the LLM judge was considered sufficiently reliable for automated evaluation.

The calibration spreadsheet is included in the project codebase for transparency and reproducibility.

---

## Evaluation Criteria

The Answer Synthesizer was evaluated using three independent criteria.

Each criterion receives a score between **0.0 and 1.0**.

### 1. Faithfulness

Faithfulness measures whether the generated answer is fully supported by the retrieved evidence.

The evaluation considers the following questions:

* Is the answer grounded in the retrieved evidence?
* Does the answer avoid unsupported claims?
* Does the answer avoid introducing outside knowledge?
* Does the answer accurately represent the retrieved evidence?

Any unsupported claim is considered a material violation and significantly reduces the faithfulness score.

---

### 2. Completeness

Completeness measures whether the generated answer adequately addresses the user's question using the available evidence.

The evaluation considers the following questions:

* Does the answer address the user's question?
* Does the answer include the materially important information contained in the retrieved evidence?
* Does the answer omit important facts that were available in the evidence?

The judge evaluates completeness only against the evidence that was actually retrieved.

The Answer Synthesizer is not penalized for information that was never retrieved by the retrieval pipeline.

---

### 3. Source Attribution

Source Attribution measures whether the generated answer clearly identifies the evidence supporting its claims.

The evaluation considers the following questions:

* Are sources clearly identified?
* Are sources correctly attributed?
* Are internal firm documents and external legal authorities clearly distinguished?

The evaluation does not require a citation after every sentence.

However, a reasonable reader should be able to identify which source supports a particular claim.

Answers receive lower scores when sources are missing, incorrectly attributed, or insufficiently distinguished.

---

## Structured Evaluation Procedure

The evaluation prompt was designed with an explicit, step-by-step reasoning process.

Defining the evaluation procedure inside the prompt was particularly important because legal evaluation requires consistent and reproducible decision-making.

The judge follows the following sequence:

1. Read and understand the user's query.
2. Review the retrieved evidence.
3. Identify the evidence relevant to the query.
4. Evaluate faithfulness.
5. Evaluate completeness.
6. Evaluate source attribution.
7. Generate an evaluation summary.
8. Assign a confidence score.

The prompt explicitly requires the judge to perform its analysis before producing any scores.

This structured approach was adopted to improve evaluation consistency and reduce arbitrary scoring.

---

## Reasoning Before Scoring

The evaluation prompt instructs the judge to explain its assessment before producing its final output.

However, the system does not expose chain-of-thought reasoning.

Instead, the judge produces a concise evaluation summary that explains:

* The assigned faithfulness score
* The assigned completeness score
* The assigned source attribution score
* Any important deficiencies identified in the generated answer

This approach improves interpretability while avoiding the exposure of internal reasoning.

---

## Evaluation Output

Each evaluated query produces the following structured result:

```json
{
    "query": "...",
    "faithfulness": 0.0,
    "completeness": 0.0,
    "source_attribution": 0.0,
    "overall_score": 0.0,
    "final_verdict": "...",
    "confidence": 0.0,
    "reasoning": "..."
}
```

The three evaluation criteria are first scored independently.

The system then performs a mathematical aggregation of these scores to calculate an overall score.

The final verdict is derived from this aggregated score rather than being directly assigned by the LLM judge.

---

## Reporting

All evaluation results are stored as structured JSON objects.

The complete set of evaluation results is automatically converted into a Markdown report to simplify analysis and comparison across multiple test cases.

The report includes:

* Individual criterion scores
* Overall scores
* Final verdicts
* Confidence scores
* Evaluation summaries

This reporting process provides a reproducible and scalable method for evaluating Answer Synthesizer performance across large evaluation datasets.
