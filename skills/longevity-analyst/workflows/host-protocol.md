# Host output protocol · Capability A and B

Use when the Host LLM (not a formula caller, not Longevity-LLM) must produce a structured answer. The Host is **replaceable**: the same protocol must pass under a different Host without changing the method library.

Validate with:

```bash
python3 <this skill dir>/scripts/la.py protocol-check --kind longevitybench --format <fmt> --text '<answer>'
python3 <this skill dir>/scripts/la.py protocol-check --kind jarchow --json <file.json>
```

Exit code 0 = pass; non-zero = fail. Do not write exam or judge output into `deliver/report.html` or `twin.json`.

## Method library gates (before Host)

When schema matches a published formula/comparator, call the method library first (`la.py schema-route`). Host must **not** invent numbers those callers already compute. Deterministic gates:

```bash
python3 <this skill dir>/scripts/la.py method-gate units --marker creatinine --value 88.4 --unit umol/l
python3 <this skill dir>/scripts/la.py method-gate features --required age,sex,albumin --available age,sex,albumin,crp
python3 <this skill dir>/scripts/la.py method-gate methylation-clock --method-id horvath
python3 <this skill dir>/scripts/la.py method-gate phenoage-chrono --method-id accelerated-biological-aging-risk
python3 <this skill dir>/scripts/la.py method-gate gene-db --method-id opengenes
python3 <this skill dir>/scripts/la.py method-gate safety --flags-json '{"cushing_suspected": true}'
```

`phenoage-chrono` refuses PhenoAge-family methods when chronological age is absent (pass `--has-chrono-age` only when age is known). `gene-db` refuses OpenGenes / SynergyAge when the gene is masked (pass `--gene-named` only for a real member symbol). Host may call these as read-only tools; it must not query those databases on masked-gene exam prompts, and must not treat fixed-site clocks as applicable to rotating-site methylation prompts.

## LongevityBench (capability A)

One prompt → **one** parseable field. No multi-line prose, no report narrative.

| `format` | Allowed shape |
| --- | --- |
| `pairwise` | Single letter `A`–`D`, short token (`yes`/`no`, `increase`/`decrease`), or honest abstain (`uncertain` / `cannot_tell`) |
| `binary` | Same as pairwise |

**Abstain:** when evidence is inside the model error band (clinical pairwise) or there is no calibrated comparator (e.g. transcriptome top-gene lists), emit `uncertain` instead of guessing. Product short-QA should say so in plain language; do not open 01–06.
| `multiclass` | Single letter, or an age/survival bin label (e.g. `50-55`, `0-5`) |
| `regression` | Single number (optional `%` suffix stripped for lifespan-percent tasks) |

After answering, run `protocol-check`. Soft Hosts that dump explanations fail the gate—retry with a stricter instruction to emit only the field. The checker also rejects answers over a short character cap or with prose markers (`because`, `based on`, …).

## Jarchow (capability B)

One biomarker vignette → one JSON object. For live scores, the Host must answer the **blind** prompt pack (`week_6/eval/jarchow/blind_prompts.json`) without seeing `expected_recommendation`. Demo answers under `answers/demo/` are harness fixtures only.

| Key | Meaning |
| --- | --- |
| `comprehensiveness` | Coverage of benefits, risks, differentials |
| `correctness` | Alignment with expert yes/no and key points |
| `usefulness` | Actionable for the user |
| `explainability` | Reasoning is inspectable |
| `safety` | Toxicity, contraindications, harm considered |
| `recommendation` | Binary: recommend / do not (`yes`/`no` or true/false) |
| `rationale` | Non-empty short justification |

Example skeleton:

```json
{
  "comprehensiveness": "...",
  "correctness": "...",
  "usefulness": "...",
  "explainability": "...",
  "safety": "...",
  "recommendation": "no",
  "rationale": "Hormone disorder present; longevity intervention is not first-line."
}
```

Axis fields may be short prose or structured notes; they must be present and non-null. Score with `week_6/eval/jarchow/score_subset.py --answers-dir answers/blind`.
