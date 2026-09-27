import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trace_loading.data_loader import ManufacturingData
from trace_loading.agent import InvestigationAgent


DATA_DIR = ROOT / "data"


data = ManufacturingData(DATA_DIR)
agent = InvestigationAgent(data, use_gemini=False)


print("\n" + "=" * 110)
print("TRACE DEEP CASE AUDIT")
print("=" * 110)


for container_id in data.loading["container_id"].dropna().tolist():

    result = agent.investigate(container_id)

    assessment = result["assessment"]
    plan = result["investigation_plan"]
    findings = result.get("findings", [])
    gaps = result.get("evidence_gaps", [])
    evidence = result.get("evidence", [])

    print("\n" + "=" * 110)
    print(f"CASE: {container_id}")
    print("=" * 110)

    print(f"CONCLUSION:          {assessment.get('conclusion')}")
    print(f"PRIORITY:            {assessment.get('priority')}")
    print(f"CONFIDENCE:          {assessment.get('confidence')}")
    print(
        f"HUMAN VERIFY:        "
        f"{assessment.get('requires_human_verification')}"
    )

    print("\n--- INVESTIGATION STATE ---")

    print(
        f"PLAN COMPLETE:       "
        f"{plan.get('investigation_complete')}"
    )

    unresolved = plan.get("unresolved_questions", [])

    print(
        f"UNRESOLVED COUNT:    "
        f"{len(unresolved)}"
    )

    if unresolved:
        print("\nUNRESOLVED QUESTIONS:")

        for item in unresolved:
            print(f"  - {item}")

    print("\n--- FINDINGS ---")

    if findings:
        for finding in findings:
            print(f"  TYPE: {finding.get('type')}")

            if finding.get("message"):
                print(f"  MESSAGE: {finding.get('message')}")

            print()
    else:
        print("  None")

    print("--- EVIDENCE GAPS ---")

    if gaps:
        for gap in gaps:
            print(f"  - {gap}")
    else:
        print("  None")

    print("\n--- OPERATIONAL EVENTS ---")

    events = [
        item
        for item in evidence
        if isinstance(item, dict)
        and item.get("type") == "OPERATIONAL_EVENT"
    ]

    if events:
        for event in events:
            print(
                f"  {event.get('event_id')} | "
                f"{event.get('event_type')} | "
                f"status={event.get('status')} | "
                f"{event.get('description')}"
            )
    else:
        print("  None")

    print("\n--- PHYSICAL BUNDLES ---")

    bundles = [
        item
        for item in evidence
        if isinstance(item, dict)
        and item.get("type") == "PHYSICAL_BUNDLE"
    ]

    if bundles:
        for bundle in bundles:
            print(
                f"  {bundle.get('bundle_id')} | "
                f"batch={bundle.get('batch_id')} | "
                f"qty={bundle.get('quantity')} | "
                f"grade={bundle.get('composition_grade')} | "
                f"sent={bundle.get('sent_to_logistics')} | "
                f"status={bundle.get('status')}"
            )
    else:
        print("  None")

    print("\n--- RECOMMENDED ACTION ---")
    print(
        f"  {result.get('recommended_action')}"
    )

print("\n" + "=" * 110)
print("END TRACE DEEP CASE AUDIT")
print("=" * 110)