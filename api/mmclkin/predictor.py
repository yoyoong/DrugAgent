from __future__ import annotations

import csv
import math
import os
import sys
import tarfile
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import MMCLKinSettings
from .schemas import (
    AffinityProfileItem,
    AffinityRequest,
    AffinityResponse,
    SelectivityMetrics,
    SelectivityRequest,
    SelectivityResponse,
)


class MMCLKinPredictionError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400, warnings: list[str] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.warnings = warnings or []


class MMCLKinPredictor:
    def __init__(self, settings: MMCLKinSettings):
        self.settings = settings
        self.device = None
        self.affinity_model = None
        self.selectivity_model = None
        self.esm_model = None
        self.esm_batch_converter = None
        self.chem_model = None
        self.chem_tokenizer = None
        self.rows: list[dict[str, str]] = []
        self.kinase_index: dict[str, dict[str, str]] = {}
        self.ligand_index: dict[str, dict[str, str]] = {}

    def load(self) -> None:
        self._prepare_paths()
        self.rows = self._load_rows()
        self.kinase_index, self.ligand_index = self._build_indexes(self.rows)

        mmclkin_root = str(self.settings.mmclkin_root)
        if mmclkin_root not in sys.path:
            sys.path.insert(0, mmclkin_root)

        try:
            import torch
            import esm
            from model import MMCLKin
            from transformers import AutoModel, AutoTokenizer
        except Exception as exc:
            raise MMCLKinPredictionError(
                "MMCLKin dependencies are not available. Install api/mmclkin/requirements.txt "
                f"in the runtime environment. Import error: {exc}",
                status_code=500,
            ) from exc

        if self.settings.device == "auto":
            self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(self.settings.device)

        self.affinity_model = self._load_mmclkin_model(
            MMCLKin,
            self.settings.affinity_checkpoint,
            hidden_dim=256,
            dropout_rate=0.3,
        )
        self.selectivity_model = self._load_mmclkin_model(
            MMCLKin,
            self.settings.selectivity_checkpoint,
            hidden_dim=512,
            dropout_rate=0.4,
        )

        self.esm_model, alphabet = esm.pretrained.esm1b_t33_650M_UR50S()
        self.esm_model.to(self.device)
        self.esm_model.eval()
        self.esm_batch_converter = alphabet.get_batch_converter()

        self.chem_tokenizer = AutoTokenizer.from_pretrained(self.settings.chemberta_model)
        self.chem_model = AutoModel.from_pretrained(self.settings.chemberta_model)
        self.chem_model.to(self.device)
        self.chem_model.eval()

    def predict_affinity(self, request: AffinityRequest) -> AffinityResponse:
        self._validate_request_metadata(request.dataset, request.structure_source)
        kinase = self._resolve_kinase(request.kinase_id)
        ligand = self._resolve_ligand(request.ligand_id)
        score = self._predict_pair(self.affinity_model, kinase, ligand)
        return AffinityResponse(
            kinase_id=request.kinase_id,
            ligand_id=request.ligand_id,
            predicted_affinity=score,
            dataset=request.dataset,
            structure_source=request.structure_source,
            warnings=[],
        )

    def predict_selectivity(self, request: SelectivityRequest) -> SelectivityResponse:
        self._validate_request_metadata(request.dataset, request.structure_source)
        ligand = self._resolve_ligand(request.ligand_id)
        profile: list[AffinityProfileItem] = []
        for kinase_id in request.kinase_panel:
            kinase = self._resolve_kinase(kinase_id)
            score = self._predict_pair(self.selectivity_model, kinase, ligand)
            profile.append(AffinityProfileItem(kinase_id=kinase_id, predicted_affinity=score))

        values = [item.predicted_affinity for item in profile]
        return SelectivityResponse(
            ligand_id=request.ligand_id,
            affinity_profile=profile,
            selectivity_metrics=SelectivityMetrics(
                gini=_gini(values),
                selectivity_entropy=_selectivity_entropy(values),
            ),
            dataset=request.dataset,
            structure_source=request.structure_source,
            warnings=[],
        )

    def _load_mmclkin_model(self, model_cls: Any, checkpoint: Path, hidden_dim: int, dropout_rate: float):
        if not checkpoint.exists():
            raise MMCLKinPredictionError(f"MMCLKin checkpoint not found: {checkpoint}", status_code=500)

        import torch

        model = model_cls(
            lstm_dropout=0.2,
            alpha=0.2,
            num_heads=2,
            hidden_dim=hidden_dim,
            dropout_rate=dropout_rate,
            n_head=8,
            smile_vocab=63,
            local_rank=self.device,
        )
        state = torch.load(checkpoint, map_location=self.device)
        model.load_state_dict(state["model"] if isinstance(state, dict) and "model" in state else state, strict=True)
        model.to(self.device)
        model.eval()
        return model

    def _predict_pair(self, model: Any, kinase: dict[str, str], ligand: dict[str, str]) -> float:
        import torch

        x_feats = self._build_x_feats(kinase, ligand).to(self.device)
        with torch.no_grad():
            prediction = model(x_feats)[0].reshape(-1)[0]
        return round(float(prediction.detach().cpu().item()), 6)

    def _build_x_feats(self, kinase: dict[str, str], ligand: dict[str, str]):
        from torch_geometric.data import Data
        import torch

        kinase_feature = self._kinase_feature(kinase["uniprot_id"])
        pocket_feature = self._pocket_feature(kinase["uniprot_id"])
        ligand_feature = self._ligand_feature(ligand["com_name"])

        pocinpro_index = [
            kinase_feature.pro_index.index(residue)
            for residue in pocket_feature.pro_index
            if residue in kinase_feature.pro_index
        ]
        if not pocinpro_index:
            raise MMCLKinPredictionError(
                f"No pocket residues could be aligned to kinase {kinase['target_name']} ({kinase['uniprot_id']}).",
                status_code=500,
            )

        return Data(
            mol_batch=torch.zeros(ligand_feature.mol_atoms_feats.shape[0], dtype=torch.int64),
            poc_batch=torch.zeros(pocket_feature.pro_atoms_feats_s.shape[0], dtype=torch.int64),
            pro_batch=torch.zeros(kinase_feature.pro_atoms_feats_s.shape[0], dtype=torch.int64),
            atominmol_indexes=[torch.tensor(ligand_feature.atoinmol_index).type(torch.long)],
            pocinpro_indexes=[torch.tensor([x for x in pocinpro_index if x <= 1022]).type(torch.long)],
            subwinsmi_indexes=[torch.tensor(ligand_feature.subwinsmi_index).type(torch.long)],
            po_dist=pocket_feature.pr_dist,
            po_theta=pocket_feature.pr_theta,
            po_phi=pocket_feature.pr_phi,
            po_tau=pocket_feature.pr_tau,
            mol_dist=ligand_feature.mol_dist,
            mol_theta=ligand_feature.mol_theta,
            mol_phi=ligand_feature.mol_phi,
            mol_tau=ligand_feature.mol_tau,
            pr_dist=kinase_feature.pr_dist,
            pr_theta=kinase_feature.pr_theta,
            pr_phi=kinase_feature.pr_phi,
            pr_tau=kinase_feature.pr_tau,
            mol_atoms_feats=ligand_feature.mol_atoms_feats,
            mol_edges_feats=ligand_feature.mol_edges_feats,
            mol_coords_feats=ligand_feature.mol_coords_feats,
            mol_edge_index=ligand_feature.mol_edge_index.type(torch.long),
            mol_embedding=ligand_feature.mol_embedding,
            poc_coords_feats=pocket_feature.pro_coords_feats,
            poc_atoms_feats_s=pocket_feature.pro_atoms_feats_s,
            poc_edges_feats_s=pocket_feature.pro_edges_feats_s,
            poc_atoms_feats_v=pocket_feature.pro_atoms_feats_v,
            poc_edges_feats_v=pocket_feature.pro_edges_feats_v,
            poc_edge_index=pocket_feature.pro_edge_index.type(torch.long),
            poc_token_repre=pocket_feature.pro_token_repre,
            pro_atoms_feats_s=kinase_feature.pro_atoms_feats_s,
            pro_atoms_feats_v=kinase_feature.pro_atoms_feats_v,
            pro_coords_feats=kinase_feature.pro_coords_feats,
            pro_edges_feats_s=kinase_feature.pro_edges_feats_s,
            pro_edges_feats_v=kinase_feature.pro_edges_feats_v,
            pro_edge_index=kinase_feature.pro_edge_index.type(torch.long),
            pro_token_repre=kinase_feature.pro_token_repre,
        )

    @lru_cache(maxsize=256)
    def _kinase_feature(self, uniprot_id: str):
        return self._protein_feature(self._kinase_pdb_path(uniprot_id))

    @lru_cache(maxsize=256)
    def _pocket_feature(self, uniprot_id: str):
        return self._protein_feature(self._pocket_pdb_path(uniprot_id))

    @lru_cache(maxsize=1024)
    def _ligand_feature(self, com_name: str):
        from feature_extracted import generate_smiles_nodes_edges_coords_graph_index_features
        from torch_geometric.data import Data

        sdf_path = self._ligand_sdf_path(com_name)
        (
            mol_atoms_feats,
            mol_edges_feats,
            mol_coords_feats,
            mol_graph,
            mol_edge_index,
            mol_smiles,
            atom_types,
        ) = generate_smiles_nodes_edges_coords_graph_index_features("sdf", str(sdf_path))
        mol_dist, mol_theta, mol_phi, mol_tau = self._generate_inner_coor(
            mol_coords_feats, mol_atoms_feats, mol_edge_index
        )
        atoinmol_index, subwinsmi_index, mol_embedding = self._generate_ligand_indexes(atom_types, mol_smiles)
        return Data(
            mol_atoms_feats=mol_atoms_feats,
            mol_edges_feats=mol_edges_feats,
            mol_coords_feats=mol_coords_feats,
            atoinmol_index=atoinmol_index,
            subwinsmi_index=subwinsmi_index,
            mol_embedding=mol_embedding,
            mol_graphs=mol_graph,
            mol_edge_index=mol_edge_index,
            mol_seq=mol_smiles,
            mol_dist=mol_dist,
            mol_theta=mol_theta,
            mol_phi=mol_phi,
            mol_tau=mol_tau,
        )

    def _protein_feature(self, pdb_path: Path):
        from feature_extracted import generate_graph_feature
        from torch_geometric.data import Data
        import torch

        pro_index = _gen_seq_list(pdb_path)
        protein, protein_graph, _coords = generate_graph_feature(str(pdb_path))
        protein_sequence = _generate_protein_sequence(pdb_path)
        pr_dist, pr_theta, pr_phi, pr_tau = self._generate_inner_coor(
            protein.x, protein.node_s, protein.edge_index
        )

        prot = [(0, protein_sequence[:1022])]
        _labels, _strs, batch_tokens = self.esm_batch_converter(prot)
        batch_tokens = batch_tokens.to(self.device)
        with torch.no_grad():
            results = self.esm_model(batch_tokens, repr_layers=[33], return_contacts=True)
        pro_token_repre = results["representations"][33].detach().cpu()

        return Data(
            pro_graphs=protein_graph,
            pro_index=pro_index,
            pro_atoms_feats_s=protein.node_s,
            pro_atoms_feats_v=protein.node_v,
            pro_coords_feats=protein.x,
            pro_edges_feats_s=protein.edge_s,
            pro_edges_feats_v=protein.edge_v,
            pro_edge_index=protein.edge_index,
            pro_token_repre=pro_token_repre,
            pro_fp=protein_sequence,
            pr_dist=pr_dist,
            pr_theta=pr_theta,
            pr_phi=pr_phi,
            pr_tau=pr_tau,
        )

    def _generate_ligand_indexes(self, atom_types: list[str], mol_smiles: str):
        import torch

        ignored_prefixes = {"Z", "h", "i", "M", "g", "V", "T", "l", "H", "e", "r", "R", "u", "t"}
        atoinmol_index = [idx for idx, atom_type in enumerate(atom_types) if atom_type[0] not in ignored_prefixes]
        tokenized = self.chem_tokenizer(mol_smiles, padding=True, truncation=True, return_tensors="pt")
        tokenized = {key: value.to(self.device) for key, value in tokenized.items()}
        subwords = self.chem_tokenizer.tokenize(mol_smiles)
        with torch.no_grad():
            embedding = self.chem_model(**tokenized).last_hidden_state.detach().cpu()

        subwinsmi_index = [idx for idx, token in enumerate(subwords) if token.isalpha()]
        atom_symbols = [atom_type[0].upper() for atom_type in atom_types]
        subword_symbols = [token.upper() for token in subwords if token.isalpha()]
        if atom_symbols != subword_symbols:
            differing = set(atom_symbols) ^ set(subword_symbols)
            if len(atom_types) > len(subword_symbols):
                atoinmol_index = [
                    idx
                    for idx, atom_type in enumerate(atom_types)
                    if atom_type.isalpha() and atom_type not in differing and atom_type[0] not in ignored_prefixes
                ]
            elif len(atom_types) < len(subword_symbols):
                subwinsmi_index = [
                    idx for idx, token in enumerate(subwords) if token.isalpha() and token.upper() not in differing
                ]

        if not atoinmol_index or not subwinsmi_index:
            raise MMCLKinPredictionError(
                f"Could not align ligand atom features with ChemBERTa tokens for SMILES: {mol_smiles}",
                status_code=500,
            )
        return atoinmol_index, subwinsmi_index, embedding

    def _generate_inner_coor(self, pos: Any, atom_feats: Any, edge_index: Any):
        import torch
        from torch_scatter import scatter_min

        cutoff = 8.0
        num_nodes = atom_feats.size(0)
        j, i = edge_index
        vecs = pos[j] - pos[i]
        dist = vecs.norm(dim=-1)

        _min0, argmin0 = scatter_min(dist, i, dim_size=num_nodes)
        argmin0[argmin0 >= len(i)] = 0
        n0 = j[argmin0]
        add = torch.zeros_like(dist).to(dist.device)
        add[argmin0] = cutoff
        dist1 = dist + add
        _min1, argmin1 = scatter_min(dist1, i, dim_size=num_nodes)
        argmin1[argmin1 >= len(i)] = 0
        n1 = j[argmin1]

        _min0_j, argmin0_j = scatter_min(dist, j, dim_size=num_nodes)
        argmin0_j[argmin0_j >= len(j)] = 0
        n0_j = i[argmin0_j]
        add_j = torch.zeros_like(dist).to(dist.device)
        add_j[argmin0_j] = cutoff
        dist1_j = dist + add_j
        _min1_j, argmin1_j = scatter_min(dist1_j, j, dim_size=num_nodes)
        argmin1_j[argmin1_j >= len(j)] = 0
        n1_j = i[argmin1_j]

        n0 = n0[i]
        n1 = n1[i]
        n0_j = n0_j[j]
        n1_j = n1_j[j]

        mask_iref = n0 == j
        idx_iref = argmin0[i]
        idx_iref[mask_iref] = argmin1[i][mask_iref]
        mask_jref = n0_j == i
        idx_jref = argmin0_j[j]
        idx_jref[mask_jref] = argmin1_j[j][mask_jref]

        pos_ji = vecs
        pos_in0 = vecs[argmin0][i]
        pos_in1 = vecs[argmin1][i]
        pos_iref = vecs[idx_iref]
        pos_jref_j = vecs[idx_jref]

        a = ((-pos_ji) * pos_in0).sum(dim=-1)
        b = torch.cross(-pos_ji, pos_in0).norm(dim=-1)
        theta = torch.atan2(b, a)
        theta[theta < 0] = theta[theta < 0] + math.pi

        dist_ji = pos_ji.pow(2).sum(dim=-1).sqrt()
        plane1 = torch.cross(-pos_ji, pos_in0)
        plane2 = torch.cross(-pos_ji, pos_in1)
        a = (plane1 * plane2).sum(dim=-1)
        b = (torch.cross(plane1, plane2) * pos_ji).sum(dim=-1) / dist_ji
        phi = torch.atan2(b, a)
        phi[phi < 0] = phi[phi < 0] + math.pi

        plane1 = torch.cross(pos_ji, pos_jref_j)
        plane2 = torch.cross(pos_ji, pos_iref)
        a = (plane1 * plane2).sum(dim=-1)
        b = (torch.cross(plane1, plane2) * pos_ji).sum(dim=-1) / dist_ji
        tau = torch.atan2(b, a)
        tau[tau < 0] = tau[tau < 0] + math.pi
        return dist, theta, phi, tau

    def _validate_request_metadata(self, dataset: str, structure_source: str) -> None:
        if dataset != self.settings.dataset:
            raise MMCLKinPredictionError(f"Only {self.settings.dataset} is supported in the first version.")
        if structure_source != self.settings.structure_source:
            raise MMCLKinPredictionError(
                "Only mmclkin_database structures are supported in the first version."
            )

    def _resolve_kinase(self, kinase_id: str) -> dict[str, str]:
        row = self.kinase_index.get(_norm_id(kinase_id))
        if row is None:
            raise MMCLKinPredictionError(
                f"Kinase '{kinase_id}' was not found in the MMCLKin 3DKDavis database. "
                "Use a target_name, UniProt ID, or protein_id from new_3dkdavis_overall.csv.",
                status_code=404,
            )
        self._kinase_pdb_path(row["uniprot_id"])
        self._pocket_pdb_path(row["uniprot_id"])
        return row

    def _resolve_ligand(self, ligand_id: str) -> dict[str, str]:
        row = self.ligand_index.get(_norm_id(ligand_id))
        if row is None:
            raise MMCLKinPredictionError(
                f"Ligand '{ligand_id}' was not found in the MMCLKin 3DKDavis database. "
                "Use a com_name or drug_id from new_3dkdavis_overall.csv.",
                status_code=404,
            )
        self._ligand_sdf_path(row["com_name"])
        return row

    def _kinase_pdb_path(self, uniprot_id: str) -> Path:
        return self._require_file(self.settings.kinase_pdb_dir / f"{uniprot_id}_kinase.pdb")

    def _pocket_pdb_path(self, uniprot_id: str) -> Path:
        return self._require_file(self.settings.pocket_pdb_dir / f"{uniprot_id}_kinase_pocket.pdb")

    def _ligand_sdf_path(self, com_name: str) -> Path:
        return self._require_file(self.settings.ligand_sdf_dir / f"{com_name}.sdf")

    def _require_file(self, path: Path) -> Path:
        if not path.exists():
            raise MMCLKinPredictionError(f"Required MMCLKin database file not found: {path}", status_code=404)
        return path

    def _prepare_paths(self) -> None:
        if self.settings.auto_extract_archives:
            _extract_if_missing(
                self.settings.dataset_root / "3dkdavis_kinase_pdbs.tar.gz",
                self.settings.kinase_pdb_dir,
            )
            _extract_if_missing(self.settings.dataset_root / "pockets.tar.gz", self.settings.pocket_pdb_dir)
            _extract_if_missing(self.settings.dataset_root / "ligand_sdfs.tar.gz", self.settings.ligand_sdf_dir)

        missing = [
            str(path)
            for path in [
                self.settings.overall_csv,
                self.settings.kinase_pdb_dir,
                self.settings.pocket_pdb_dir,
                self.settings.ligand_sdf_dir,
                self.settings.affinity_checkpoint,
                self.settings.selectivity_checkpoint,
            ]
            if not path.exists()
        ]
        if missing:
            raise MMCLKinPredictionError(
                "MMCLKin database/checkpoint paths are missing: " + "; ".join(missing),
                status_code=500,
            )

    def _load_rows(self) -> list[dict[str, str]]:
        with self.settings.overall_csv.open(newline="", encoding="utf-8") as handle:
            return [
                {key: (value or "").strip() for key, value in row.items()}
                for row in csv.DictReader(handle)
            ]

    def _build_indexes(
        self, rows: list[dict[str, str]]
    ) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
        kinase_index: dict[str, dict[str, str]] = {}
        ligand_index: dict[str, dict[str, str]] = {}
        for row in rows:
            for key in (row.get("target_name"), row.get("uniprot_id"), row.get("protein_id")):
                if key:
                    kinase_index.setdefault(_norm_id(key), row)
            for key in (row.get("com_name"), row.get("drug_id")):
                if key:
                    ligand_index.setdefault(_norm_id(key), row)
        return kinase_index, ligand_index


