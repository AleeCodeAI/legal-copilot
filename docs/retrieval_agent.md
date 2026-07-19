# Retrieval Agent Design Guide

## Purpose

The Retrieval Agent is responsible for gathering sufficient evidence to answer a user's legal research question. It acts as an intelligent researcher that examines the available knowledge sources, determines whether additional information is required, and returns the evidence needed by the downstream Answer Synthesizer.

The Retrieval Agent does **not** generate legal advice or produce the final response. Its sole responsibility is evidence acquisition.

This strict separation of responsibilities is one of the fundamental architectural principles of the system. By isolating retrieval from answer generation, each component remains simpler, easier to evaluate, and easier to improve independently.

---

# Design Philosophy

The Retrieval Agent follows a single guiding principle:

> Retrieve sufficient evidence, not final answers.

Traditional Retrieval-Augmented Generation (RAG) systems often follow a fixed pipeline:

```
Search

↓

Generate Answer
```

This assumes that the first retrieval attempt always provides sufficient evidence. If retrieval fails, the generated answer is likely to be incomplete or unsupported.

The Retrieval Agent introduces an adaptive retrieval process.

Rather than immediately generating an answer, the system first evaluates whether enough evidence has been collected. If necessary, it gathers additional context before handing the selected evidence to the Answer Synthesizer.

The agent therefore behaves similarly to a legal researcher who first searches for relevant material, reviews it, and decides whether additional documents should be consulted before presenting conclusions.

---

# Scope of Responsibility

The Retrieval Agent is responsible for:

* initiating retrieval using the Search tool
* inspecting retrieved previews
* determining whether retrieved previews provide sufficient information
* reading complete chunks when additional context is required
* optionally expanding retrieval to neighboring chunks
* determining when sufficient evidence has been collected
* returning structured evidence for the Answer Synthesizer

The Retrieval Agent is **not** responsible for:

* answering legal questions
* interpreting the law
* producing legal analysis
* generating citations
* validating factual correctness
* grounding or hallucination detection

These responsibilities belong to later stages of the pipeline.

---

# Position Within the Overall Architecture

```
User Question
        │
        ▼
Hybrid Retrieval
        │
        ▼
Retrieval Agent
        │
        ▼
Selected Evidence
        │
        ▼
Answer Synthesizer
        │
        ▼
Grounding
        │
        ▼
Final Response
```

The Retrieval Agent acts as the bridge between document retrieval and answer generation.

---

# Knowledge Sources

The agent operates over two completely independent knowledge bases.

## External Knowledge Base

Official California Tenants Guide.

This serves as the firm's trusted legal reference.

Stored as document chunks.

---

## Internal Knowledge Base

Attorney case summaries and attorney notes.

Each summary represents one complete retrievable unit.

No additional chunking is performed.

---

Both knowledge sources maintain independent retrieval pipelines.

The agent itself remains unaware of this implementation detail.

It simply receives unified search results.

---

# Available Tools

The Retrieval Agent currently has two tools.

## Tool 1 — Search

### Purpose

Discover potentially relevant evidence.

The Search tool performs the complete retrieval pipeline internally.

Internally, it executes:

* Dense embedding retrieval
* PostgreSQL Full Text Search
* Reciprocal Rank Fusion
* Optional Cohere reranking

These implementation details remain completely hidden from the Retrieval Agent.

The agent simply invokes:

```
search(question)
```

---

## Search Result Format

Search does **not** return complete chunks.

Instead it returns retrieval previews.

Each result contains:

* chunk_id
* source
* retrieval_summary
* score

Example:

```json
{
  "chunk_id": "guide_18a9f2",
  "source": "external",
  "retrieval_summary": "Covers permissible security deposit deductions, documentation requirements, and the landlord's obligation to return any remaining deposit within 21 days.",
  "score": 0.94
}
```

---

# Why Retrieval Summaries Instead of Chunk Previews?

Originally, previews were planned as truncated portions of the original chunk.

However, Hybrid Chunking preserves document structure rather than splitting purely by token count.

Consequently, chunks may contain several hundred tokens.

Important information may appear near the middle or end of a chunk.

A truncated preview therefore risks hiding the most relevant content.

Instead, each chunk receives a retrieval summary during the ingestion pipeline.

These summaries are generated once and stored alongside the chunk.

The retrieval summary is specifically designed to help the Retrieval Agent decide whether reading the complete chunk is necessary.

Unlike a conventional summary, it serves two purposes:

* identify the legal topics discussed
* briefly describe the important legal rules, procedures, or concepts contained within the chunk

The retrieval summary is therefore a decision-support artifact rather than a user-facing summary.

This allows the Retrieval Agent to make better decisions while avoiding unnecessary tool calls.

---

# Tool 2 — Read

### Purpose

Retrieve complete chunk contents.

The agent invokes:

```
read(chunk_ids)
```

Example:

```
read([
    "guide_18a9f2",
    "notes_0041"
])
```

The tool returns the complete text for the requested chunks.

---

# Neighbor Expansion

The Read tool optionally supports neighboring chunk retrieval.

Example:

