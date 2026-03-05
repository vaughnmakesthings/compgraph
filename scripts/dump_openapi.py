import json
import os
import sys
from pathlib import Path

os.environ["AUTH_DISABLED"] = "true"
os.environ["ENVIRONMENT"] = "development"
os.environ["DATABASE_PASSWORD"] = "openapi-gen-placeholder"  # noqa: S105

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from compgraph.main import app


def generate_openapi():
    output_path = Path(__file__).resolve().parent.parent / "openapi.json"
    with open(output_path, "w") as f:
        json.dump(app.openapi(), f, indent=2)
    print(f"Successfully dumped {output_path}")


if __name__ == "__main__":
    generate_openapi()
