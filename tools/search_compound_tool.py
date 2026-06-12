import asyncio
import os
from typing import Any, Literal
from urllib.parse import quote

import httpx


PUBCHEM_BASE_URL = os.getenv(
    "PUBCHEM_BASE_URL",
    "https://pubchem.ncbi.nlm.nih.gov/rest/pug",
)

SearchType = Literal["name", "cid", "smiles", "inchi", "formula"]
SEARCH_TYPES = {"name", "cid", "smiles", "inchi", "formula"}


async def search_compound(
    query: str,
    search_type: SearchType | None = None,
    max_records: int = 10,
) -> dict[str, Any]:
    if not query or not query.strip():
        raise ValueError("query is required")
    if search_type is not None and search_type not in SEARCH_TYPES:
        raise ValueError(
            "search_type must be one of: name, cid, smiles, inchi, formula"
        )
    if max_records < 1 or max_records > 100:
        raise ValueError("max_records must be between 1 and 100")

    normalized_query = query.strip()
    normalized_search_type = search_type or _infer_search_type(normalized_query)

    async with httpx.AsyncClient(timeout=30.0) as client:
        cids = await _get_cids(client, normalized_query, normalized_search_type)
        selected_cids = cids[:max_records]
        records = await _get_compound_records_with_sdf(client, selected_cids)

    return {
        "query": {
            "value": query,
            "search_type": normalized_search_type,
            "max_records": max_records,
        },
        "source": "PubChem",
        "total_found": len(cids),
        "cids": selected_cids,
        "records": records,
    }


def _infer_search_type(query: str) -> SearchType:
    if query.isdigit():
        return "cid"
    if query.startswith("InChI="):
        return "inchi"
    return "name"


async def _get_cids(
    client: httpx.AsyncClient,
    query: str,
    search_type: SearchType,
) -> list[int]:
    if search_type == "cid":
        cid = int(query)
        return [cid]

    if search_type in {"smiles", "inchi"}:
        response = await client.post(
            f"{PUBCHEM_BASE_URL}/compound/{search_type}/cids/JSON",
            data={search_type: query},
        )
    else:
        namespace = "fastformula" if search_type == "formula" else search_type
        response = await client.get(
            f"{PUBCHEM_BASE_URL}/compound/{namespace}/{quote(query, safe='')}/cids/JSON"
        )

    response.raise_for_status()
    data = response.json()
    cids = data.get("IdentifierList", {}).get("CID", [])
    if not cids:
        raise ValueError(f"No PubChem CID found for {search_type}: {query}")
    return [int(cid) for cid in cids]


async def _get_compound_records(
    client: httpx.AsyncClient,
    cids: list[int],
) -> list[dict[str, Any]]:
    if not cids:
        return []

    response = await client.get(
        f"{PUBCHEM_BASE_URL}/compound/cid/{','.join(str(cid) for cid in cids)}/JSON"
    )
    response.raise_for_status()
    data = response.json()
    return data.get("PC_Compounds", [])


async def _get_compound_records_with_sdf(
    client: httpx.AsyncClient,
    cids: list[int],
) -> list[dict[str, Any]]:
    records = await _get_compound_records(client, cids)
    sdfs = await asyncio.gather(*[_get_sdf(client, str(cid)) for cid in cids])

    records_by_cid = {
        int(record.get("id", {}).get("id", {}).get("cid")): record
        for record in records
        if record.get("id", {}).get("id", {}).get("cid") is not None
    }

    return [
        {
            **records_by_cid.get(cid, {"id": {"id": {"cid": cid}}}),
            "sdf": sdf,
        }
        for cid, sdf in zip(cids, sdfs)
    ]


async def _get_sdf(client: httpx.AsyncClient, cid: str) -> str:
    response = await client.get(
        f"{PUBCHEM_BASE_URL}/compound/cid/{quote(cid, safe='')}/SDF"
    )
    response.raise_for_status()
    return response.text
