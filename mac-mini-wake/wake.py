#!/usr/bin/env python3
"""Send a Wake-on-LAN magic packet.

Works with Python 3.8+ stdlib only — suitable for Synology Container Manager
or a DSM Task Scheduler script that has python3 available.
"""

from __future__ import annotations

import argparse
import os
import re
import socket
import sys
from pathlib import Path

MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}([:-]?)){5}[0-9A-Fa-f]{2}$")


def normalize_mac(mac: str) -> bytes:
    cleaned = mac.strip().replace("-", "").replace(":", "").replace(".", "")
    if len(cleaned) != 12 or any(c not in "0123456789abcdefABCDEF" for c in cleaned):
        raise ValueError(f"Invalid MAC address: {mac!r}")
    return bytes.fromhex(cleaned)


def build_magic_packet(mac: bytes) -> bytes:
    return b"\xff" * 6 + mac * 16


def send_magic_packet(
    mac: str,
    broadcast: str = "255.255.255.255",
    port: int = 9,
    count: int = 3,
) -> None:
    packet = build_magic_packet(normalize_mac(mac))
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for _ in range(max(1, count)):
            sock.sendto(packet, (broadcast, port))


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parent
    load_dotenv(root / "config.env")

    parser = argparse.ArgumentParser(description="Wake a machine via Wake-on-LAN")
    parser.add_argument(
        "--mac",
        default=os.environ.get("MAC_ADDRESS", ""),
        help="Target MAC address (or set MAC_ADDRESS in config.env)",
    )
    parser.add_argument(
        "--broadcast",
        default=os.environ.get("BROADCAST_ADDRESS", "255.255.255.255"),
        help="Broadcast / directed-broadcast address",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("WOL_PORT", "9")),
        help="UDP port (default 9)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=int(os.environ.get("PACKET_COUNT", "3")),
        help="How many packets to send",
    )
    args = parser.parse_args(argv)

    if not args.mac:
        print("MAC address missing. Set MAC_ADDRESS in config.env or pass --mac.", file=sys.stderr)
        return 2

    try:
        send_magic_packet(args.mac, args.broadcast, args.port, args.count)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"Failed to send magic packet: {exc}", file=sys.stderr)
        return 1

    print(
        f"Sent {max(1, args.count)} Wake-on-LAN packet(s) to {args.mac} "
        f"via {args.broadcast}:{args.port}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
