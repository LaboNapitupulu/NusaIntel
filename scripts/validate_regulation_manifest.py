from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "backend"))

from app.regulasilens.manifest import load_manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a RegulasiLens source manifest"
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=REPOSITORY_ROOT
        / "regulations"
        / "manifests"
        / "personal-data-protection.v1.json",
    )
    arguments = parser.parse_args()
    manifest = load_manifest(arguments.manifest)
    print(
        f"valid corpus={manifest.corpus_id} version={manifest.corpus_version} "
        f"documents={len(manifest.documents)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
