# Molecule Property Prediction

Use this skill when the user wants to predict molecule properties from a SMILES string.

Call the MCP tool:

```text
predict_molecule_property
```

Input:

- `smiles`: molecule SMILES string

Output:

- model name
- model version
- supported properties
- demo prediction result

This demo calls the FastAPI model wrapper. The real model source code can be added under:

```text
models/molecule_property_prediction/
```
