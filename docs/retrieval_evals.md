# Retrieval Evaluation Methodology

## Purpose

This document defines the evaluation methodology for the retrieval stage of the Legal Copilot system.

The primary objective of evaluation is not to maximize arbitrary metrics, but to provide actionable feedback for improving the system. Every evaluation should clearly indicate which component requires improvement when performance degrades.

The retrieval pipeline consists of two independent components:

1. Complete Search
2. Retrieval Agent

These components have different responsibilities and are therefore evaluated independently.

This separation follows the overall architecture of the system, where each component has a single responsibility and communicates through well-defined interfaces.

---

# Evaluation Philosophy

The evaluation methodology follows several guiding principles.

## Evaluate Responsibilities, Not the Entire Pipeline

Each component should only be evaluated against the responsibility it owns.
The Complete Search is responsible for finding candidate evidence.
The Retrieval Agent is responsible for selecting sufficient evidence from those candidates.
Neither component should be evaluated for responsibilities that belong to another stage of the pipeline.

---

## Every Metric Must Support Engineering Decisions

Metrics are collected only if they help answer the question:

> What component should be improved next?

The evaluation intentionally avoids collecting a large number of metrics that provide little practical value.
Instead, it focuses on a small number of measurements that directly support debugging and system improvement.

---

## Sufficiency Over Completeness

The Legal Copilot is not designed to retrieve every relevant document.
Its objective is to retrieve enough evidence for the downstream Answer Synthesizer to produce a complete and accurate answer.
This distinction is fundamental.
A retrieval result is considered successful when it contains sufficient evidence, even if additional relevant chunks exist elsewhere in the corpus.

The system therefore optimizes for **minimal sufficient evidence**, not maximum evidence coverage.

---

# Evaluation Structure

The retrieval stage is evaluated through two independent evaluations.

| Evaluation                 | Component       | Primary Question                                                                                      |
| -------------------------- | --------------- | ----------------------------------------------------------------------------------------------------- |
| Complete Search Evaluation | Complete Search | Was the necessary evidence retrieved into the candidate set?                                          |
| Retrieval Agent Evaluation | Retrieval Agent | Given the candidate set, did the agent return sufficient evidence while avoiding unnecessary context? |

These evaluations intentionally measure different responsibilities.

---

# Evaluation 1 — Complete Search

## Purpose

The purpose of this evaluation is to measure retrieval recall.
The Complete Search does not need to identify the final evidence.
Its responsibility is simply to ensure that the evidence required to answer the question appears somewhere within the retrieved candidate set.
If the required evidence is present, the Complete Search has fulfilled its responsibility.
Filtering irrelevant information is not the responsibility of this stage.

---

## Evaluation Dataset

The evaluation dataset consists of a list of legal queries.
Each evaluation sample contains:

* user query

For each query, the Complete Search is executed and the retrieved candidate set is passed to an LLM judge together with the query.
The judge assesses whether the candidate set contains the relevant information needed to answer the question.

---

## Evaluation Procedure

For every evaluation query:

1. Execute the Complete Search.
2. Collect the retrieved candidate chunk identifiers and associated content.
3. Pass the query and the retrieved candidate set to an LLM judge.
4. Ask the judge to determine whether the candidate set contains the relevant evidence needed to answer the query.
5. Record the structured judgment produced by the judge according to the predefined evaluation schema.

The objective is to determine whether the required evidence entered the candidate set from the perspective of an independent judge.
This evaluation does not rely on simple rule-based matching against predefined chunk identifiers.
Instead, it evaluates whether the candidate set is sufficient for downstream reasoning.

---

## Success Criterion

The Complete Search succeeds when the LLM judge determines that the retrieved candidate set contains relevant evidence for the query.
It is acceptable for additional irrelevant candidates to appear in the results.
High recall remains preferable to aggressive filtering because the Retrieval Agent performs evidence selection later in the pipeline.

---

# Evaluation 2 — Retrieval Agent

## Purpose

The Retrieval Agent sits between Complete Search and the Answer Synthesizer.

Its responsibility is to examine the evidence returned by Complete Search, determine whether enough evidence is available, and select a focused set of chunks for downstream synthesis.

The system only sends the selected evidence to the Answer Synthesizer when the Retrieval Agent determines that the evidence is sufficient. Therefore, the primary evaluation question is:

> **When the Retrieval Agent says the evidence is sufficient, is it actually sufficient to answer the user's question?**

A secondary objective is to evaluate how focused the selected evidence is and whether it contains unnecessary or distracting chunks.

The evaluation is performed at the **chunk level**. Information that is unnecessary within an otherwise useful chunk is not penalized because the system selects and passes complete chunks rather than individual portions of chunks.

