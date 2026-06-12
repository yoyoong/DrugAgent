import argparse
import json

import httpx


def print_json(title: str, data: object) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test the MMCLKin FastAPI service.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8020")
    parser.add_argument("--kinase-id", default="ABL1")
    parser.add_argument("--ligand-id", default="11314340")
    parser.add_argument("--panel", nargs="+", default=["ABL1", "EGFR", "KIT"])
    args = parser.parse_args()

    with httpx.Client(base_url=args.base_url, timeout=600.0, trust_env=False) as client:
        health = client.get("/health")
        health.raise_for_status()
        print_json("health", health.json())

        affinity = client.post(
            "/api/mmclkin/affinity",
            json={
                "kinase_id": args.kinase_id,
                "ligand_id": args.ligand_id,
                "dataset": "3DKDavis",
                "structure_source": "mmclkin_database",
            },
        )
        print_json("affinity", affinity.json())
        affinity.raise_for_status()

        selectivity = client.post(
            "/api/mmclkin/selectivity",
            json={
                "ligand_id": args.ligand_id,
                "kinase_panel": args.panel,
                "dataset": "3DKDavis",
                "structure_source": "mmclkin_database",
            },
        )
        print_json("selectivity", selectivity.json())
        selectivity.raise_for_status()


if __name__ == "__main__":
    main()
