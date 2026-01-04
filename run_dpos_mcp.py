import io
import os
import sys
from pathlib import Path

# Force project root onto sys.path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# MCP uses stdio. Keep stdout clean for JSON-RPC messages.
os.environ.setdefault("DPOS_LOG_STREAM", "stderr")


class _MCPStdoutRouter(io.TextIOBase):
	"""Route non-protocol stdout output to stderr.

	Claude Desktop (and other MCP clients) treat every line on stdout as a protocol
	message. Some parts of the codebase still use print() which would corrupt the
	protocol stream and cause client-side parse/validation errors.

	This router forwards JSON-RPC lines to real stdout and sends everything else to
	stderr.
	"""

	def __init__(self, real_stdout, real_stderr):
		self._out = real_stdout
		self._err = real_stderr
		self._buf = ""

	def writable(self):
		return True

	def write(self, s):
		if not s:
			return 0
		self._buf += s

		written = 0
		while "\n" in self._buf:
			line, self._buf = self._buf.split("\n", 1)
			written += len(line) + 1

			stripped = line.lstrip()
			# Heuristic: JSON-RPC messages always include a top-level jsonrpc field.
			if stripped.startswith('{') and '"jsonrpc"' in stripped:
				self._out.write(line + "\n")
				self._out.flush()
			else:
				self._err.write(line + "\n")
				self._err.flush()

		return written

	def flush(self):
		# Flush any partial buffer as non-protocol output.
		if self._buf:
			self._err.write(self._buf)
			self._err.flush()
			self._buf = ""
		self._out.flush()

	def isatty(self):
		return False


# Install stdout router only for MCP runs.
sys.stdout = _MCPStdoutRouter(sys.stdout, sys.stderr)

from dpos_mcp.server import run_stdio_server

run_stdio_server()
