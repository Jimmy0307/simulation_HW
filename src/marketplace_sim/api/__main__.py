"""Run the local API: python -m marketplace_sim.api [--pack synthetic|private] [--path DIR] [--save FILE] [--port N].

Binds to loopback only (127.0.0.1). It is a local tool for one operator, never a server on a network.
"""

from __future__ import annotations

import argparse

import uvicorn

from marketplace_sim.api import service as svc
from marketplace_sim.api.app import create_app

LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pack", choices=["synthetic", "private"], default="synthetic")
    parser.add_argument("--path", help="pack directory (default: examples/synthetic or evidence/private/model)")
    parser.add_argument("--save", help="open an mpsim save instead (its pack is used)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.host not in LOOPBACK:
        raise SystemExit("the local API only binds to loopback (127.0.0.1 / localhost / ::1)")
    session = svc.Session()
    if args.save:
        svc.load_save(session, args.save)
    else:
        svc.load_pack_into(session, args.pack, args.path)
    info = svc.pack_info(session)
    print(f"mpsim API on http://{args.host}:{args.port}  pack={info['name']} private={info['is_private']}")
    uvicorn.run(create_app(session), host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
