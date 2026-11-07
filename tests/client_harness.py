"""Automated conformance test for the Task 2 client.

How it works
------------
1. Starts ImageDescriptionServer.py with --backend mock on a free port
   (the five Part-1 functions must already be implemented).
2. Runs ImageDescriptionClient.py with a scripted stdin covering all six
   commands, local file errors, invalid IDs, non-overwriting download and
   the "No images" list.
3. Compares the client transcript line by line with the expected Section 3.1
   style output, checks the downloaded file bytes, checks that an existing
   target file was not overwritten and that no stray files were created.
4. Runs the client against a closed port and expects exit code 2.

Requirements: an interpreter that has pillow installed (any backend of the
assignment works; mock mode still decodes images).  Usage:

    python client_harness.py
    python client_harness.py --server "C:\\...\\ImageDescriptionServer.py" \
                             --client "C:\\...\\ImageDescriptionClient.py"

Exit code 0 means every check passed.
"""

import argparse
import queue
import re
import shutil
import socket
import struct
import subprocess
import sys
import threading
import time
import zlib
from pathlib import Path

DEFAULT_SERVER = Path(
    r"C:\Users\qwe11\Downloads\image-description-assignment"
    r"\image-description-assignment\ImageDescriptionServer.py"
)
DEFAULT_CLIENT = Path(__file__).resolve().parent.parent / "ImageDescriptionClient_STUDENT_IDS.py"


def make_png():
    """Return a valid 1x1 red RGB PNG using only the standard library."""

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    signature = b"\x89PNG\r\n\x1a\n"
    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    pixels = zlib.compress(b"\x00\xff\x00\x00")  # filter 0 + red
    return signature + chunk(b"IHDR", header) + chunk(b"IDAT", pixels) + chunk(b"IEND", b"")


def wait_ready(proc, timeout=60):
    """Read the server's stdout until READY appears; return the TCP port."""
    lines = queue.Queue()

    def reader():
        for line in proc.stdout:
            lines.put(line)
        lines.put(None)

    threading.Thread(target=reader, daemon=True).start()
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            line = lines.get(timeout=0.2)
        except queue.Empty:
            continue
        if line is None:
            break
        match = re.match(r"READY host=.* port=(\d+)$", line.strip())
        if match:
            return int(match.group(1))
    raise RuntimeError("server never printed READY")


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def run_client(python, client, port, script, cwd):
    return subprocess.run(
        [python, str(client), "127.0.0.1", str(port)],
        input=script, text=True, capture_output=True,
        cwd=str(cwd), timeout=180,
        encoding="utf-8", errors="replace",
    )


def expected_lines():
    """Expected transcript for the mock-backend script (regexes)."""
    hour = r"TIME: \d{2}:\d{2}:\d{2}"
    lines = [
        r"client: UNKNOWN",
        r"server: ERROR - Command not understood",

        r"client: LIST",
        r"server: OK",
        r"server: No images",

        r"client: UPLOAD",
        r"client: missing\.jpg",
        r"client: ERROR - File not found",

        r"client: UPLOAD",
        r"client: invalid\.jpg",
        r"server: ERROR - Invalid image",

        r"client: UPLOAD",
        r"client: valid\.png",
        r"server: OK 0000",

        r"client: LIST",
        r"server: OK",
        r"server: IMAGE ID: 0000 \| FILE: valid\.png \| %s \| DESCRIPTION: no" % hour,

        r"client: DESCRIBE",
        r"client: 9999",
        r"server: ERROR - Invalid ID",

        r"client: DESCRIBE",
        r"client: 0000",
        r"server: OK",
        r"server: Mock description: the image was received and decoded successfully\.",

        r"client: LIST",
        r"server: OK",
        r"server: IMAGE ID: 0000 \| FILE: valid\.png \| %s \| DESCRIPTION: yes" % hour,

        r"client: DOWNLOAD",
        r"client: 9999",
        r"client: out_missing\.png",
        r"server: ERROR - Invalid ID",

        r"client: DOWNLOAD",
        r"client: 0000",
        r"client: out\.png",
        r"server: OK valid\.png",
        r"client: Saved to out\.png",

        r"client: DOWNLOAD",
        r"client: 0000",
        r"client: existing\.png",
        r"server: OK valid\.png",
        r"client: ERROR - Choose a new file in an existing directory",

        r"client: DOWNLOAD",
        r"client: 0000",
        r"client: nodir/out\.png",
        r"server: OK valid\.png",
        r"client: ERROR - Choose a new file in an existing directory",

        r"client: REMOVE",
        r"client: 9999",
        r"server: ERROR - Invalid ID",

        r"client: REMOVE",
        r"client: 0000",
        r"server: OK",

        r"client: LIST",
        r"server: OK",
        r"server: No images",

        r"client: QUIT",
        r"server: OK",
    ]
    return lines


