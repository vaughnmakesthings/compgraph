import json
import os
import sys

# Force AUTH_DISABLED before importing compgraph to avoid pydantic validation
# errors on missing secrets (Settings() is instantiated at import time)
os.environ["AUTH_DISABLED"] = "true"

# Add src to sys.path to allow importing compgraph
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from compgraph.main import app


def generate_openapi():
    with open("openapi.json", "w") as f:
        json.dump(app.openapi(), f, indent=2)
    print("Successfully dumped openapi.json")


if __name__ == "__main__":
    generate_openapi()
