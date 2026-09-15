"""Live lightning-strike logger. Standalone app — no dependency on
anything outside this directory (run it even with the rest of the FBS
repo deleted).

Connects to blitzortung.org's public websocket feed — the same feed
lightningmaps.org's own live map uses (lightningmaps.org has no separate
API; it's a frontend over this exact socket, confirmed by reading its
production JS at blitzortung.org/en/JS/live_lightning_maps.js and
JS/lbr.js). Only this one process talks to the socket directly; every
strike gets appended to a local SQLite DB, and other apps read from that
DB — never from the live socket itself. This matches blitzortung's
stated third-party policy: apps must run their own server as an
intermediary rather than have every client hit their servers.

Protocol (reverse-engineered from their own client, not officially
documented): connect to wss://<server>, send '{"a":111}' to subscribe,
then every incoming message is an LZW-compressed JSON string. Decoded
JSON is either one strike object (time: ns since epoch, lat, lon, plus
optional latc/lonc corrections to add on) or a {"timeout": ...} keepalive.
"""

import argparse
import asyncio
import json
import time

import websockets

from db import DB_PATH, insert_flashes, open_db
from models import Flash

WS_SERVERS = ["ws1.blitzortung.org", "ws2.blitzortung.org", "ws7.blitzortung.org", "ws8.blitzortung.org"]
SUBSCRIBE_MSG = '{"a":111}'


def lzw_decode(data):
    """Python port of blitzortung's own decode() (JS/lbr.js) — a classic
    LZW variant where dictionary codes are embedded as characters with
    codepoint >= 256 (raw bytes are codepoints < 256, passed through)."""
    if not data:
        return ""

    dictionary = {}
    prev_entry = data[0]
    first_char = data[0]
    result = [data[0]]
    next_code = 256

    for ch in data[1:]:
        code = ord(ch)
        entry = ch if code < 256 else dictionary.get(code, prev_entry + first_char)
        result.append(entry)
        first_char = entry[0]
        dictionary[next_code] = prev_entry + first_char
        next_code += 1
        prev_entry = entry

    return "".join(result)


async def listen(conn, server, batch_size=20, flush_interval_s=5.0):
    uri = f"wss://{server}"
    buffer = []
    last_flush = time.monotonic()
    total = 0

    async with websockets.connect(uri, open_timeout=10) as ws:
        await ws.send(SUBSCRIBE_MSG)
        print(f"connected to {uri}, listening...")

        async for message in ws:
            try:
                strike = json.loads(lzw_decode(message))
            except (ValueError, TypeError):
                continue

            if not all(key in strike for key in ("time", "lat", "lon")):
                continue  # timeout/keepalive message, not a strike

            lat = strike["lat"] + strike.get("latc", 0.0)
            lon = strike["lon"] + strike.get("lonc", 0.0)
            buffer.append(Flash(lat, lon, strike["time"] / 1e9))  # ns -> s

            now = time.monotonic()
            if len(buffer) >= batch_size or now - last_flush >= flush_interval_s:
                insert_flashes(conn, buffer)
                total += len(buffer)
                print(f"logged {len(buffer)} strikes ({total} this run)")
                buffer.clear()
                last_flush = now


async def run(db_path, servers):
    conn = open_db(db_path)
    server_idx = 0
    while True:
        server = servers[server_idx % len(servers)]
        try:
            await listen(conn, server)
        except (OSError, asyncio.TimeoutError, websockets.exceptions.WebSocketException) as exc:
            print(f"connection to {server} lost ({exc}); retrying in 5s...")
            server_idx += 1
            await asyncio.sleep(5)


def main():
    parser = argparse.ArgumentParser(description="Log live lightning strikes into a local DB.")
    parser.add_argument("--db", default=str(DB_PATH), help="SQLite path (default: live_flashes.db)")
    args = parser.parse_args()

    try:
        asyncio.run(run(args.db, WS_SERVERS))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
