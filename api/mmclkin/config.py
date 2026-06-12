import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MMCLKIN_ROOT = Path(os.getenv("MMCLKIN_ROOT", PROJECT_ROOT / "models" / "MMCLKin"))


@dataclass(frozen=True)
class MMCLKinSettings:
    host: str = os.getenv("MMCLKIN_API_HOST", "0.0.0.0")
    port: int = int(os.getenv("MMCLKIN_API_PORT", "8020"))
    dataset: str = os.getenv("MMCLKIN_DATASET", "3DKDavis")
    structure_source: str = os.getenv("MMCLKIN_STRUCTURE_SOURCE", "mmclkin_database")
    device: str = os.getenv("MMCLKIN_DEVICE", "auto")
    auto_extract_archives: bool = os.getenv("MMCLKIN_AUTO_EXTRACT", "1") not in {"0", "false", "False"}
    chemberta_model: str = os.getenv("MMCLKIN_CHEMBERTA_MODEL", "DeepChem/ChemBERTa-10M-MLM")

    mmclkin_root: Path = MMCLKIN_ROOT
    dataset_root: Path = Path(
        os.getenv("MMCLKIN_3DKDAVIS_ROOT", MMCLKIN_ROOT / "datasets" / "3DKDavis")
    )
    overall_csv: Path = Path(
        os.getenv(
            "MMCLKIN_3DKDAVIS_CSV",
            MMCLKIN_ROOT / "datasets" / "3DKDavis" / "new_3dkdavis_overall.csv",
        )
    )
    kinase_pdb_dir: Path = Path(
        os.getenv(
            "MMCLKIN_KINASE_PDB_DIR",
            MMCLKIN_ROOT / "datasets" / "3DKDavis" / "3dkdavis_kinase_pdbs",
        )
    )
    pocket_pdb_dir: Path = Path(
        os.getenv("MMCLKIN_POCKET_PDB_DIR", MMCLKIN_ROOT / "datasets" / "3DKDavis" / "pockets")
    )
    ligand_sdf_dir: Path = Path(
        os.getenv(
            "MMCLKIN_LIGAND_SDF_DIR",
            MMCLKIN_ROOT / "datasets" / "3DKDavis" / "ligand_sdfs",
        )
    )
    affinity_checkpoint: Path = Path(
        os.getenv(
            "MMCLKIN_AFFINITY_CKPT",
            MMCLKIN_ROOT / "ckpt" / "MMCLKin_3dkdavis_affinity.pkl",
        )
    )
    selectivity_checkpoint: Path = Path(
        os.getenv(
            "MMCLKIN_SELECTIVITY_CKPT",
            MMCLKIN_ROOT / "ckpt" / "MMCLKin_3dkdavis_selectivity.pkl",
        )
    )


settings = MMCLKinSettings()
