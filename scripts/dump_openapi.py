import json
import os
import sys
from pathlib import Path

os.environ["AUTH_DISABLED"] = "true"
os.environ["ENVIRONMENT"] = "development"
os.environ["DATABASE_PASSWORD"] = "openapi-gen-placeholder"  # noqa: S105

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from compgraph.main import app

HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


def _sort_path_methods(spec: dict) -> dict:
    """Sort HTTP methods within each path for deterministic output."""
    paths = spec.get("paths", {})
    for path_key, path_item in paths.items():
        sorted_item = {}
        for k, v in path_item.items():
            if k not in HTTP_METHODS:
                sorted_item[k] = v
        for method in HTTP_METHODS:
            if method in path_item:
                sorted_item[method] = path_item[method]
        paths[path_key] = sorted_item
    return spec


def generate_openapi():
    output_path = Path(__file__).resolve().parent.parent / "openapi.json"
    spec = _sort_path_methods(app.openapi())
    with open(output_path, "w") as f:
        json.dump(spec, f, indent=2)
        f.write("\n")
    print(f"Successfully dumped {output_path}")


if __name__ == "__main__":
    generate_openapi()
