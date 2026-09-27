from pathlib import Path

import pandas as pd


class ManufacturingData:
    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)

        self.erp = pd.read_csv(self.data_dir / "erp_inventory.csv")
        self.bundles = pd.read_csv(self.data_dir / "physical_bundles.csv")
        self.loading = pd.read_csv(self.data_dir / "loading_schedule.csv")
        self.events = pd.read_csv(self.data_dir / "known_events.csv")

    def get_loading(self, container_id: str) -> pd.Series:
        matches = self.loading[
            self.loading["container_id"] == container_id
        ]

        if matches.empty:
            raise ValueError(f"Container not found: {container_id}")

        return matches.iloc[0]

    def get_material(self, material_id: str) -> pd.DataFrame:
        return self.erp[
            self.erp["material_id"] == material_id
        ]

    def get_bundles(self, material_id: str) -> pd.DataFrame:
        return self.bundles[
            self.bundles["material_id"] == material_id
        ]

    def get_events(self, material_id: str) -> pd.DataFrame:
        return self.events[
            self.events["material_id"] == material_id
        ]