# DrugAgent

A minimal demo for building a drug-development agent with:

- Skills for Codex / Claude Code instructions
- FastAPI for wrapping model capabilities
- MCP tools for agent-callable functions
- A simple PubChem molecule search tool

## Project Layout

```text
DrugAgent/
+-- skills/
+-- models/
+-- api/
+-- tools/
+-- tests/
+-- mcp_server.py
`-- requirements.txt
```

## Install With Conda

```bash
conda env create -f environment.yml
conda activate DrugAgent
```

This environment sets `PYTHONNOUSERSITE=1` so Python will not load packages from the user-level `AppData/Roaming` site-packages directory.

If the conda solver cannot find the latest `mcp` package, install the pip dependencies after activating the environment:

```bash
pip install -r requirements.txt
```

If you created the environment before `PYTHONNOUSERSITE` was added, run this once:

```powershell
conda env config vars set PYTHONNOUSERSITE=1 -n DrugAgent
conda deactivate
conda activate DrugAgent
```

## Run Model API

```bash
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Check:

```bash
curl http://127.0.0.1:8000/health
```

## Run MCP Server

```bash
python mcp_server.py
```

The MCP server registers:

- `search_molecule`: search PubChem by SMILES and return molecule metadata plus SDF.
- `predict_molecule_property`: call the FastAPI model wrapper.

## Run Real Test Scripts

```bash
python tests/run_api_client.py
```

The API test requires the FastAPI server to be running first.

```bash
python tests/run_search_molecule_tool.py
```

The PubChem tool test requires network access.

```bash
python tests/run_mcp_client.py --skip-pubchem
```

The MCP client test starts `mcp_server.py` through stdio automatically. Keep the FastAPI server running because `predict_molecule_property` calls it.