CLIENT_SCRIPT = (
    "UNKNOWN\n"
    "LIST\n"
    "UPLOAD\nmissing.jpg\n"
    "UPLOAD\ninvalid.jpg\n"
    "UPLOAD\nvalid.png\n"
    "LIST\n"
    "DESCRIBE\n9999\n"
    "DESCRIBE\n0000\n"
    "LIST\n"
    "DOWNLOAD\n9999\nout_missing.png\n"
    "DOWNLOAD\n0000\nout.png\n"
    "DOWNLOAD\n0000\nexisting.png\n"
    "DOWNLOAD\n0000\nnodir/out.png\n"
    "REMOVE\n9999\n"
    "REMOVE\n0000\n"
    "LIST\n"
    "QUIT\n"
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", type=Path, default=DEFAULT_SERVER)
    parser.add_argument("--client", type=Path, default=DEFAULT_CLIENT)
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()

    for path in (args.server, args.client):
        if not path.is_file():
            raise SystemExit(f"file not found: {path}")

    workdir = Path(__file__).resolve().parent / "_harness_work"
    shutil.rmtree(workdir, ignore_errors=True)
    workdir.mkdir(parents=True)
    try:
        (workdir / "valid.png").write_bytes(make_png())
        (workdir / "invalid.jpg").write_text("this is not an image", encoding="utf-8")
        (workdir / "existing.png").write_bytes(b"ORIGINAL CONTENT")

        server_proc = subprocess.Popen(
            [args.python, str(args.server), "--backend", "mock",
             "--host", "127.0.0.1", "--port", "0"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, cwd=str(args.server.parent),
            encoding="utf-8", errors="replace",
        )
        try:
            port = wait_ready(server_proc)
            print(f"server ready on 127.0.0.1:{port}")

            result = run_client(args.python, args.client, port, CLIENT_SCRIPT, workdir)

            failures = []
            expected = expected_lines()
            actual = result.stdout.splitlines()

            for index, pattern in enumerate(expected):
                if index >= len(actual):
                    failures.append(f"missing line {index + 1}: expected /{pattern}/")
                    break
                if not re.fullmatch(pattern, actual[index]):
                    failures.append(
                        f"line {index + 1}: expected /{pattern}/\n"
                        f"             got   {actual[index]!r}"
                    )
            if len(actual) != len(expected):
                failures.append(
                    f"transcript has {len(actual)} lines, expected {len(expected)}"
                )
            if result.returncode != 0:
                failures.append(f"client exit code {result.returncode}, expected 0")
                if result.stderr.strip():
                    failures.append("client stderr: " + result.stderr.strip())

            saved = workdir / "out.png"
            if not saved.is_file():
                failures.append("out.png was not created")
            elif saved.read_bytes() != (workdir / "valid.png").read_bytes():
                failures.append("out.png bytes differ from valid.png")
            if (workdir / "existing.png").read_bytes() != b"ORIGINAL CONTENT":
                failures.append("existing.png was overwritten")
            if (workdir / "nodir").exists():
                failures.append("nodir/ was created unexpectedly")
            if (workdir / "out_missing.png").exists():
                failures.append("out_missing.png was created unexpectedly")

            # Connection-refused behaviour: exit code 2 and an error message.
            refused = run_client(args.python, args.client, free_port(),
                                 "LIST\n", workdir)
            if refused.returncode != 2:
                failures.append(
                    f"connection-refused exit code {refused.returncode}, expected 2"
                )
            if "ERROR" not in (refused.stdout + refused.stderr):
                failures.append("connection-refused produced no ERROR message")
        finally:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server_proc.kill()

        if failures:
            print("\nFAIL: %d problem(s)" % len(failures))
            for failure in failures:
                print(" - " + failure)
            if "result" in locals() and result.stdout:
                print("\n--- client transcript ---")
                print(result.stdout)
            return 1
        print("PASS: client transcript, downloads and error handling verified")
        return 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
