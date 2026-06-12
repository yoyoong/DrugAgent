# Kinase Inhibitor Prediction

Use this skill when the user wants MMCLKin-based kinase-inhibitor affinity prediction or inhibitor selectivity prediction across a kinase panel.

## Scope

This skill coordinates inputs and calls the MMCLKin MCP tools. It does not run the deep learning model directly.

The first version prioritizes compounds and kinases already present in the local MMCLKin 3DKDavis database.

## Task Types

Classify the request as one of:

- `affinity`: one kinase plus one inhibitor
- `selectivity`: one inhibitor plus multiple kinases or a kinase panel

If the task type is ambiguous, ask for the missing kinase, inhibitor, or panel information.

## Required Inputs

Collect:

- `task_type`: `affinity` or `selectivity`
- `kinase_id` or `kinase_name` for affinity prediction
- `kinase_panel` for selectivity prediction
- `ligand_id`, `ligand_smiles`, or `ligand_sdf`
- `dataset`, default `3DKDavis`
- `structure_source`, default `mmclkin_database`

For the base workflow, prefer MMCLKin database IDs:

- kinase: `target_name`, UniProt ID, or `protein_id` from `new_3dkdavis_overall.csv`
- ligand: `com_name` or `drug_id` from `new_3dkdavis_overall.csv`

## Input Lookup Workflow

1. Check the local MMCLKin 3DKDavis CSV to confirm the kinase exists.
2. Check the local MMCLKin 3DKDavis CSV and `ligand_sdfs` directory to confirm the ligand exists.
3. If the user provides only ligand SMILES, call `search_compound_tool` to obtain SDF information where possible, but explain that the first MMCLKin API version only predicts directly for ligands present in the MMCLKin database.
4. If the kinase is not present, report that the first version does not support it.
5. Do not fetch new kinase structures from RCSB PDB or AlphaFold DB in the first version.
6. Do not run P2Rank pocket prediction in the first version.

## MCP Tool Calls

Affinity prediction:

```text
predict_kinase_inhibitor_affinity
```

Arguments:

```json
{
  "kinase_id": "ABL1",
  "ligand_id": "11314340",
  "dataset": "3DKDavis",
  "structure_source": "mmclkin_database"
}
```

Selectivity prediction:

```text
predict_kinase_inhibitor_selectivity
```

Arguments:

```json
{
  "ligand_id": "11314340",
  "kinase_panel": ["ABL1", "EGFR", "KIT"],
  "dataset": "3DKDavis",
  "structure_source": "mmclkin_database"
}
```

## Response Handling

For affinity prediction, return:

- predicted affinity value
- dataset
- kinase structure source
- ligand structure source
- whether MMCLKin database structures were used
- warnings from the API

For selectivity prediction, return:

- affinity profile for each kinase
- selectivity metrics, including Gini and selectivity entropy
- dataset and structure source
- warnings from the API

## Constraints

- Do not claim a prediction was completed unless the MMCLKin MCP tool returned a successful result from the MMCLKin API.
- If a ligand or kinase is not in the MMCLKin database, explicitly say so.
- The first version does not automatically download structures from RCSB PDB or AlphaFold DB.
- The first version does not automatically run P2Rank.
- Future versions may extend the workflow with external structure retrieval and pocket prediction.
