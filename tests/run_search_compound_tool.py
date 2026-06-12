import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.search_compound_tool import search_compound


def print_json(title: str, data: Any) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(data, ensure_ascii=False, indent=2))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run the real PubChem compound search check.")
    parser.add_argument("--query", default="Aspirin")
    parser.add_argument(
        "--search-type",
        choices=["name", "cid", "smiles", "inchi", "formula"],
        default=None,
    )
    parser.add_argument("--max-records", type=int, default=1)
    args = parser.parse_args()

    result = await search_compound(args.query, args.search_type, args.max_records)
    summary = {
        "query": result["query"],
        "source": result["source"],
        "total_found": result["total_found"],
        "cids": result["cids"],
        "record_count": len(result["records"]),
        "first_record_keys": sorted(result["records"][0].keys()) if result["records"] else [],
        "first_sdf_length": len(result["records"][0]["sdf"]) if result["records"] else 0,
    }
    print_json("search_compound", summary)
    print("\nSearch compound tool check passed.")


if __name__ == "__main__":
    asyncio.run(main())
