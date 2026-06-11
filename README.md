# DrugAgent

A minimal demo for building a drug-development agent with:

- Skills for Codex / Claude Code instructions
- FastAPI for wrapping model capabilities
- MCP tools for agent-callable functions
- A simple PubChem molecule search tool
- A remote FastAPI retrosynthesis prediction tool

## Project Layout

```text
DrugAgent/
+-- skills/
+-- models/
+-- tools/
+-- tests/
+-- .env
+-- mcp_server.py
`-- requirements.txt
```

## Install With Conda

```bash
conda env create -f environment.yml
conda activate DrugAgent
```

This environment sets `PYTHONNOUSERSITE=1` so Python will not load packages from the user-level `AppData/Roaming` site-packages directory.

Create local configuration from the example file if `.env` does not exist:

```bash
cp .env.example .env
```

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
uvicorn models.main:app --reload --host 172.25.16.31 --port 8000
```

Check:

```bash
curl http://172.25.16.31:8000/health
```

The default API and MCP settings are configured in `.env`:

```env
MODEL_API_HOST=172.25.16.31
MODEL_API_PORT=8000
MODEL_API_PORT_DCTBM=8010
MCP_HOST=172.25.16.31
MCP_PORT=8001
MCP_PATH=/mcp
MCP_TRANSPORT=streamable-http
```

## Run MCP Server

```bash
python mcp_server.py
```

The MCP server registers:

- `search_molecule`: search PubChem by SMILES and return molecule metadata plus SDF.
- `predict_retrosynthesis`: call the remote FastAPI retrosynthesis model wrapper.

## Run Real Test Scripts

```bash
python tests/run_api_client.py
```

The PubChem tool test requires network access.

```bash
python tests/run_mcp_client.py --skip-pubchem
```

The MCP client test starts `mcp_server.py` through stdio automatically. Keep the FastAPI server running because `predict_molecule_property` calls it.

```bash
python tests/run_retrosynthesis_mcp_client.py --smiles CCO
```

The retrosynthesis MCP test starts `mcp_server.py` through stdio automatically. Keep the remote retrosynthesis FastAPI service running on `MODEL_API_HOST:MODEL_API_HOST_DCTBM`.
