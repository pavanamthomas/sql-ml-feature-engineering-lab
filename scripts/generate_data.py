"""Write the laboratory SQLite file under data/lab.sqlite."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sqlfeat.generate import DEFAULT_SEED, counts_by_table, generate_frames, write_database


def main() -> None:
    path = ROOT / "data" / "lab.sqlite"
    write_database(path, seed=DEFAULT_SEED, with_indexes=True)
    frames = generate_frames(seed=DEFAULT_SEED)
    counts = counts_by_table(frames)
    print(f"Wrote {path}")
    print(f"seed={DEFAULT_SEED}")
    for name, n in counts.items():
        print(f"  {name}: {n}")


if __name__ == "__main__":
    main()
