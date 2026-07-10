"""Application entry point."""

from __future__ import annotations

import sys


def main() -> int:
    from easypal_next.app.application import run_application

    return run_application(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
