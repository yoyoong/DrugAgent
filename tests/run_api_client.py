import argparse
import json
from typing import Any

import httpx


def print_json(title: str, data: Any) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(data, ensure_ascii=False, indent=2))


def request_json(client: httpx.Client, method: str, path: str, **kwargs) -> Any:
    response = client.request(method, path, **kwargs)
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the real FastAPI model API check.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--smiles", default="CCO")
    args = parser.parse_args()

    with httpx.Client(base_url=args.base_url, timeout=20.0) as client:
        health = request_json(client, "GET", "/health")
        print_json("GET /health", health)

        info = request_json(client, "GET", "/models/info")
        print_json("GET /models/info", info)

        prediction = request_json(
            client,
            "POST",
            "/models/molecule_property_prediction",
            json={"smiles": args.smiles},
        )
        print_json("POST /models/molecule_property_prediction", prediction)

    print("\nAPI check passed.")


if __name__ == "__main__":
    main()
