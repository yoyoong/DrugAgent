import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from tools.search_compound_tool import search_compound as search_compound_from_pubchem


PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


def required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.strip()


MCP_HOST = required_env("MCP_HOST")
MCP_PORT = int(required_env("MCP_PORT"))
MCP_PATH = required_env("MCP_PATH")
MCP_TRANSPORT = required_env("MCP_TRANSPORT")

MODEL_API_HOST = required_env("MODEL_API_HOST")
MODEL_API_PORT_DCTBM = int(required_env("MODEL_API_PORT_DCTBM")) # DCTBM

mcp = FastMCP(
    "DrugAgent",
    host=MCP_HOST,
    port=MCP_PORT,
    streamable_http_path=MCP_PATH,
)


@mcp.tool()
async def search_compound(
    query: str,
    search_type: str | None = None,
    max_records: int = 10,
) -> dict[str, Any]:
    """Search PubChem compounds by name, CID, SMILES, InChI, or formula."""
    return await search_compound_from_pubchem(query, search_type, max_records)


@mcp.tool()
async def predict_retrosynthesis(smiles: str) -> dict[str, Any]:
    """Call the FastAPI-wrapped DCTBM model."""

    if not smiles or not smiles.strip():
        raise ValueError("smiles is required")

    url = f"http://{MODEL_API_HOST}:{MODEL_API_PORT_DCTBM}/models/retrosynthesis_prediction"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(url, json={"smiles": smiles.strip()})
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    mcp.run(transport=MCP_TRANSPORT)
