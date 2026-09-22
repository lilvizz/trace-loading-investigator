# Apex Industrial Components — Operational Data Investigator Dataset

A synthetic-but-relationally-coherent manufacturing dataset built for the
**AI Builder Cup 2026 (Manufacturing track)**. It supports a benchmark for an
**AI-powered Operational Data Investigator** — an agent whose job is to
investigate discrepancies across multiple operational sources, decide
whether each one is a genuine data problem, a legitimate operational
difference, an unresolved case needing human verification, or a low-priority
historical inconsistency, and to explain its conclusion with evidence.

This is a **detect → investigate → explain → identify gaps → prioritize →
verify** benchmark, not a spreadsheet-comparison benchmark. It models two
layers of a real logistics workflow, confirmed by direct practitioner
evidence: (1) whether the *entered operational data itself* can be trusted
(ERP vs. warehouse vs. transaction history), and (2) whether the *physical
bundles* actually on hand — identified by batch and composition grade —
genuinely satisfy what a loading plan requires, before a container is
loaded. A mismatch discovered after bundles have already been dispatched to
logistics is far more costly to fix than one caught beforehand, which is why
priority is driven by dispatch status and loading deadline together, not by
the size of a discrepancy alone.

---

## 1. The fictional company

**Apex Industrial Components**, **Chennai Plant 2** (`plant_id = CHN2`), an
industrial-components manufacturer. The plant receives raw materials and
components from suppliers, stores them across several raw-material and
finished-goods locations, consumes them in production, transfers materials
between storage locations, processes returns and adjustments, and prepares
materials for customer container shipments.

All companies, suppliers, materials, purchase orders, batches, transactions,
events and customers are fictional. All data was generated from a single
internal relational model (materials → suppliers → purchase orders →
goods-receipt transactions → current inventory), so every file describes the
**same** operational history rather than independently-randomized tables.

---

## 2. Data sources (`data/`)

| File | Role | Approx. size |
|---|---|---|
| `erp_inventory.csv` | ERP system export of current inventory by material/batch/location. **Not assumed to be ground truth** — some records contain planted errors. | ~70 rows |
| `warehouse_inventory.xlsx` | Manually maintained warehouse count sheet. Reflects realistic manual-entry behavior: formatting differences, occasional missing values, occasional duplicated rows, stale counts. Not every difference from ERP is an error. | ~76 rows |
| `transactions.csv` | The transaction ledger: `GOODS_RECEIPT`, `PRODUCTION_ISSUE`, `TRANSFER`, `RETURN`, `ADJUSTMENT`, `SCRAP`. This is the primary evidence source for explaining — or failing to explain — apparent discrepancies. | ~155 rows |
| `purchase_orders.csv` | Purchase orders: supplier, material, ordered/received quantities, delivery dates, status. | ~52 rows |
| `historical_inventory_snapshot.csv` | Periodic whole-plant inventory snapshots (roughly three dates across the recent past), each covering a subset of materials, for temporal reasoning. | ~25 rows across 3 dates |
| `loading_schedule.csv` | Planned container/customer shipments: material required, quantity, date, priority. Used to determine which discrepancies actually matter operationally. | ~13 rows |
| `known_events.csv` | Logged operational events: cycle counts, stock adjustments, production issues, returns, quality holds, supplier corrections, warehouse recounts, reconciliation notes. Additional evidence — and, in several cases, deliberate distractors. | ~44 rows |
| `physical_bundles.csv` | The physical goods layer: individual bundles belonging to a batch, with quantity, whether each has been sent to logistics, and its status. This is what logistics actually cross-checks against the entered records before a container loads — a batch can be, and often is, split across several bundles. | ~90 rows |

### Entity relationships

All files connect through shared identifiers: `material_id`, `batch_id`,
`supplier_id`, `purchase_order_id` / `po_number`, `goods_receipt_id` (a
`transaction_id` of type `GOODS_RECEIPT`), `transaction_id`,
`reference_document`, `container_id`, and `bundle_id`. A material can be
traced across ERP → warehouse → transactions → purchase orders → historical
snapshots → loading schedule → known events → physical bundles, and an
investigator is expected to traverse those relationships rather than look at
any one file in isolation.

### The composition-grade / loading-requirement layer

`erp_inventory.csv` carries a `composition_grade` column (`GRADE_A` /
`GRADE_B` / `GRADE_C`) — a simplified suitability grade for the batch, not a
chemistry calculation. Every physical bundle inherits its grade from its
batch; `physical_bundles.csv` does not carry its own grade column, so there
is exactly one source of truth for a batch's composition. `loading_schedule.csv`
carries an optional `required_composition_grade` column: blank where a
container has no composition constraint, or a specific grade where it does.
A container can look fully supplied on quantity alone and still not be
loadable — the grade of the *specific bundles actually on hand* has to be
checked independently.

---

## 3. Investigation cases