---

## Evaluation Philosophy

The Retrieval Agent is not evaluated by comparing its output against a predefined set of "correct" chunk IDs.

Multiple different combinations of chunks may contain sufficient evidence to answer the same question. Requiring the agent to select one exact set of chunks would therefore incorrectly penalize valid retrieval decisions.

Instead, evaluation focuses on the **quality of the final selected evidence**:

1. Does the selected evidence contain everything necessary to answer the question?
2. Is the selected evidence reasonably focused, without an excessive number of unnecessary chunks?

This reflects the actual role of the Retrieval Agent in the production pipeline.

---

## Evaluation Metrics

### 1. Evidence Sufficiency

Sufficiency is the primary metric.

The judge determines whether the selected chunks collectively contain enough evidence for the Answer Synthesizer to answer **all material aspects** of the user's question.

A result is considered sufficient when:

* the necessary evidence is present across the selected chunks;
* all material aspects of the query can be addressed;
* no important information has been omitted from the selected evidence.

Minor missing details that would not meaningfully change the answer do not make a result insufficient.

The evaluation does not assess the quality of the final synthesized answer. It only determines whether the selected evidence is sufficient to support one.

### 2. Focus

Focus measures whether the Retrieval Agent selects unnecessary or distracting chunks in addition to the evidence required to answer the question.

A chunk may be relevant to the broader topic but still be unnecessary for answering the specific query. Such a chunk is considered **relevant-but-unnecessary**, rather than irrelevant.

The evaluation therefore distinguishes between:

* **Necessary chunks** — required to answer the question.
* **Relevant-but-unnecessary chunks** — useful or related information that is not required to answer the current question.
* **Distracting chunks** — chunks that provide little or no meaningful value for the current question.

A small number of relevant-but-unnecessary chunks is acceptable. The selection becomes unfocused when unnecessary or distracting chunks constitute a substantial portion of the selected set. In particular, when more than half of the selected chunks are relevant-but-unnecessary or distracting, the result is considered unfocused.

This assessment is performed strictly at the **chunk level**. Unnecessary information contained within a selected chunk is not separately penalized.

---

## Evaluation Dataset

The evaluation dataset consists of **real-world Retrieval Agent outputs** produced by running  user queries through the system.

The process used to construct the dataset is:

1. Select a set of evaluation queries.
2. Run the queries through the retrieval agent.
3. Collect the Retrieval Agent's outputs and selected chunks.
4. Keep only cases where the Retrieval Agent itself returned `sufficient=true`.
5. Exclude cases where the Retrieval Agent returned `sufficient=false`.

This filtering is intentional.

The production system only forwards evidence to the Answer Synthesizer when the Retrieval Agent claims that the evidence is sufficient. Therefore, the evaluation specifically tests the reliability of this decision:

> **When the Retrieval Agent claims sufficiency, is that claim actually correct?**

The resulting dataset therefore represents real Retrieval Agent behavior under the same conditions encountered during normal system execution.

Each retained evaluation sample contains:

* user query;
* Retrieval Agent's selected internal chunks, if any;
* Retrieval Agent's selected external chunks, if any;
* the corresponding chunk content.

The Retrieval Agent's original sufficiency decision is retained as the basis for constructing the evaluation dataset, but the LLM Judge independently determines whether the selected evidence is actually sufficient.

---

## Evaluation Procedure

For every evaluation sample:

1. Take the original user query.
2. Provide the selected chunks produced by the Retrieval Agent to the evaluator.
3. Evaluate the selected chunks collectively.
4. Determine whether the evidence is sufficient to answer all material aspects of the query.
5. Determine whether the selected chunk set is focused or contains excessive unnecessary evidence.
6. Record the evaluator's confidence and concise reasoning.

The evaluator does not receive the original Complete Search candidate set.

This is intentional: the evaluation is focused on the **final evidence passed downstream**, rather than on how effectively the Retrieval Agent filtered the original candidate set.

---

# LLM Judge Calibration

## Purpose

An LLM Judge is used to automate the evaluation of Retrieval Agent outputs.

Before using the judge for the larger evaluation dataset, its ability to identify insufficient evidence must be tested through a calibration process.

The calibration is particularly important because the production evaluation dataset contains only cases where the Retrieval Agent itself claims `sufficient=true`. The judge must therefore be capable of identifying cases where the agent's sufficiency decision is incorrect.

---

## Calibration Dataset

The calibration dataset contains **15 mocked Retrieval Agent results**.

These samples are not generated by the Retrieval Agent. Instead, they are manually constructed to follow the same output structure and format that the Retrieval Agent would produce.

The dataset intentionally contains a mixture of:

