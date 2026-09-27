# WN Translator

Personal AI-assisted translator for English WN/LN documents into Indonesian.

## Current workflow

EPUB/DOCX
→ Parser
→ Document IR
→ Chapter Splitter
→ Entity Detection
→ Entity Resolution / Research
→ Chapter Context
→ Hybrid Chunker
→ Gemini/Gemma Translation
→ Rule-Based QA
→ Automatic Retry
→ Progress Save
→ Document Reconstruction
→ EPUB/DOCX

## Current architecture

- `models/` — internal document representation
- `parsers/` — EPUB/DOCX parsing
- `research/` — entity detection, resolution, glossary, research
- `translation/` — context, chunking, translation, chapter/project pipeline
- `qa/` — deterministic quality checks and retry control
- `storage/` — glossary, rules, and progress persistence
- `reconstruction/` — EPUB/DOCX output reconstruction
- `tests/` — integration and fidelity tests
- `progress/` — runtime progress state (ignored by Git)
- `output/` — generated translations (ignored by Git)

## Supported input

- EPUB
- DOCX

## Supported output

- EPUB
- DOCX

## Models

The project is designed around:

- Gemini
- Gemma

## Security

API keys must be provided through the `GEMINI_API_KEY` environment variable.

Do not commit API keys, `.env` files, generated translations, or runtime progress data.

## Development

The project is currently under active development.
