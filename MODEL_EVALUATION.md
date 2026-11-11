# Evaluation methodology

Current baseline is deterministic field extraction and verification; it is not a trained fraud classifier. Optional multimodal and hybrid modes are implemented for local Ollama but need live validation on an installed vision-capable model.

Synthetic manifests contain document ID, scenario, expected indicator, seed, and document type. Expected labels never enter the rule engine. Scenarios: clean, missing name, incorrect salary/statement arithmetic, expired identity. Mixed generation cycles clean/arithmetic/missing-name. Unsupported arithmetic scenarios on nonfinancial documents become missing-name scenarios and the actual scenario is stored.

Evaluation compares `bool(findings)` with the stored `expected_finding`, producing TP/FP/TN/FN, precision, recall, and F1. Undefined precision/recall are reported as zero. The result records the dataset and configuration. Evaluation currently uses each document's latest result, so do not overwrite results between experiments and assume a paired comparison. Immutable analysis-run selection is future work.

Template arithmetic can yield perfect scores because rules and synthetic formatting are closely aligned. Such scores establish implementation behavior only. They do not imply generalization or real-world fraud detection accuracy.

Final study still requires applicant/template-grouped held-out splits, diverse document layouts, human annotations, extraction field F1, classification macro F1, localization metrics, latency/cost, OCR degradation, unseen scenarios, calibrated uncertainty/coverage, consistent model-run selection, and confidence intervals. No results for these unfinished studies are claimed.
