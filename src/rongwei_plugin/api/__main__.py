"""Run the local HTTP adapter with a loopback-only bind by default."""
from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("RONGWEI_HOST", "127.0.0.1")
    if host not in {"127.0.0.1", "localhost", "::1"} and not os.getenv("RONGWEI_API_KEY"):
        raise SystemExit(
            "Refusing to bind HTTP tools publicly without RONGWEI_API_KEY configured."
        )
    port = int(os.getenv("RONGWEI_PORT", "8000"))
    uvicorn.run("rongwei_plugin.api.app:app", host=host, port=port)


if __name__ == "__main__":
    main()
