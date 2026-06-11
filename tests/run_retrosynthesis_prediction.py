import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.strip()


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
    parser = argparse.ArgumentParser(
        description="Run the real DrugAgent retrosynthesis MCP tool check."
    )
    parser.add_argument("--smiles", default="Cc1cc(C)n2nc(C=O)nc2n1", help="Target molecule SMILES string.")
    args = parser.parse_args()

    server = StdioServerParameters(
        command="python",
        args=[str(PROJECT_ROOT / "mcp_server.py")],
        env={
            **os.environ,
            "PYTHONNOUSERSITE": "1",
            "MODEL_API_HOST": required_env("MODEL_API_HOST"),
            "MODEL_API_PORT": required_env("MODEL_API_PORT"),
            "MODEL_API_HOST_DCTBM": required_env("MODEL_API_PORT_DCTBM"),
            "MCP_HOST": required_env("MCP_HOST"),
            "MCP_PORT": required_env("MCP_PORT"),
            "MCP_PATH": required_env("MCP_PATH"),
            "MCP_TRANSPORT": "stdio",
        },
        cwd=str(PROJECT_ROOT),
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            prediction = await session.call_tool(
                "predict_retrosynthesis",
                {"smiles": args.smiles},
            )
            print_result("predict_retrosynthesis", prediction)

    print("\nRetrosynthesis MCP check passed.")


if __name__ == "__main__":
    asyncio.run(main())
