import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from tools.search_molecule_tool import search_molecule_by_smiles


MODEL_API_BASE_URL = os.getenv("MODEL_API_BASE_URL", "http://127.0.0.1:8000")

mcp = FastMCP("DrugAgent")


@mcp.tool()
async def search_molecule(smiles: str) -> dict[str, Any]:
    """Search PubChem by SMILES and return molecule metadata plus SDF."""
    return await search_molecule_by_smiles(smiles)


@mcp.tool()
async def predict_molecule_property(smiles: str) -> dict[str, Any]:
    """Call the FastAPI-wrapped molecule property prediction model."""
    if not smiles or not smiles.strip():
        raise ValueError("smiles is required")

    url = f"{MODEL_API_BASE_URL}/models/molecule_property_prediction"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(url, json={"smiles": smiles.strip()})
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    mcp.run()
