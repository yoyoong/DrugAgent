import os
from typing import Any

import httpx


PUBCHEM_BASE_URL = os.getenv(
    "PUBCHEM_BASE_URL",
    "https://pubchem.ncbi.nlm.nih.gov/rest/pug",
)


async def search_molecule_by_smiles(smiles: str) -> dict[str, Any]:
    if not smiles or not smiles.strip():
        raise ValueError("smiles is required")

    async with httpx.AsyncClient(timeout=20.0) as client:
        cid = await _get_cid(client, smiles.strip())
        properties = await _get_properties(client, cid)
        sdf = await _get_sdf(client, cid)

    return {
        "query": {"smiles": smiles},
        "source": "PubChem",
        "cid": cid,
        "properties": properties,
        "sdf": sdf,
    }


async def _get_cid(client: httpx.AsyncClient, smiles: str) -> int:
    url = f"{PUBCHEM_BASE_URL}/compound/smiles/cids/JSON"
    response = await client.post(url, data={"smiles": smiles})
    response.raise_for_status()
    data = response.json()
    cids = data.get("IdentifierList", {}).get("CID", [])
    if not cids:
        raise ValueError(f"No PubChem CID found for SMILES: {smiles}")
    return int(cids[0])


async def _get_properties(client: httpx.AsyncClient, cid: int) -> dict[str, Any]:
    fields = ",".join(
        [
            "MolecularFormula",
            "MolecularWeight",
            "CanonicalSMILES",
            "IsomericSMILES",
            "IUPACName",
        ]
    )
    url = f"{PUBCHEM_BASE_URL}/compound/cid/{cid}/property/{fields}/JSON"
    response = await client.get(url)
    response.raise_for_status()
    data = response.json()
    properties = data.get("PropertyTable", {}).get("Properties", [])
    if not properties:
        return {}
    return properties[0]


async def _get_sdf(client: httpx.AsyncClient, cid: int) -> str:
    url = f"{PUBCHEM_BASE_URL}/compound/cid/{cid}/SDF"
    response = await client.get(url)
    response.raise_for_status()
    return response.text
