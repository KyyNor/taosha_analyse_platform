"""The gateway must successfully query Quack for the container to be healthy."""
import json
import os
import urllib.request

port = os.environ.get("GATEWAY_PORT", "9495")
with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
    health = json.load(response)
if health.get("upstream") != "ok":
    raise SystemExit(1)