def _generate_protein_sequence(pdb_path: Path) -> str:
    from Bio.PDB import PDBParser

    aa_codes = {
        "ALA": "A",
        "CYS": "C",
        "ASP": "D",
        "GLU": "E",
        "PHE": "F",
        "GLY": "G",
        "HIS": "H",
        "LYS": "K",
        "ILE": "I",
        "LEU": "L",
        "MET": "M",
        "ASN": "N",
        "PRO": "P",
        "GLN": "Q",
        "ARG": "R",
        "SER": "S",
        "THR": "T",
        "VAL": "V",
        "TYR": "Y",
        "TRP": "W",
    }
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("protein", str(pdb_path))
    sequence = ""
    for model in structure:
        for chain in model:
            for residue in chain:
                if (
                    residue.get_id()[0] == " "
                    and residue.get_resname() in aa_codes
                    and all(atom in residue for atom in ("N", "CA", "C", "O"))
                ):
                    sequence += aa_codes[residue.get_resname()]
    return sequence


def _gen_seq_list(pdb_path: Path) -> list[str]:
    from Bio.PDB import PDBParser

    valid = {
        "ALA",
        "CYS",
        "ASP",
        "GLU",
        "PHE",
        "GLY",
        "HIS",
        "ILE",
        "LYS",
        "LEU",
        "MET",
        "ASN",
        "PRO",
        "GLN",
        "ARG",
        "SER",
        "THR",
        "VAL",
        "TRP",
        "TYR",
    }
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure(str(pdb_path), str(pdb_path))
    residues = []
    for residue in structure.get_residues():
        hetero, residue_id, insertion = residue.full_id[-1]
        if (
            hetero == " "
            and residue.resname in valid
            and "CA" in residue
            and all(atom in residue for atom in ("N", "CA", "C", "O"))
        ):
            residues.append(f"{residue_id}{insertion}")
    return residues


def _extract_if_missing(archive_path: Path, expected_dir: Path) -> None:
    if expected_dir.exists() or not archive_path.exists():
        return
    with tarfile.open(archive_path, "r:gz") as archive:
        archive.extractall(archive_path.parent)


def _norm_id(value: str) -> str:
    return value.strip().lower()


def _gini(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(max(value, 0.0) for value in values)
    total = sum(sorted_values)
    if total == 0:
        return 0.0
    n = len(sorted_values)
    weighted_sum = sum((idx + 1) * value for idx, value in enumerate(sorted_values))
    return round((2 * weighted_sum) / (n * total) - (n + 1) / n, 6)


def _selectivity_entropy(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    max_value = max(values)
    weights = [math.exp(value - max_value) for value in values]
    total = sum(weights)
    probs = [weight / total for weight in weights if weight > 0]
    return round(-sum(prob * math.log(prob) for prob in probs), 6)
