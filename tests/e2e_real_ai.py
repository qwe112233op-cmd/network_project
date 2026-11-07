"""Real-AI end-to-end test for the finished server + client.

Starts ImageDescriptionServer.py with the REAL AI backend, runs
ImageDescriptionClient.py with scripted input, uploads the three provided
test images, describes each one, downloads one image back and compares
the saved bytes, removes an image and quits.

Checks:
  * upload replies OK 0000/0001/0002
  * LIST initially shows DESCRIPTION: no for all three
  * each DESCRIBE returns a non-empty caption (not the mock string)
  * LIST after describing shows DESCRIPTION: yes
  * DOWNLOAD restores byte-identical content
  * REMOVE 0001 removes only that image
  * QUIT replies OK and the client exits 0

Exit code 0 = PASS.  Takes roughly 1-3 minutes on CPU.
"""

import argparse
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

DEFAULT_SERVER = Path(
    r"C:\Users\qwe11\Downloads\image-description-assignment"
    r"\image-description-assignment\ImageDescriptionServer.py"
)
DEFAULT_CLIENT = Path(__file__).resolve().parent.parent / "ImageDescriptionClient_STUDENT_IDS.py"


def wait_ready(proc, timeout=300):
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


def get_activity(text):
    """Split transcript into activity items: ('client', line) / ('server', line)."""
    activity = []
    for line in text.splitlines():
        if line.startswith("client: "):
            activity.append(("client", line[len("client: "):]))
        elif line.startswith("server: "):
            activity.append(("server", line[len("server: "):]))
        elif line.strip():
            activity.append(("other", line))
    return activity