* sufficient and focused selections;
* sufficient but unnecessarily broad selections;
* insufficient selections;
* cases where the evidence is insufficient even though the mocked Retrieval Agent output is explicitly labeled `sufficient=true`.

The final category is particularly important.

Because the production system relies on the Retrieval Agent's `sufficient=true` decision before forwarding evidence to the Answer Synthesizer, the judge must demonstrate that it can **challenge an incorrect sufficiency claim** rather than simply agreeing with the agent's label.

The mocked labels therefore act as controlled test conditions rather than ground truth supplied to the judge.

---

## Human Evaluation

Each calibration sample is independently reviewed by a human evaluator.

The human evaluator determines:

* whether the selected evidence is sufficient;
* whether the selected chunks are focused;
* the reasoning supporting the decision.

These human judgments serve as the reference for evaluating the LLM Judge.

---

## LLM Judge Evaluation

The LLM Judge receives only:

* the user query;
* the selected chunk contents.

It does not receive the Retrieval Agent's sufficiency label or internal reasoning.

The judge independently produces:

* `sufficient`;
* `focused`;
* `confidence`;
* concise reasoning.

This prevents the judge from simply reproducing or anchoring on the Retrieval Agent's original decision.

---

## Calibration Objective

The objective is to verify that the LLM Judge can reliably distinguish between:

* genuinely sufficient evidence;
* evidence that is missing a material aspect of the question;
* focused selections;
* selections containing excessive unnecessary or distracting chunks.

Particular attention is given to **false sufficiency cases**, where the Retrieval Agent claims `sufficient=true` even though the selected evidence is not sufficient.

Once the judge demonstrates acceptable agreement with human evaluation, it can be used to evaluate the larger real-world Retrieval Agent dataset.

---

# What Is Considered Success?

The Retrieval Agent's ideal behavior is:

> **Select enough chunks to completely support the answer while avoiding unnecessary chunks.**

A successful result therefore has two properties:

1. **Sufficient** — the selected chunks contain all evidence necessary to answer the user's question.
2. **Focused** — the selected chunk set does not contain an excessive amount of unnecessary or distracting evidence.

The agent does **not** need to select every relevant chunk. If two chunks completely support the answer and a third chunk only provides additional background information, selecting the third chunk is unnecessary but does not automatically constitute failure.

Likewise, information that is unnecessary inside a selected chunk is not penalized because evaluation operates at the chunk level.

The primary failure mode is **insufficient evidence**: if the Retrieval Agent claims that the evidence is sufficient but has omitted a material piece of information required to answer the query, the result is considered insufficient.

The secondary failure mode is **poor focus**: if the selected set contains too many unnecessary or distracting chunks, the result is considered unfocused.

Together, these metrics measure whether the Retrieval Agent provides the Answer Synthesizer with evidence that is both **complete and appropriately focused**.

---

# LLM Judge Calibration Strategy

Both Complete Search and Retrieval Agent are evaluated using an LLM Judge, but calibration is applied only to the Retrieval Agent evaluation.

### Complete Search

The Complete Search evaluation asks a relatively simple question:

> **Does the candidate set contain sufficient evidence to answer the user's question?**

The judge only needs to determine whether the required evidence exists somewhere within the candidate set. It does not need to select chunks, assess minimality, or evaluate focus. Because this is a straightforward evidence-presence task with limited reasoning complexity, separate judge calibration was not considered necessary.

### Retrieval Agent

The Retrieval Agent evaluation is more complex. The judge must determine whether the **selected chunks themselves** are sufficient and whether the selection is sufficiently focused without excessive unnecessary or distracting chunks.

Because this requires more nuanced judgment, the LLM Judge was calibrated using a controlled set of mocked Retrieval Agent results and human evaluations before being used on the larger evaluation dataset.

---

# Design Principles

The evaluation methodology follows several architectural principles.

## Component Independence

Each evaluation measures only the responsibility assigned to that component.
Complete Search is evaluated independently from Retrieval Agent reasoning.

---

## Contract-Based Evaluation

Each component is evaluated against the contract it provides to the next stage of the pipeline.
Complete Search promises that necessary evidence is present in the candidate set.
The Retrieval Agent promises that the selected evidence is sufficient for answer generation.

---

## Evidence Sufficiency

Success is measured by evidence sufficiency rather than document completeness.
The system seeks enough evidence to answer the user's question, not every piece of related information.

---

## Practical Engineering

The evaluation methodology intentionally favors simplicity.
Rather than collecting numerous metrics, the evaluation focuses on measurements that directly inform engineering decisions and system improvements.
The objective is to create an evaluation process that remains understandable, maintainable, and useful throughout the continued development of the Legal Copilot.
