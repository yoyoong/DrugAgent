import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.search_molecule_tool import search_molecule_by_smiles


def print_json(title: str, data: Any) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(data, ensure_ascii=False, indent=2))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run the real PubChem search tool check.")
    parser.add_argument("--smiles", default="CCO")
    args = parser.parse_args()

    result = await search_molecule_by_smiles(args.smiles)
    summary = {
        "query": result["query"],
        "source": result["source"],
        "cid": result["cid"],
        "properties": result["properties"],
        "sdf_preview": result["sdf"][:500],
        "sdf_length": len(result["sdf"]),
    }
    print_json("search_molecule_by_smiles", summary)
    print("\nSearch molecule tool check passed.")


if __name__ == "__main__":
    asyncio.run(main())