def take_until_client(activity, start):
    """Return (server_lines, next_index) collecting server lines after start."""
    collected = []
    index = start
    while index < len(activity) and activity[index][0] == "server":
        collected.append(activity[index][1])
        index += 1
    return collected, index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", type=Path, default=DEFAULT_SERVER)
    parser.add_argument("--client", type=Path, default=DEFAULT_CLIENT)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--images", type=Path, default=DEFAULT_SERVER.parent / "test_images")
    args = parser.parse_args()

    workdir = Path(__file__).resolve().parent / "_e2e_real_work"
    shutil.rmtree(workdir, ignore_errors=True)
    workdir.mkdir(parents=True)

    images = {}

    def add_image(name):
        source = args.images / name
        if not source.is_file():
            raise SystemExit("test image missing: " + str(source))
        shutil.copyfile(source, workdir / name)
        images[name] = (workdir / name).read_bytes()

    for name in ("cat.jpg", "flower.png", "fruit_bowl.jpg"):
        add_image(name)

    script = (
        "UPLOAD\ncat.jpg\n"
        "UPLOAD\nflower.png\n"
        "UPLOAD\nfruit_bowl.jpg\n"
        "LIST\n"
        "DESCRIBE\n0000\n"
        "DESCRIBE\n0001\n"
        "DESCRIBE\n0002\n"
        "LIST\n"
        "DOWNLOAD\n0002\nfruit_bowl_copy.jpg\n"
        "REMOVE\n0001\n"
        "LIST\n"
        "QUIT\n"
    )

    server_proc = subprocess.Popen(
        [args.python, str(args.server), "--host", "127.0.0.1", "--port", "0"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, cwd=str(args.server.parent),
        encoding="utf-8", errors="replace",
    )
    failures = []
    try:
        port = wait_ready(server_proc)
        print("real-AI server ready on 127.0.0.1:%d" % port)

        result = subprocess.run(
            [args.python, str(args.client), "127.0.0.1", str(port)],
            input=script, text=True, capture_output=True,
            cwd=str(workdir), timeout=600,
            encoding="utf-8", errors="replace",
        )
        print(result.stdout)
        if result.returncode != 0:
            failures.append("client exit code %d" % result.returncode)
            if result.stderr.strip():
                failures.append("client stderr: " + result.stderr.strip())

        activity = get_activity(result.stdout)
        index = 0
        uploaded = ["cat.jpg", "flower.png", "fruit_bowl.jpg"]
        for number, name in enumerate(uploaded):
            while index < len(activity) and activity[index] != ("client", "UPLOAD"):
                index += 1
            if index >= len(activity):
                failures.append("UPLOAD missing for " + name)
                break
            index += 1
            if index >= len(activity) or activity[index] != ("client", name):
                failures.append("path prompt missing for " + name)
                break
            index += 1
            if index >= len(activity):
                failures.append("upload reply missing for " + name)
                break
            reply = activity[index][1]
            expected = "OK %04d" % number
            if reply != expected:
                failures.append("upload reply %r != %r" % (reply, expected))

        def server_lines_after(client_line, expected_client_lines):
            nonlocal index
            while index < len(activity) and activity[index] != ("client", client_line):
                index += 1
            if index >= len(activity):
                return None
            index += 1
            for expected in expected_client_lines:
                if index >= len(activity) or activity[index] != ("client", expected):
                    return None
                index += 1
            lines, index = take_until_client(activity, index)
            return lines

        listing = server_lines_after("LIST", [])
        if listing is None:
            failures.append("first LIST not found")
        else:
            if len(listing) != 4:
                failures.append("first LIST has %d lines, expected 4" % len(listing))
            if listing[0] != "OK":
                failures.append("first LIST missing OK")
            for line in listing[1:]:
                if "DESCRIPTION: no" not in line:
                    failures.append("first LIST should say no: %r" % line)

        captions = {}
        for image_id in ("0000", "0001", "0002"):
            lines = server_lines_after("DESCRIBE", [image_id])
            if lines is None:
                failures.append("DESCRIBE %s not found" % image_id)
                continue
            if not lines or lines[0] != "OK":
                failures.append("DESCRIBE %s didn't answer OK: %r" % (image_id, lines[:1]))
                continue
            caption = " ".join(lines[1:]).strip()
            captions[image_id] = caption
            if not caption or caption.startswith("ERROR"):
                failures.append("DESCRIBE %s returned no caption" % image_id)
            elif caption.startswith("Mock description"):
                failures.append("DESCRIBE %s still uses the mock backend" % image_id)
            elif not re.search(r"[A-Za-z]{3}", caption):
                failures.append("DESCRIBE %s caption is not English: %r" % (image_id, caption))

        listing = server_lines_after("LIST", [])
        if listing is None:
            failures.append("second LIST not found")
        else:
            joined = "\n".join(listing[1:])
            for image_id in ("0000", "0001", "0002"):
                if ("IMAGE ID: %s " % image_id) not in joined or "DESCRIPTION: yes" not in joined:
                    failures.append("second LIST missing described " + image_id)

        lines = server_lines_after("DOWNLOAD", ["0002", "fruit_bowl_copy.jpg"])
        if lines is None:
            failures.append("DOWNLOAD not found")
        else:
            if not lines or lines[0] != "OK fruit_bowl.jpg":
                failures.append("DOWNLOAD reply %r" % lines[:1])
        saved = workdir / "fruit_bowl_copy.jpg"
        if not saved.is_file():
            failures.append("downloaded file missing")
        elif saved.read_bytes() != images["fruit_bowl.jpg"]:
            failures.append("downloaded bytes differ from fruit_bowl.jpg")

        lines = server_lines_after("REMOVE", ["0001"])
        if lines is None or lines[:1] != ["OK"]:
            failures.append("REMOVE 0001 did not reply OK")

        listing = server_lines_after("LIST", [])
        if listing is None:
            failures.append("final LIST not found")
        else:
            joined = "\n".join(listing[1:])
            if "IMAGE ID: 0001 " in joined:
                failures.append("removed image 0001 still listed")
            for image_id in ("0000", "0002"):
                if ("IMAGE ID: %s " % image_id) not in joined:
                    failures.append("image %s missing after REMOVE" % image_id)

        while index < len(activity) and activity[index] != ("client", "QUIT"):
            index += 1
        if index >= len(activity):
            failures.append("QUIT not found")
        else:
            index += 1
            if index >= len(activity) or activity[index] != ("server", "OK"):
                failures.append("QUIT did not reply OK")

        print("captions:")
        for image_id, caption in captions.items():
            print("  %s -> %s" % (image_id, caption))
    finally:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        shutil.rmtree(workdir, ignore_errors=True)

    if failures:
        print("\nFAIL: %d problem(s)" % len(failures))
        for failure in failures:
            print(" - " + failure)
        return 1
    print("PASS: real-AI end-to-end run verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