```
read(
    chunk_ids=["guide_18a9f2"],
    include_neighbors=True,
    radius=1
)
```

This returns:

* previous chunk
* requested chunk
* next chunk

Neighbor expansion is disabled by default.

```
include_neighbors = False
```

---

# Why Neighbor Expansion Is Optional

Neighboring chunks frequently contain unrelated information.

Automatically retrieving surrounding chunks would increase context size and token usage without always improving evidence quality.

Instead, the Retrieval Agent explicitly decides whether surrounding context appears necessary.

This preserves efficiency while allowing additional context when required.

---

# Why Neighbor Expansion Is Not a Separate Tool

Neighbor expansion was considered as an independent tool.

However, retrieving neighboring chunks fundamentally represents a variation of reading rather than a distinct capability.

Introducing another tool would unnecessarily increase the agent's action space.

Instead, neighbor expansion is implemented as an optional parameter within the Read tool.

This keeps the tool interface simpler while preserving flexibility.

---

# Agent Workflow

The Retrieval Agent follows an iterative evidence-gathering process.

```
User Question

↓

Search

↓

Inspect retrieval summaries

↓

Enough information?

├── Yes
│
│   Return selected chunk IDs
│
└── No
        │
        ▼
Read complete chunks

↓

Enough information?

├── Yes
│
└── No
        │
        ▼
Read neighboring chunks

↓

Return selected chunk IDs
```

This process resembles how legal professionals first review search results before deciding which documents deserve closer examination.

---

# Why Search Returns Summaries Instead of Full Chunks

The retrieval stage intentionally retrieves more candidate chunks than will ultimately be used.

If every retrieved chunk were immediately returned in full, a substantial amount of context would be wasted.

Returning lightweight retrieval summaries provides several advantages:

* significantly reduces context consumption
* reduces unnecessary tool calls
* allows rapid inspection of many candidates
* mimics human document review behaviour
* improves agent efficiency

Only chunks judged useful are expanded into their complete text.

---

# Expected Search Behaviour

The architecture assumes that retrieval quality is sufficiently strong that the Retrieval Agent will rarely need to perform multiple searches.

This expectation is based on several design decisions:

* dense semantic retrieval
* PostgreSQL Full Text Search
* Reciprocal Rank Fusion
* optional reranking
* optional neighboring chunk expansion

Together these components are expected to provide high retrieval recall.

Consequently, most legal questions should be answerable after a single retrieval operation followed by selective reading.

Although repeated searches remain possible, they are expected to be exceptional rather than routine.

---

# Agent Output

The Retrieval Agent returns structured evidence rather than natural-language responses.

Example:

```json
{
  "sufficient": true,
  "selected_chunks": {
    "external": [
      "guide_18a9f2",
      "guide_6d72ce"
    ],
    "internal": [
      "notes_0041"
    ]
  }
}
```

The backend validates all returned chunk identifiers before retrieving the corresponding chunk contents for the Answer Synthesizer.

This validation ensures that only valid database records are processed and prevents accidental or hallucinated identifiers from propagating through the system.

---

# Separation from the Answer Synthesizer

The Retrieval Agent and Answer Synthesizer communicate exclusively through structured evidence.

The synthesizer receives:

* original user question
* selected chunk contents

It has no knowledge of:

* retrieval scores
* search rankings
* retrieval summaries
* tool calls
* retrieval history

This separation ensures that retrieval and generation remain independent components that can be evaluated and improved separately.

---

# Design Decisions

Several important architectural decisions underpin the Retrieval Agent.

**Single Responsibility**

The Retrieval Agent gathers evidence only.

It never generates answers.

---

**Independent Retrieval Pipelines**

External legal references and internal attorney notes remain independent throughout retrieval.

They are retrieved separately and only unified after retrieval processing.

---

**Retrieval Summaries**

Retrieval summaries are generated once during ingestion.

They are not intended for users.

They exist solely to support agent decision-making.

---

**Selective Reading**

Complete chunks are retrieved only when required.

This reduces unnecessary context usage.

---

**Optional Neighbor Expansion**

Neighboring chunks provide additional context only when explicitly requested.

---

**Structured Communication**

The Retrieval Agent communicates through structured chunk identifiers rather than conversational text.

This creates a clear contract between retrieval and generation.

---

**Backend Validation**

All returned chunk identifiers are validated before retrieval.

The system never assumes that model outputs are inherently correct.

---

# Benefits of the Retrieval Agent

Compared with a traditional fixed RAG pipeline, this architecture provides several advantages.

* Improved retrieval flexibility.
* Reduced unnecessary context consumption.
* Better separation of concerns.
* Easier debugging.
* Independent evaluation of retrieval quality.
* Reduced hallucination risk through evidence-driven generation.
* Clear interfaces between system components.
* Greater maintainability and extensibility.

The Retrieval Agent therefore functions as an intelligent evidence collector rather than a conversational assistant. Its narrow scope, explicit responsibilities, and structured interaction with the remainder of the pipeline contribute to a more robust and production-oriented Retrieval-Augmented Generation architecture suitable for legal research applications.
