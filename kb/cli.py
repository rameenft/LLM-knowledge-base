"""Local operations CLI.

    python -m kb.cli upload-raw [dir]     upload raw notes to storage (skips unchanged)
    python -m kb.cli run [--force]        run the ingestion pipeline
    python -m kb.cli status               show what storage currently holds
Backend is chosen by KB_STORAGE_BACKEND (local | azure); see kb/storage.py.
"""

import argparse
import json
import logging

from . import config, pipeline, runtime


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("azure").setLevel(logging.WARNING)  # SDK logs every HTTP call at INFO
    p = argparse.ArgumentParser(prog="kb.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    up = sub.add_parser("upload-raw")
    up.add_argument("directory", nargs="?", default=str(config.RAW_DIR))
    run = sub.add_parser("run")
    run.add_argument("--force", action="store_true")
    sub.add_parser("status")
    args = p.parse_args(argv)

    storage = runtime.get_storage()
    if args.cmd == "upload-raw":
        print(json.dumps(pipeline.sync_raw_dir(storage, args.directory), indent=2))
    elif args.cmd == "run":
        try:
            report = runtime.run_ingestion(force=args.force)
        except config.ConfigError as e:
            print(e)
            return 2
        print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.ok else 1
    else:
        print(json.dumps({c: storage.list(c) for c in ("raw", "processed", "artifacts", "quarantine")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
