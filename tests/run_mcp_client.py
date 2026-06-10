import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def print_result(title: str, result: Any) -> None:
    print(f"\n=== {title} ===")
    for item in result.content:
        text = getattr(item, "text", None)
        if text is None:
            print(item)
            continue

        try:
            print(json.dumps(json.loads(text), ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            print(text)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run the real DrugAgent MCP server check.")
    parser.add_argument("--smiles", default="CCO", help="SMILES string to check.")
    parser.add_argument(
        "--skip-pubchem",
        action="store_true",
        help="Skip search_molecule because it requires PubChem network access.",
    )
    args = parser.parse_args()

    server = StdioServerParameters(
        command="python",
        args=[str(PROJECT_ROOT / "mcp_server.py")],
        env={
            **os.environ,
            "PYTHONNOUSERSITE": "1",
            "MODEL_API_BASE_URL": os.getenv(
                "MODEL_API_BASE_URL",
                "http://127.0.0.1:8000",
            ),
        },
        cwd=str(PROJECT_ROOT),
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Available MCP tools:")
            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")

            prediction = await session.call_tool(
                "predict_molecule_property",
                {"smiles": args.smiles},
            )
            print_result("predict_molecule_property", prediction)

            if not args.skip_pubchem:
                molecule = await session.call_tool(
                    "search_molecule",
                    {"smiles": args.smiles},
                )
                print_result("search_molecule", molecule)

    print("\nMCP client check passed.")


if __name__ == "__main__":
    asyncio.run(main())
