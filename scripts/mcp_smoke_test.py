#!/usr/bin/env python3
"""DPOS MCP stdio smoke test.

Starts the MCP server (stdio mode), sends a couple JSON-RPC requests, and
prints the responses.

This is useful to validate that:
- Python imports resolve from the chosen `cwd`
- The MCP server speaks JSON-RPC over stdio
- Tools are registered and listable

By default this does NOT call any DPOS tool (so it doesn't require Neo4j).
Use `--call dpos_search_products --args '{"query":"customer"}'` if you want
an end-to-end tool call (requires Neo4j + loaded sample data).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from queue import Queue, Empty
from typing import Any, Dict, Optional


def _reader_thread(stream, queue: Queue[str]) -> None:
    for line in iter(stream.readline, ""):
        queue.put(line)


def _read_json_line(queue: Queue[str], timeout_s: float) -> Dict[str, Any]:
    start = time.time()
    buf = ""

    while True:
        remaining = timeout_s - (time.time() - start)
        if remaining <= 0:
            raise TimeoutError(f"Timed out waiting for server response. Partial buffer: {buf!r}")

        try:
            line = queue.get(timeout=min(0.2, remaining))
        except Empty:
            continue

        buf += line
        line = line.strip()
        if not line:
            continue

        try:
            return json.loads(line)
        except json.JSONDecodeError:
            # If the server ever emits non-JSON lines on stdout (it shouldn't),
            # keep going and try the next line.
            continue


def _send(proc: subprocess.Popen[str], payload: Dict[str, Any]) -> None:
    assert proc.stdin is not None
    proc.stdin.write(json.dumps(payload) + "\n")
    proc.stdin.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test DPOS MCP stdio server")
    parser.add_argument(
        "--cwd",
        default=os.getcwd(),
        help="Working directory to run the server from (should be dpos-ecommerce root)",
    )
    parser.add_argument(
        "--python",
        dest="python_exe",
        default=sys.executable,
        help="Python executable to use (ideally your venv python)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Timeout (seconds) waiting for each server response",
    )
    parser.add_argument(
        "--call",
        default=None,
        help="Optional tool name to call (requires dependencies like Neo4j for most tools)",
    )
    parser.add_argument(
        "--args",
        default="{}",
        help="JSON object string for tool arguments (used with --call)",
    )

    args = parser.parse_args()

    # Start server: `-m src.mcp.server` runs the stdio server (see src/mcp/server.py).
    proc = subprocess.Popen(
        [args.python_exe, "-m", "src.mcp.server"],
        cwd=args.cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    assert proc.stdout is not None
    assert proc.stderr is not None

    out_q: Queue[str] = Queue()
    err_q: Queue[str] = Queue()
    threading.Thread(target=_reader_thread, args=(proc.stdout, out_q), daemon=True).start()
    threading.Thread(target=_reader_thread, args=(proc.stderr, err_q), daemon=True).start()

    try:
        _send(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        init_resp = _read_json_line(out_q, args.timeout)
        print("initialize =>")
        print(json.dumps(init_resp, indent=2))

        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools_resp = _read_json_line(out_q, args.timeout)
        print("\ntools/list =>")
        print(json.dumps(tools_resp, indent=2))

        if args.call:
            try:
                tool_args = json.loads(args.args)
                if not isinstance(tool_args, dict):
                    raise ValueError("--args must be a JSON object")
            except Exception as e:
                raise SystemExit(f"Invalid --args JSON: {e}")

            _send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": args.call, "arguments": tool_args},
                },
            )
            call_resp = _read_json_line(out_q, args.timeout)
            print(f"\ntools/call ({args.call}) =>")
            print(json.dumps(call_resp, indent=2))

        return 0
    finally:
        # Best-effort shutdown.
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

        # Surface any stderr (helpful if imports fail).
        err_lines = []
        while True:
            try:
                err_lines.append(err_q.get_nowait())
            except Empty:
                break
        if err_lines:
            sys.stderr.write("\n[server stderr]\n" + "".join(err_lines) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
