# RegulasiLens parser benchmark

- Evaluation set: `regulations/evaluation/parser-boundaries.v1.json`
- Benchmark version: `1.0.0`
- Parser version: `regulation-structure-v1`
- Corpus manifest version: `2026-08-16.1`
- Reviewed cases: 30 across three official documents
- Result: 30 correct / 30 total = **100%**
- Required threshold: **95%**
- Date executed: 2026-08-16

The sample covers BAB, bagian, pasal, and ayat boundaries, source page identity, OCR
normalization of `Pasal I` to `Pasal 1`, and a negative case ensuring a repeated ayat at a
page boundary is not emitted twice. Cases are exact expected boundary facts reviewed against
the checksum-pinned official PDFs.

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\benchmark_regulation_parser.py
```

The command exits non-zero when the active parser version differs, fewer than 30 cases are
present, an approved source cannot be validated, or accuracy falls below the threshold.
