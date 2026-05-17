# KanoonVault Design References

This document captures the architecture inspirations and open-source references used across KanoonVault.

## Semantic Retrieval & RAG

- **LlamaIndex** — https://github.com/run-llama/llama_index
  - Inspiration for chunk-based retrieval, hierarchical retrieval logic, and metadata-aware search.
  - KanoonVault uses a simplified LlamaIndex-style chunking layer combined with SQL metadata controls.

- **LangChain** — https://github.com/langchain-ai/langchain
  - Design reference for multi-step retrieval orchestration and tool-calling patterns.
  - KanoonVault is not dependent on LangChain, but the architecture borrows the concept of separate retrieval, reasoning, and tool layers.

- **RAG** — https://github.com/ThomasJay/RAG
  - Minimal RAG pipeline reference for injection correctness.
  - KanoonVault uses FTS + vector retrieval and prompt injection instead of a full LangChain agent.

- **Ragent** — https://github.com/nageoffer/ragent
  - Inspiration for query decomposition and hybrid ranking.
  - KanoonVault uses Ragent-style ranking boosts and fallback hierarchy in `services/vector_memory_service.py`.

## Memory OS / Persistent Memory

- **MemoryOS** — https://github.com/BAI-LAB/MemoryOS
  - Persistent multi-layer memory design reference.
  - Influences case isolation, timeline storage, and structured memory retrieval.

- **EverOS** — https://github.com/EverMind-AI/EverOS
  - Full AI OS architecture reference.
  - Helpful for future expansions around tool + memory + agent integration.

- **AgentOS** — https://github.com/SpharxTeam/AgentOS
  - Multi-agent workflow reference.
  - Useful for future OCR, timeline, and retrieval agent orchestration.

- **Memvid** — https://github.com/memvid/memvid
  - Experimental long-term memory compression reference.
  - Useful if KanoonVault needs archiving or storage footprint reduction.

## OCR Intelligence Pipeline

- **PaddleOCR** — https://github.com/PaddlePaddle/PaddleOCR
  - Primary OCR engine for scanned legal documents.
  - KanoonVault prefers PaddleOCR when available.

- **Paddle2ONNX** — https://github.com/PaddlePaddle/Paddle2ONNX
  - Reference for converting OCR models to optimized runtime.
  - Useful for future production acceleration.

- **PaddleOCR-json** — https://github.com/hiroi-sora/PaddleOCR-json
  - Reference for converting raw OCR output into structured JSON.
  - Useful for timeline extraction and metadata detection.

## How these references are used in KanoonVault

- `services/llm_service.py`
  - Retrieval prompt design follows LlamaIndex/RAG-style chunk injection and grounding.

- `services/vector_memory_service.py`
  - Hybrid search and ranking logic is inspired by RAG and Ragent.
  - SQL-first retrieval and metadata boosting are used for legal context.

- `database.py`
  - Case memory structure, timeline storage, and audit logging reflect MemoryOS/EverOS design principles.

- `services/ocr_service.py`
  - OCR pipeline references PaddleOCR and fallback paths for robust document processing.

## Notes

This document is intentionally lightweight. It describes the architectural influences without requiring the repository to depend on these external tools directly.
