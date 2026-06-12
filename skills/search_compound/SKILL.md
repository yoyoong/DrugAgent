# Search Compound

Use this skill when the user wants to search compound information from PubChem by compound name, PubChem CID, SMILES, InChI, or molecular formula.

## Requirement

Use the local DrugAgent MCP server. The MCP server should be configured by the Codex client to run:

```text
python C:\Project\DrugAgent\mcp_server.py
```

Recommended working directory:

```text
C:\Project\DrugAgent
```

Recommended environment variable:

```text
PYTHONNOUSERSITE=1
```

## MCP Tool

Call this MCP tool:

```text
search_compound
```

## Input

Pass these arguments:

```json
{
  "query": "Aspirin",
  "search_type": "name",
  "max_records": 10
}
```

- `query`: required string. Compound name, PubChem CID, SMILES, InChI, or molecular formula.
- `search_type`: optional string. One of `name`, `cid`, `smiles`, `inchi`, or `formula`. If omitted, numeric queries are treated as `cid`, `InChI=` queries as `inchi`, and other queries as `name`.
- `max_records`: optional integer from 1 to 100. Limits how many matching PubChem compound records are returned.

## Output

The tool returns structured compound information from PubChem:

- `query`: original query, resolved search type, and record limit
- `source`: data source, normally `PubChem`
- `total_found`: number of matching PubChem CIDs
- `cids`: returned PubChem compound IDs
- `records`: returned compound records with PubChem compound data and an `sdf` structure string for each CID

## Behavior

1. Validate that the user provided a query string.
2. Pick the correct `search_type` from the user request. Use explicit types when possible, especially for SMILES and formula queries.
3. Call the local MCP tool `search_compound`.
4. Summarize the useful fields for the user, including SDF only when needed because it can be long.

## Examples

Compound name:

```json
{
  "tool": "search_compound",
  "arguments": {
    "query": "Aspirin",
    "search_type": "name",
    "max_records": 1
  }
}
```

PubChem CID:

```json
{
  "tool": "search_compound",
  "arguments": {
    "query": "2244",
    "search_type": "cid"
  }
}
```

SMILES:

```json
{
  "tool": "search_compound",
  "arguments": {
    "query": "CCO",
    "search_type": "smiles",
    "max_records": 1
  }
}
```

## Error Handling

- If the local MCP server is unavailable, tell the user to start or configure the DrugAgent MCP server.
- If PubChem cannot find a compound for the query, report that no PubChem CID was found.
- If network access fails, explain that the PubChem request failed and suggest retrying when the network is available.
