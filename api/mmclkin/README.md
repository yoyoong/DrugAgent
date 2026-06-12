# MMCLKin API

FastAPI wrapper for MMCLKin kinase-inhibitor affinity and selectivity prediction.

## Files

- `api.py`: FastAPI app and routes
- `predictor.py`: model loading, database lookup, feature construction, and inference
- `schemas.py`: Pydantic request/response models
- `config.py`: environment-driven paths and runtime settings
- `start_api.sh`: shell launcher

## Data And Weights

Default paths are relative to `C:\Project\DrugAgent`:

- MMCLKin repo: `models/MMCLKin`
- 3DKDavis CSV: `models/MMCLKin/datasets/3DKDavis/new_3dkdavis_overall.csv`
- Kinase PDBs: `models/MMCLKin/datasets/3DKDavis/3dkdavis_kinase_pdbs`
- Pocket PDBs: `models/MMCLKin/datasets/3DKDavis/pockets`
- Ligand SDFs: `models/MMCLKin/datasets/3DKDavis/ligand_sdfs`
- Affinity checkpoint: `models/MMCLKin/ckpt/MMCLKin_3dkdavis_affinity.pkl`
- Selectivity checkpoint: `models/MMCLKin/ckpt/MMCLKin_3dkdavis_selectivity.pkl`

If the three 3DKDavis structure directories are absent but the bundled `.tar.gz` archives are present, the service extracts them on startup by default. Set `MMCLKIN_AUTO_EXTRACT=0` to disable this.

Important environment variables:

```bash
MMCLKIN_ROOT=C:/Project/DrugAgent/models/MMCLKin
MMCLKIN_3DKDAVIS_ROOT=C:/Project/DrugAgent/models/MMCLKin/datasets/3DKDavis
MMCLKIN_AFFINITY_CKPT=C:/Project/DrugAgent/models/MMCLKin/ckpt/MMCLKin_3dkdavis_affinity.pkl
MMCLKIN_SELECTIVITY_CKPT=C:/Project/DrugAgent/models/MMCLKin/ckpt/MMCLKin_3dkdavis_selectivity.pkl
MMCLKIN_DEVICE=auto
MMCLKIN_API_HOST=0.0.0.0
MMCLKIN_API_PORT=8020
```

## Install

Use an MMCLKin-compatible Python environment. The original project was tested with Python 3.8, PyTorch 1.12, CUDA 11, DGL, PyG, RDKit, ESM, and Transformers.

```bash
pip install -r api/mmclkin/requirements.txt
```

The first startup may download ESM-1b and ChemBERTa weights if they are not already cached.

## Start

From `C:\Project\DrugAgent`:

```bash
bash api/mmclkin/start_api.sh
```

or:

```bash
uvicorn api.mmclkin.api:app --host 0.0.0.0 --port 8020
```

## Test

Use database IDs from `new_3dkdavis_overall.csv`. For example, `ABL1` and ligand `11314340` exist in the bundled CSV.

```bash
python tests/test_mmclkin_api.py --base-url http://127.0.0.1:8020 --ligand-id 11314340 --kinase-id ABL1 --panel ABL1 EGFR KIT
```

## Endpoints

### POST `/api/mmclkin/affinity`

```json
{
  "kinase_id": "ABL1",
  "ligand_id": "11314340",
  "dataset": "3DKDavis",
  "structure_source": "mmclkin_database"
}
```

### POST `/api/mmclkin/selectivity`

```json
{
  "ligand_id": "11314340",
  "kinase_panel": ["ABL1", "EGFR", "KIT"],
  "dataset": "3DKDavis",
  "structure_source": "mmclkin_database"
}
```

## Current Scope

This first version supports only kinase and ligand entries already present in the local MMCLKin 3DKDavis database. It does not download new kinase structures from RCSB PDB or AlphaFold DB, and it does not run P2Rank for new pocket prediction.
