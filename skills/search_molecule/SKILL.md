# Search Molecule

Use this skill when the user wants to search molecule information from a SMILES string, especially when they ask for PubChem information, CID, molecular formula, molecular weight, IUPAC name, canonical SMILES, or SDF structure data.

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
search_molecule
```

## Input

Pass one argument:

```json
{
  "smiles": "CCO"
}
```

- `smiles`: required string. The molecule SMILES to search.

## Output

The tool returns structured molecule information from PubChem:

- `query.smiles`: original SMILES
- `source`: data source, normally `PubChem`
- `cid`: PubChem compound ID
- `properties`: molecule properties, such as molecular formula, molecular weight, IUPAC name, and SMILES fields
- `sdf`: SDF structure text

## Behavior

1. Validate that the user provided a SMILES string.
2. Call the local MCP tool `search_molecule` with the SMILES string.
3. Return the useful fields to the user in a concise structured summary.
4. If the user needs the full SDF, provide it only when requested because it can be long.

## Example

User request:

```text
Search PubChem information for CCO.
```

MCP call:

```json
{
  "tool": "search_molecule",
  "arguments": {
    "smiles": "CCO"
  }
}
```

Expected response summary:

```text
CID: 702
Formula: C2H6O
IUPAC name: ethanol
SMILES: CCO
```

## Error Handling

- If the local MCP server is unavailable, tell the user to start or configure the DrugAgent MCP server.
- If PubChem cannot find a compound for the SMILES, report that no PubChem CID was found.
- If network access fails, explain that the PubChem request failed and suggest retrying when the network is available.
