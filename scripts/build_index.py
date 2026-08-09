from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.retrieval.search import build_index


def main() -> None:
    print(json.dumps(build_index("."), indent=2))


if __name__ == "__main__":
    main()
