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

## Conda Install

Use a dedicated conda environment for MMCLKin. The original MMCLKin project was tested with Python 3.8, PyTorch 1.12, CUDA 11, DGL, PyG, RDKit, ESM, and Transformers.

```bash
conda create -y -n MMCLKin python=3.8 pip
conda activate MMCLKin

pip install --upgrade pip
pip install torch==1.12.1+cu116 torchvision==0.13.1+cu116 torchaudio==0.12.1 \
  --extra-index-url https://download.pytorch.org/whl/cu116

pip install --pre dgl-cu116 -f https://data.dgl.ai/wheels-test/repo.html
pip install --no-cache-dir --only-binary=:all: \
  pyg_lib torch_geometric torch_scatter torch_sparse torch_cluster torch_spline_conv \
  -f https://data.pyg.org/whl/torch-1.12.1+cu116.html

pip install fastapi==0.115.12 "uvicorn[standard]==0.30.6" pydantic==2.10.6 httpx==0.28.1 \
  rdkit==2024.3.5 biopython==1.83 transformers==4.46.3 scikit-learn==1.3.2 \
  pandas==2.0.3 sympy==1.13.3 networkx==2.7.1

conda install -y -c conda-forge cudatoolkit=11.6
```

`cudatoolkit=11.6` provides CUDA runtime libraries such as `libcusparse.so.11` required by `dgl-cu116`. The API launcher adds `$CONDA_PREFIX/lib` to `LD_LIBRARY_PATH` automatically when the conda environment is active.

The first startup downloads ESM-1b and ChemBERTa weights if they are not already cached. ESM-1b is large, approximately 7.3 GB under `~/.cache/torch/hub/checkpoints`.

If the machine has a newer GPU architecture that PyTorch 1.12 does not support, such as NVIDIA H20/sm_90, start with CPU mode:

```bash
export MMCLKIN_DEVICE=cpu
```

On GPUs supported by PyTorch 1.12/cu116, keep the default `MMCLKIN_DEVICE=auto`.

## Start

From `C:\Project\DrugAgent`:

```bash
conda activate MMCLKin
bash api/mmclkin/start_api.sh
```

or:

```bash
uvicorn api.mmclkin.api:app --host 0.0.0.0 --port 8020
```

For this workspace on Linux, start from `/home/hongyuyang_cluster/project/DrugAgent`. On H20, use:

```bash
conda activate MMCLKin
export MMCLKIN_DEVICE=cpu
export MMCLKIN_API_HOST=127.0.0.1
export MMCLKIN_API_PORT=8020
bash api/mmclkin/start_api.sh
```

## Test

Use database IDs from `new_3dkdavis_overall.csv`. For example, `ABL1` and ligand `11314340` exist in the bundled CSV.

```bash
python tests/test_mmclkin_api.py --base-url http://127.0.0.1:8020 --ligand-id 11314340 --kinase-id ABL1 --panel ABL1 EGFR KIT
```

The smoke test disables environment proxy variables for local requests. If testing manually with `curl`, use `--noproxy '*'` when proxy variables are set:

```bash
curl --noproxy '*' http://127.0.0.1:8020/health
curl --noproxy '*' -X POST http://127.0.0.1:8020/api/mmclkin/affinity \
  -H 'Content-Type: application/json' \
  -d '{"kinase_id":"ABL1","ligand_id":"11314340","dataset":"3DKDavis","structure_source":"mmclkin_database"}'
```

Verified in the `MMCLKin` conda environment on this workspace:

- `GET /health` returned `{"status":"ok","model":"MMCLKin"}`.
- `POST /api/mmclkin/affinity` with ABL1 and ligand 11314340 returned `predicted_affinity: 4.659635`.
- `POST /api/mmclkin/selectivity` with panel `ABL1 EGFR KIT` returned affinity profile values `5.418914`, `5.332935`, and `6.110356`.

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
