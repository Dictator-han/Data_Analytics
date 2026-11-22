#!/usr/bin/env python3
"""Tiny HTTP API + one-button page to wake the Mac mini from a Synology NAS."""

from __future__ import annotations

import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from wake import load_dotenv, send_magic_packet

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / "config.env")

HOST = os.environ.get("HTTP_HOST", "0.0.0.0")
PORT = int(os.environ.get("HTTP_PORT", "8787"))
TOKEN = os.environ.get("WAKE_TOKEN", "").strip()
MAC_ADDRESS = os.environ.get("MAC_ADDRESS", "").strip()
BROADCAST = os.environ.get("BROADCAST_ADDRESS", "255.255.255.255").strip()
WOL_PORT = int(os.environ.get("WOL_PORT", "9"))
PACKET_COUNT = int(os.environ.get("PACKET_COUNT", "3"))
DEVICE_NAME = os.environ.get("DEVICE_NAME", "Mac mini")


INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>唤醒 {device}</title>
  <style>
    :root {{
      --bg: #0f1419;
      --panel: #1a222c;
      --text: #e8eef5;
      --muted: #8b9aab;
      --accent: #3d9cfd;
      --ok: #3ecf8e;
      --bad: #ff6b6b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      font-family: "SF Pro Text", "PingFang SC", "Noto Sans SC", sans-serif;
      color: var(--text);
      background:
        radial-gradient(ellipse at 20% 10%, #1c3a5a 0%, transparent 45%),
        radial-gradient(ellipse at 80% 90%, #143028 0%, transparent 40%),
        var(--bg);
    }}
    main {{
      width: min(420px, 92vw);
      padding: 2rem;
      border-radius: 1.25rem;
      background: color-mix(in srgb, var(--panel) 88%, transparent);
      border: 1px solid rgba(255,255,255,0.08);
      backdrop-filter: blur(12px);
      text-align: center;
    }}
    h1 {{ margin: 0 0 0.4rem; font-size: 1.5rem; font-weight: 650; }}
    p {{ margin: 0 0 1.5rem; color: var(--muted); line-height: 1.5; }}
    label {{
      display: block;
      text-align: left;
      font-size: 0.85rem;
      color: var(--muted);
      margin-bottom: 0.35rem;
    }}
    input {{
      width: 100%;
      margin-bottom: 1rem;
      padding: 0.75rem 0.9rem;
      border-radius: 0.7rem;
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(0,0,0,0.25);
      color: var(--text);
      font-size: 1rem;
    }}
    button {{
      width: 100%;
      border: 0;
      border-radius: 999px;
      padding: 0.95rem 1.2rem;
      font-size: 1.05rem;
      font-weight: 650;
      color: #041018;
      background: linear-gradient(135deg, #6cbcff, var(--accent));
      cursor: pointer;
    }}
    button:disabled {{ opacity: 0.6; cursor: wait; }}
    #status {{
      min-height: 1.4rem;
      margin-top: 1rem;
      font-size: 0.95rem;
      color: var(--muted);
    }}
    #status.ok {{ color: var(--ok); }}
    #status.bad {{ color: var(--bad); }}
  </style>
</head>
<body>
  <main>
    <h1>唤醒 {device}</h1>
    <p>通过家里的群晖发送 Wake-on-LAN 魔法包。</p>
    <label for="token">访问令牌</label>
    <input id="token" type="password" autocomplete="current-password" placeholder="WAKE_TOKEN" />
    <button id="wake" type="button">立即唤醒</button>
    <div id="status"></div>
  </main>
  <script>
    const statusEl = document.getElementById("status");
    const tokenEl = document.getElementById("token");
    const button = document.getElementById("wake");
    const saved = localStorage.getItem("wake_token");
    if (saved) tokenEl.value = saved;

    async function wake() {{
      const token = tokenEl.value.trim();
      if (!token) {{
        statusEl.className = "bad";
        statusEl.textContent = "请先填写访问令牌";
        return;
      }}
      localStorage.setItem("wake_token", token);
      button.disabled = true;
      statusEl.className = "";
      statusEl.textContent = "正在发送唤醒包…";
      try {{
        const res = await fetch("/wake", {{
          method: "POST",
          headers: {{
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json"
          }},
          body: "{{}}"
        }});
        const data = await res.json().catch(() => ({{}}));
        if (!res.ok) throw new Error(data.error || ("HTTP " + res.status));
        statusEl.className = "ok";
        statusEl.textContent = data.message || "已发送";
      }} catch (err) {{
        statusEl.className = "bad";
        statusEl.textContent = err.message || String(err);
      }} finally {{
        button.disabled = false;
      }}
    }}
    button.addEventListener("click", wake);
  </script>
</body>
</html>
""".format(device=DEVICE_NAME)


def require_token(handler: BaseHTTPRequestHandler) -> bool:
    if not TOKEN:
        handler.send_json(500, {"ok": False, "error": "Server WAKE_TOKEN is not configured"})
        return False

    auth = handler.headers.get("Authorization", "")
    token = ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    if not token:
        parsed = urlparse(handler.path)
        token = parse_qs(parsed.query).get("token", [""])[0]

    if not token or not secrets.compare_digest(token, TOKEN):
        handler.send_json(401, {"ok": False, "error": "Unauthorized"})
        return False
    return True


class WakeHandler(BaseHTTPRequestHandler):
    server_version = "MacMiniWake/1.0"

    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {self.address_string()} {fmt % args}")

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            body = INDEX_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/health":
            self.send_json(200, {"ok": True, "device": DEVICE_NAME})
            return
        if path == "/wake":
            self.do_POST()
            return
        self.send_json(404, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/wake":
            self.send_json(404, {"ok": False, "error": "Not found"})
            return
        if not require_token(self):
            return
        if not MAC_ADDRESS:
            self.send_json(500, {"ok": False, "error": "MAC_ADDRESS is not configured"})
            return
        try:
            send_magic_packet(MAC_ADDRESS, BROADCAST, WOL_PORT, PACKET_COUNT)
        except Exception as exc:  # noqa: BLE001 - surface to caller
            self.send_json(500, {"ok": False, "error": str(exc)})
            return
        self.send_json(
            200,
            {
                "ok": True,
                "message": f"已向 {DEVICE_NAME} ({MAC_ADDRESS}) 发送唤醒包",
                "broadcast": BROADCAST,
                "port": WOL_PORT,
                "count": PACKET_COUNT,
            },
        )


def main() -> None:
    if not MAC_ADDRESS:
        raise SystemExit("MAC_ADDRESS missing in config.env")
    if not TOKEN:
        raise SystemExit("WAKE_TOKEN missing in config.env — refuse to start unauthenticated")

    httpd = ThreadingHTTPServer((HOST, PORT), WakeHandler)
    print(f"Listening on http://{HOST}:{PORT}  device={DEVICE_NAME} mac={MAC_ADDRESS}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
