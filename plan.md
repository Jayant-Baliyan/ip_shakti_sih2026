# IP-SAKTI Sahayak — Corrected Architecture Plan (v2)

Restructured from the original 26-phase plan. Original phase names kept in
parentheses for traceability. Two merges (chunking → ingestion,
retrieval-engine → rag-architecture) collapse the plan to 24 phases.

Root causes fixed:
- Cross-cutting decisions (data model, tech stack, source authority tiers,
  security) were placed *after* the phases that already depended on them.
- Retrieval/RAG content was specified three separate times (phase3, 5, 6).
- The evaluation/experiment harness was built *after* a phase (knowledge-graph)
  that explicitly required it to validate its own value.

---

## Phase 1: Requirements Engineering *(was phase1-requirements)*
No change. Correct as first phase.
- Change needed: none — keep as-is, but add explicit acceptance criteria for
  "Source Authority Levels" and "Privacy Requirements" sections since two new
  early phases (3, 6 below) now consume them directly.

## Phase 2: System-Level Architecture *(was phase2-system-architecture)*
No change. Correct as second phase.
- Change needed: none.

## Phase 3: Data Model *(was phase15-data-model, moved up 12 slots)*
- Problem fixed: originally sat at position 15, after chunking (5),
  knowledge-graph (7), citation-generation (10) had already referenced
  "chunks schema," "graph entities schema," "citations schema" as if they
  existed. Schema must exist before consumers.
- Change needed: finalize Documents / Chunks / Embeddings / Citations /
  Graph-entity / Jurisdiction schemas here, before any retrieval or KG design
  work starts. Treat later phases' schema mentions as consumers only, not
  designers.

## Phase 4: Technology Selection *(was phase23-technology-selection, moved up 19 slots)*
- Problem fixed: original RAG-architecture and retrieval-engine phases
  (3, 6) hard-coded bge-m3, HNSW, bge-reranker-v2-m3, BM25 as if already
  decided, then phase23 pretended to select them from scratch, and phase26
  ADRs "decided" the same choices a third time.
- Change needed: lock embedding model, reranker, vector index, sparse
  method, LLM(s), graph DB, and OCR tool here with rationale. Every
  downstream phase must cite this phase, not restate the decision.

## Phase 5: Source Authority System *(was phase11-source-authority-system, moved up 6 slots)*
- Problem fixed: Tier 1–4 authority weighting is consumed inside RRF fusion
  in the original phase3/phase6, but the phase that defines the tier system
  didn't exist yet at that point (it was phase11).
- Change needed: formalize the Tier 1–4 hierarchy already sketched in the
  Phase 0 corpus investigation into enforceable rules (weight values,
  verification method, anti-fabrication checks) before retrieval fusion logic
  is designed.

## Phase 6: Security Architecture *(was phase19-security-architecture, moved up 13 slots)*
- Problem fixed: security was a single bolt-on phase at the end, disconnected
  from the ingestion, agentic, and API phases it's supposed to protect.
  Privacy/safety *requirements* existed early (phase1) but *enforcement*
  design didn't exist until phase19 — after those components were built.
- Change needed: define auth, secrets management, prompt-injection defense,
  malicious-document defense, retrieval-poisoning defense, tool isolation,
  and PII handling here as constraints that Ingestion (7), Agentic
  Orchestration (16), and API Architecture (18) must design against —
  don't re-derive security as an afterthought in those phases.

## Phase 7: Ingestion Architecture *(was phase4-ingestion-architecture, absorbs phase5-chunking-strategy)*
- Problem fixed: chunking strategy was split into its own phase (5) despite
  already being a checklist item inside ingestion (4), and despite
  overlapping with retrieval's own chunking-adjacent items (citation mapping,
  parent-child expansion).
- Change needed: fold all of phase5's content (fixed/semantic/hierarchical/
  parent-child chunking, citation mapping) into this phase as the final step
  of the ingestion pipeline. One phase, one chunking decision, made against
  the Phase 3 data model and Phase 4 tech choices.

## Phase 8: Retrieval / RAG Architecture *(merges phase3-rag-architecture + phase6-retrieval-engine)*
- Problem fixed: these two original phases specified the same pipeline twice
  — query processing, sparse/dense/hybrid retrieval, cross-encoder reranking,
  MMR evidence selection, confidence/abstention — under two different names.
