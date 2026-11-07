# Online Image Description System

CS3201 2026 Programming Assignment — client/server image store with an on-device
vision-language model (SmolVLM-256M-Instruct) that captions uploaded images.

The system uses **one persistent IPv4 TCP connection** between the client and the
server on port **18333**. Every message on the wire is prefixed with a 10-byte
ASCII decimal length header, so payloads are reconstructed exactly; nothing
depends on newline framing.

- **Task 1 — server:** the five socket primitives (`create_listener`,
  `accept_client`, `receive_message`, `send_message`, `close_client`) inside
  `ImageDescriptionServer.py`. Storage, command handling and AI inference were
  provided and are left unchanged.
- **Task 2 — client:** a console program with six commands (`UPLOAD`, `LIST`,
  `DESCRIBE`, `DOWNLOAD`, `REMOVE`, `QUIT`) written with the Python standard
  library only.

## Repository layout

| Path | Purpose |
| --- | --- |
| `ImageDescriptionServer_<student_IDs>.py` | Task 1 deliverable (five socket functions completed) |
| `ImageDescriptionClient_<student_IDs>.py` | Task 2 deliverable (standard library client) |
| `tests/check_sockets.py` | 40 automated checks for the five functions and the command flow |
| `tests/client_harness.py` | Client conformance run against a mock server (17-step session, byte checks, exit codes) |
| `tests/e2e_real_ai.py` | End-to-end run with the real model: three uploads, captions, download, remove |
| `screenshots/` | Figures 1–4 used in the report |
| `Report_STUDENT_IDS.pdf` | Assignment report (also `.docx` and `build_report.py`) |
| `README.md` | This document |

The submitted server file must run **inside the extracted assignment folder**, next
to `models/smolvlm-256m`, because the model path is relative. Copy it there
before starting the server:

```powershell
Copy-Item .\ImageDescriptionServer_<student_IDs>.py "C:\Users\<you>\Downloads\image-description-assignment\image-description-assignment\"
```

## Requirements

- Windows 10/11, or macOS/Linux with the provided `setup_env.sh`
- Internet access for the first setup (downloads Python 3.11.15, the virtual
  environment and the pinned CPU wheels)
- The provided assignment archive: `image-description-assignment.zip`
  (server template, setup scripts, `requirements.lock.txt`, `test_images/` and
  `models/smolvlm-256m`)

## Setup

1. Extract `image-description-assignment.zip` and keep the folder in place.

