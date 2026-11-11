# Requirements and delivery status

The approved project adapts the supplied retail-fraud master prompt to banking document verification. The core question is whether multimodal extraction combined with evidence-grounded checks improves verification over OCR-only extraction.

## Delivered initial baseline

Authentication; private case/document storage; 32 catalog routes; local PDF extraction; optional Tesseract OCR; optional local multimodal adapter; evidence fields; deterministic checks; cross-document name comparison; exact duplicate detection; human decisions; synthetic scenarios; baseline evaluation; JSON/CSV exports; local status jobs; audit history; configuration and deployment files.

## Explicitly pending

Multimodal adapter live inference validation; robust arbitrary-layout extraction; field editing; visual forgery detection; layout grounding; granular team permissions; durable background queue; job cancellation; normalized domain schema/migrations; PDF reporting; robust benchmark splits and experiments; browser automation suite; PostgreSQL/Docker verification; production hardening.

No completed research results, issuer authentication, calibrated fraud probability, real banking network integration, or production readiness is claimed.

The present local implementation is intentionally runnable without paid APIs, GPUs, or externally supplied personal documents. Use only fictional documents in the demonstration.