The dataset embeds **38 deliberately designed investigation cases** —
CASE-001 through CASE-030 (the original entered-data layer) plus CASE-031
through CASE-038 (the physical-bundle / composition-grade / loading-plan
layer, added on top without altering any of the first 30) — spanning the
categories below (see `evaluation/ground_truth.json` for the full, hidden
answer key — do not ship that file with the application).

**CASE-001..030** (entered-data layer):
- Genuine data errors (duplicate postings, wrong supplier/material mapping,
  incorrect document references, unsupported adjustments)
- Legitimate operational differences (production consumption, returns,
  transfers, timing lag between systems, supplier corrections)
- Unresolved discrepancies with no supporting evidence, requiring human
  verification
- Traceability gaps that are not quantity problems
- A partially-explained, multi-source conflicting case
- An explicitly insufficient-evidence case
- Clean records, including some with cosmetic formatting differences only

**CASE-031..038** (physical-bundle / composition layer): whether the
specific bundles physically marked as sent to logistics genuinely satisfy a
container's material, batch-identity, and composition-grade requirements —
including cases where quantity alone would look sufficient but isn't,
grade-mismatch pairs where one is a genuine error and a structurally similar
one is a documented, legitimate exception, a case solvable only by summing
several partial bundles, and a case where the referenced evidence itself
cannot be reconciled to any real record.

The case set deliberately includes **numerically-identical pairs with
different correct conclusions** (e.g., the same 40-unit ERP/warehouse gap is
fully explained in one case and completely unresolved in another; a grade
mismatch that's a genuine error in one case and a documented, approved
substitution in another), and **deadline-adversarial pairs** where the same
kind of unresolved discrepancy carries very different operational urgency
depending on an upcoming container loading date. Several cases also carry
unrelated-but-plausible "distractor" records — old events, unrelated
adjustments, historical corrections, a bundle sent for the wrong order —
attached to the same material, so an investigator has to identify which
evidence is actually relevant rather than retrieving everything that
mentions a given material, batch, or container.

At least 20% of the golden cases are clean or fully explained by documented
operational activity, so the benchmark does not reward an agent that simply
flags everything, and no case in the bundle layer can be solved by comparing
only two columns — each requires following material → batch → composition
grade → physical bundle → dispatch status → loading requirement, and several
require combining more than one bundle or record to reach the correct
conclusion.

---

## 4. Ground truth (`evaluation/`)

`evaluation/ground_truth.json` holds, per case: `case_id`, `category`,
`expected_conclusion`, `expected_priority`, `supporting_records`,
`required_human_verification`, `explanation`, `key_reasoning`,
`golden_answer`, `acceptable_alternative_answers`, `incorrect_conclusions`,
`critical_evidence`, and `distractor_evidence`. This file is for evaluating
a system's output — it is **not** part of the application-facing dataset and
should not be exposed to the investigator being tested.

---

## 5. Validation (`validation/`)

`validation/validate_dataset.py` is an independent script (it does not reuse
the generator's internal state — it re-derives everything from the exported
files) that checks:

- file sizes against the target ranges above
- referential integrity across all seven files (materials, batches,
  purchase orders, transaction/event/container IDs), tolerant of the
  manual-entry formatting noise that is itself part of the design
- temporal ordering (PO dates, goods-receipt-before-consumption, snapshots
  in the past, loading dates in the future)
- quantity validity (numeric, non-negative where required, received ≤
  ordered)
- that every piece of ground-truth evidence actually resolves to a real
  record in the public data files
- that cases marked "clean" really do have matching figures across sources
- that cases marked "unresolved" really do lack a reconciling transaction
- that no public data file leaks answer-revealing language
- the overall clean/legitimate case ratio
- (additive) every bundle's material/batch is real, bundle quantities never
  exceed their batch's recorded quantity, bundle status and
  `sent_to_logistics`/`sent_date` are mutually consistent and temporally
  valid, every `composition_grade` and `required_composition_grade` value is
  from the allowed set, grade is never duplicated onto bundles as a second
  source of truth, and CASE-001..030 are verified byte-identical/unreordered
  before CASE-031..038 are checked as a clean append

Run it with:

```bash
cd validation
python3 validate_dataset.py
```

It prints a per-section report and, only if every check passes, the line
`DATASET VALIDATION: PASS`.

`validation/build_dataset.py` (a copy of the generator) regenerates the
original 7 files and CASE-001..030 deterministically (fixed random seed).
`validation/patch_dataset.py` then applies the additive bundle/composition/
loading-requirement layer on top (new `physical_bundles.csv`, the two new
columns, and 8 new loading-schedule rows), and `validation/append_ground_truth.py`
appends CASE-031..038. Running all three in order, then the validator,
reproduces the full shipped dataset from scratch.

---

## 6. What this dataset intentionally does **not** tell you

The specific records that were altered, and exactly why, are not documented
here — that is what the investigation agent being benchmarked is supposed to
discover from the relationships between records. The public data files
contain no comments, flags, or language identifying which records are
"correct" or "wrong."
