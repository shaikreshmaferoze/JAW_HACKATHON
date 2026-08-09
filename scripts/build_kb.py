from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.knowledge_base.build import build_kb


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-extract", action="store_true")
    args = parser.parse_args()
    stats = build_kb(".", force_extract=args.force_extract)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