2. Open PowerShell (Windows) or a terminal (macOS/Linux) in that folder and run
   the provided setup script. It installs a managed CPython 3.11.15 with `uv`
   into `.runtime`, creates `.venv`, and installs the pinned CPU dependencies
   (`torch 2.2.2+cpu`, `transformers 4.49.0`, `Pillow 10.4.0`, …).

   ```powershell
   cd "C:\Users\<you>\Downloads\image-description-assignment\image-description-assignment"

   Move-Item .tools\uv.exe  .tools\uv\uv.exe  -Force
   Move-Item .tools\uvx.exe .tools\uv\uvx.exe -Force
   Move-Item .tools\uvw.exe .tools\uv\uvw.exe -Force

   .\setup_env.bat
   ```

   The three `Move-Item` lines put the `uv` executables where `setup_env.bat`
   expects them (`.tools\uv\`). If they already live there, PowerShell prints
   `Cannot find path …` for each line — that is harmless, continue with the
   script. macOS/Linux:

   ```bash
   cd ~/Downloads/image-description-assignment
   bash setup_env.sh
   ```

   Wait for `Setup complete.`

3. Verify the AI component before running the network tests:

   ```powershell
   .\.venv\Scripts\python.exe ImageDescriptionServer.py --check-ai .\test_images\cat.jpg
   ```

   Expected output (text may vary slightly):

   ```
   In this image we can see a cat lying on the floor.
   ```

## Running the system

Two terminals, both opened in the assignment folder.

**Terminal 1 — server** (real AI model):

```powershell
.\.venv\Scripts\python.exe ImageDescriptionServer_<student_IDs>.py
```

For fast protocol debugging without loading the model, start it in mock mode:

```powershell
.\.venv\Scripts\python.exe ImageDescriptionServer_<student_IDs>.py --backend mock
```

When the server is ready it prints:

```
READY host=0.0.0.0 port=18333
```

**Terminal 2 — client** (same computer; use the server's IPv4 address for another
computer):

```powershell
.\.venv\Scripts\python.exe ImageDescriptionClient_<student_IDs>.py 127.0.0.1 18333
```

The client prints a `client: ` prompt for every input and prefixes every server
reply line with `server: `.

## Client commands

| Command | Follow-up input | Result |
| --- | --- | --- |
| `UPLOAD` | local JPEG/PNG path | uploads the file and shows its image ID |
| `LIST` | — | IDs, file names, upload times and description status |
| `DESCRIBE` | image ID | the English caption (generated on first use, then cached) |
| `DOWNLOAD` | image ID, output path | saves the original bytes (never overwrites an existing file) and prints `Saved to <path>` |
| `REMOVE` | image ID | deletes the image and its cached caption |
| `QUIT` | — | prints `OK`, closes the connection and exits |

Example session:

```
client: UPLOAD
client: .\test_images\cat.jpg
server: OK 0000
client: LIST
server: OK
server: IMAGE ID: 0000 | FILE: cat.jpg | TIME: 00:07:39 | DESCRIPTION: no
client: DESCRIBE
client: 0000
server: OK
server: In this image we can see a cat lying on the floor.
client: DOWNLOAD
client: 0000
client: cat_download.jpg
server: OK cat.jpg
client: Saved to cat_download.jpg
client: REMOVE
client: 0000
server: OK
client: QUIT
server: OK
```

Rules enforced by the server: JPEG/PNG only, at most 5 MiB and 20 megapixels per
image, at most 20 images and 50 MiB in total. IDs start at `0000` and are not
reused. Errors keep the same connection open; only `QUIT` closes it.

## Tests

Run from the assignment folder (the server path is the file next to
`models/`):

```powershell
# 1) five socket functions + command flow — expect: 40/40 checks passed
.\.venv\Scripts\python.exe "C:\Users\<you>\image-description-final\tests\check_sockets.py" ".\ImageDescriptionServer_<student_IDs>.py"

# 2) client conformance against the mock server — expect: PASS line
.\.venv\Scripts\python.exe "C:\Users\<you>\image-description-final\tests\client_harness.py" --server ".\ImageDescriptionServer_<student_IDs>.py"

# 3) real-model end-to-end (1–3 minutes) — expect: PASS and three captions
.\.venv\Scripts\python.exe "C:\Users\<you>\image-description-final\tests\e2e_real_ai.py" --server ".\ImageDescriptionServer_<student_IDs>.py"
```

`client_harness.py` and `e2e_real_ai.py` locate the client automatically
(`..\ImageDescriptionClient_<student_IDs>.py`); pass `--client` if you rename it
differently.

Expected results on our machine:

- `check_sockets.py` → `40/40 checks passed`, exit code 0
- `client_harness.py` → `PASS: client transcript, downloads and error handling verified`, exit code 0
- `e2e_real_ai.py` → `PASS`, exit code 0, with captions such as
  “In this image we can see two pink roses and two buds.”

## Report

`Report_STUDENT_IDS.pdf` documents both tasks, the protocol, the runtime
environment, the run commands and the verification runs. It is generated from
`screenshots/` with `build_report.py`:

```powershell
# any Python 3 with python-docx; then export the DOCX to PDF in Word/LibreOffice
python .\build_report.py .\Report_STUDENT_IDS.docx
```

## Submission

- Names: `ImageDescriptionServer_<student_IDs>.py`,
  `ImageDescriptionClient_<student_IDs>.py`, `Report_<student_IDs>.pdf`
  (all member IDs joined with underscores, e.g. `51234567_57654321`).
- Submit only these three files — **not** `models/`, `.venv`, `.tools`,
  `.runtime`, `setup.log` or any executable.
- Group registration: Canvas → People → Groups → join one empty group from
  Project Group 001–200; every member joins the same group.
- Deadline: **11 November 2026, 23:59 HKT**.

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `The term '.\venv\Scripts\python.exe' is not recognized` | Wrong working folder or missing leading dot. Run `.\`**.venv**`\Scripts\python.exe` from the assignment folder. |
| `WinError 10048` / port in use | Stop the previous server, or start with `--port 18334` and connect to that port. |
| `TODO` message on startup | A Part 1 function is still unimplemented. |
| `ERROR - Invalid image` | The uploaded file is not a valid JPEG/PNG, or exceeds 5 MiB / 20 Mpx. |
| Slow first `DESCRIBE` | CPU inference with SmolVLM-256M; later calls are served from the caption cache. |