- Change needed: single phase covering query understanding → retrieval →
  reranking → evidence selection → context building. Reference Phase 4 for
  model choices and Phase 5 for authority weighting instead of re-specifying
  them. If an infra/services view is still needed (scaling, caching, top-K
  tuning), keep it as a subsection here, not a separate phase.

## Phase 9: Evaluation System *(was phase17-evaluation-system, moved up 8 slots)*
- Problem fixed: needed to exist before any phase that proposes running an
  experiment (originally Knowledge Graph, phase7, proposed "experiment design
  to prove GraphRAG value" ten phases before the evaluation harness existed).
- Change needed: retrieval/generation/citation/safety/multilingual metrics
  and benchmark dataset design happen here, immediately after core retrieval
  is architected (Phase 8), so every subsequent phase can be evaluated as
  it's built rather than retrofitted.

## Phase 10: Research Experiment Framework *(was phase18-research-experiment-framework, moved up 8 slots)*
- Problem fixed: same dependency issue as above — this is the harness the
  Knowledge Graph phase needs, and it must exist first.
- Change needed: experiment template, hypothesis tracking, config/dataset
  versioning here, built on top of Phase 9's metrics, before Knowledge Graph.

## Phase 11: Knowledge Graph *(was phase7-knowledge-graph)*
- Problem fixed: previously scheduled before the evaluation/experiment
  framework it explicitly depends on to justify itself.
- Change needed: none to content — just run the "vector-only vs hybrid vs
  graph-first vs agentic" comparison using Phase 9/10's harness, which now
  actually exists.

## Phase 12: Formulation Classification *(was phase8-formulation-classification)*
No structural change — position relative to Jurisdiction/Citation is fine.

## Phase 13: Jurisdiction Engine *(was phase9-jurisdiction-engine)*
No structural change.

## Phase 14: Citation-First Generation *(was phase10-citation-first-generation)*
- Change needed: reference Phase 5 (Source Authority) for authority/
  correctness metrics instead of redefining tiering here.

## Phase 15: Multilingual Architecture *(was phase12-multilingual-architecture)*
No structural change.

## Phase 16: Agentic Orchestration *(was phase13-agentic-orchestration)*
- Change needed: tool isolation and loop/budget limits should be specified
  against the constraints set in Phase 6 (Security), not independently.

## Phase 17: Memory Architecture *(was phase14-memory-architecture)*
No structural change — correctly follows agentic orchestration.

## Phase 18: API Architecture *(was phase16-api-architecture)*
- Change needed: auth/rate-limit sections should implement Phase 6's
  security design, not re-specify it.

## Phase 19: Deployment Architecture *(was phase20-deployment-architecture)*
No structural change.

## Phase 20: Observability *(was phase21-observability)*
No structural change.

## Phase 21: Failure Mode Analysis *(was phase22-failure-mode-analysis)*
- Change needed: this is now explicitly a consolidation phase — per-component
  failure modes were already captured in Phase 2 and Phase 8. Use this phase
  to cross-check completeness, not to re-derive them from scratch.

## Phase 22: Implementation Roadmap *(was phase24-implementation-roadmap)*
No structural change.

## Phase 23: Repository Architecture *(was phase25-repository-architecture)*
No structural change.

## Phase 24: Decision Records (ADR) *(was phase26-decision-records)*
- Problem fixed: originally "decided" things (embedding model, reranker,
  BM25 vs SPLADE, chunking strategy) that were already fixed as far back as
  the original phase3. ADRs recorded decisions retroactively.
- Change needed: since Technology Selection now genuinely happens at Phase 4
  (before those decisions are used anywhere), ADRs here are true rationale
  records written at decision time, not backfilled justifications.

---

## Summary of structural moves
| Original phase | Old position | New position |
|---|---|---|
| data-model | 15 | 3 |
| technology-selection | 23 | 4 |
| source-authority-system | 11 | 5 |
| security-architecture | 19 | 6 |
| chunking-strategy | 5 | merged into 7 (ingestion) |
| retrieval-engine | 6 | merged into 8 (rag-architecture) |
| evaluation-system | 17 | 9 |
| research-experiment-framework | 18 | 10 |
| knowledge-graph | 7 | 11 |

All other phases keep their relative order, shifted to fill the gaps.here i