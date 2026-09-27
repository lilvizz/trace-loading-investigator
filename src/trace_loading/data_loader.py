from pathlib import Path
import re

import pandas as pd


_CONTAINER_ID_PATTERN = re.compile(r"CNT-\d+")


class ManufacturingData:
    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)

        self.erp = pd.read_csv(
            self.data_dir / "erp_inventory.csv"
        )

        self.bundles = pd.read_csv(
            self.data_dir / "physical_bundles.csv"
        )

        self.loading = pd.read_csv(
            self.data_dir / "loading_schedule.csv"
        )

        self.events = pd.read_csv(
            self.data_dir / "known_events.csv"
        )

    def get_loading(self, container_id: str) -> pd.Series:
        matches = self.loading[
            self.loading["container_id"] == container_id
        ]

        if matches.empty:
            raise ValueError(
                f"Container not found: {container_id}"
            )

        loading = matches.iloc[0].copy()

        # Blank optional fields are represented by pandas as NaN.
        # Convert them to None so the investigation engine does not
        # mistake "no requirement" for a real value such as "nan".
        if "required_composition_grade" in loading.index:
            if pd.isna(loading["required_composition_grade"]):
                loading["required_composition_grade"] = None
            else:
                loading["required_composition_grade"] = str(
                    loading["required_composition_grade"]
                ).strip()

        return loading

    def get_material(self, material_id: str) -> pd.DataFrame:
        return self.erp[
            self.erp["material_id"] == material_id
        ]

    def get_bundles(self, material_id: str) -> pd.DataFrame:
        return self.bundles[
            self.bundles["material_id"] == material_id
        ]

    def get_events(
        self,
        material_id: str,
        container_id: str | None = None,
    ) -> pd.DataFrame:
        """
        Return operational events relevant to a loading investigation.

        Events that do not mention a specific container are treated as
        material-level operational evidence.

        Events that explicitly mention a container are scoped to that
        container so that a waiver or exception belonging to one loading
        operation cannot leak into another investigation.
        """

        events = self.events[
            self.events["material_id"] == material_id
        ]

        if container_id is None:
            return events

        return events[
            events.apply(
                lambda row: self._event_applies_to_container(
                    row,
                    container_id,
                ),
                axis=1,
            )
        ]

    @staticmethod
    def _event_applies_to_container(
        event: pd.Series,
        container_id: str,
    ) -> bool:
        text = (
            f"{event.get('reference_id', '')} "
            f"{event.get('description', '')}"
        )

        referenced_containers = set(
            _CONTAINER_ID_PATTERN.findall(str(text))
        )

        # No container is explicitly named, so treat the event as
        # material-level evidence.
        if not referenced_containers:
            return True

        # A container-specific event applies only to the container
        # explicitly named in the event.
        return container_id in referenced_containers