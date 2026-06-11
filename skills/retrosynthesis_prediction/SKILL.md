# Retrosynthesis Prediction

Use this skill when the user wants to predict retrosynthesis routes or possible reactants from a target molecule SMILES string.

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

The MCP server reads FastAPI connection settings from `.env`. The retrosynthesis service uses `MODEL_API_HOST` plus `MODEL_API_HOST_DCTBM` as the remote FastAPI host and port in the current server implementation.

## MCP Tool

Call this MCP tool:

```text
predict_retrosynthesis
```

## Input

Pass one argument:

```json
{
  "smiles": "CCO"
}
```

- `smiles`: required string. The target molecule SMILES to analyze for retrosynthesis.

## Output

The tool returns the JSON response from the remote FastAPI retrosynthesis endpoint:

```text
/models/retrosynthesis_prediction
```

Typical useful fields may include:

- target molecule SMILES
- predicted reactants or precursor molecules
- route scores or probabilities
- model metadata
- status or error message

## Behavior

1. Validate that the user provided a SMILES string.
2. Call the local MCP tool `predict_retrosynthesis` with the SMILES string.
3. Summarize the predicted retrosynthesis result in a concise structured format.
4. Preserve important confidence scores, ranks, or route identifiers if the model response includes them.

## Example

User request:

```text
Predict retrosynthesis routes for CCO.
```

MCP call:

```json
{
  "tool": "predict_retrosynthesis",
  "arguments": {
    "smiles": "CCO"
  }
}
```

## Error Handling

- If the local MCP server is unavailable, tell the user to start or configure the DrugAgent MCP server.
- If required `.env` values are missing, report the missing variable name from the error message.
- If the remote FastAPI retrosynthesis service is unavailable, explain that the retrosynthesis request failed and suggest checking the configured host and port.
- If the model cannot produce a route for the SMILES, report that no retrosynthesis prediction was returned.
