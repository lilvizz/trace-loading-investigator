from .data_loader import ManufacturingData


class LoadingInvestigator:
    def __init__(self, data: ManufacturingData):
        self.data = data

    def investigate(self, container_id: str) -> dict:
        loading = self.data.get_loading(container_id)

        material_id = loading["material_id"]
        required_quantity = float(loading["required_quantity"])
        required_grade = loading["required_composition_grade"]

        erp_records = self.data.get_material(material_id)
        bundles = self.data.get_bundles(material_id)
        events = self.data.get_events(material_id)

        sent_bundles = bundles[bundles["sent_to_logistics"] == True]

        evidence = []
        findings = []

        # Track whether the physical-bundle evidence is sufficient
        # to make a deterministic quantity/suitability conclusion.
        unresolved_bundle_traceability = False
        resolvable_sent_bundle_count = 0
        qualifying_quantity = 0.0

        for _, bundle in sent_bundles.iterrows():
            bundle_id = bundle["bundle_id"]
            batch_id = bundle["batch_id"]

            batch_records = erp_records[erp_records["batch_id"] == batch_id]

            if batch_records.empty:
                unresolved_bundle_traceability = True

                findings.append(
                    {
                        "type": "TRACEABILITY_GAP",
                        "bundle_id": bundle_id,
                        "batch_id": batch_id,
                        "message": (
                            f"Bundle {bundle_id} references batch {batch_id}, "
                            "but no ERP batch record was found."
                        ),
                    }
                )

                evidence.append(
                    {
                        "type": "PHYSICAL_BUNDLE",
                        "bundle_id": bundle_id,
                        "material_id": material_id,
                        "batch_id": batch_id,
                        "quantity": float(bundle["quantity"]),
                        "sent_to_logistics": bool(bundle["sent_to_logistics"]),
                        "status": bundle["status"],
                        "composition_grade": None,
                    }
                )

                continue

            resolvable_sent_bundle_count += 1

            batch = batch_records.iloc[0]
            actual_grade = batch["composition_grade"]

            evidence.append(
                {
                    "type": "PHYSICAL_BUNDLE",
                    "bundle_id": bundle_id,
                    "material_id": material_id,
                    "batch_id": batch_id,
                    "quantity": float(bundle["quantity"]),
                    "sent_to_logistics": bool(bundle["sent_to_logistics"]),
                    "status": bundle["status"],
                    "composition_grade": actual_grade,
                }
            )

            if required_grade and actual_grade != required_grade:
                findings.append(
                    {
                        "type": "GRADE_MISMATCH",
                        "bundle_id": bundle_id,
                        "batch_id": batch_id,
                        "required_grade": required_grade,
                        "actual_grade": actual_grade,
                        "quantity": float(bundle["quantity"]),
                        "message": (
                            f"Bundle {bundle_id} is linked to batch {batch_id} "
                            f"with {actual_grade}, but the loading requirement "
                            f"is {required_grade}."
                        ),
                    }
                )
            else:
                qualifying_quantity += float(bundle["quantity"])

        # Operational events are supporting evidence and may explain
        # otherwise apparent mismatches.
        for _, event in events.iterrows():
            evidence.append(
                {
                    "type": "OPERATIONAL_EVENT",
                    "event_id": event["event_id"],
                    "event_date": event["event_date"],
                    "event_type": event["event_type"],
                    "material_id": event["material_id"],
                    "description": event["description"],
                    "reference_id": event["reference_id"],
                    "status": event["status"],
                }
            )

        # IMPORTANT:
        # No sent-bundle records does NOT prove that qualifying quantity is
        # zero. It means the physical-bundle evidence needed to establish
        # loading suitability is missing.
        if required_grade:
            if resolvable_sent_bundle_count == 0:
                findings.append(
                    {
                        "type": "INSUFFICIENT_EVIDENCE",
                        "required_quantity": required_quantity,
                        "required_grade": required_grade,
                        "message": (
                            "No resolvable physical bundles sent to logistics "
                            "were found, so the available evidence is "
                            "insufficient to determine whether the required "
                            "quantity and composition grade are satisfied."
                        ),
                    }
                )

            elif not unresolved_bundle_traceability and qualifying_quantity < required_quantity:
                findings.append(
                    {
                        "type": "REQUIREMENT_UNSATISFIED",
                        "required_quantity": required_quantity,
                        "required_grade": required_grade,
                        "qualifying_quantity": qualifying_quantity,
                        "message": (
                            f"Loading requires {required_quantity:g} EA of "
                            f"{required_grade}, but only "
                            f"{qualifying_quantity:g} EA of qualifying sent "
                            "bundles were found."
                        ),
                    }
                )

        return {
            "container": {
                "container_id": container_id,
                "loading_date": loading["loading_date"],
                "destination": loading["destination"],
                "priority": loading["priority"],
                "loading_status": loading["loading_status"],
            },
            "requirement": {
                "material_id": material_id,
                "required_quantity": required_quantity,
                "required_composition_grade": required_grade,
            },
            "evidence": evidence,
            "findings": findings,
        }