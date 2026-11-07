"""Build the assignment report DOCX (placeholders for members and screenshots)."""

import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HEADING_COLOUR = RGBColor(0x1F, 0x3A, 0x5F)


def add_table(doc, headers, rows, widths=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    header_cells = table.rows[0].cells
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    table.rows[0]._tr.get_or_add_trPr().append(repeat)
    for index, text in enumerate(headers):
        paragraph = header_cells[index].paragraphs[0]
        run = paragraph.add_run(text)
        run.bold = True
        run.font.size = Pt(9.5)
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), "DCE6F0")
        header_cells[index]._tc.get_or_add_tcPr().append(shading)
    for row in rows:
        cells = table.add_row().cells
        cant_split = OxmlElement("w:cantSplit")
        table.rows[-1]._tr.get_or_add_trPr().append(cant_split)
        for index, text in enumerate(row):
            run = cells[index].paragraphs[0].add_run(text)
            run.font.size = Pt(9.5)
    if widths:
        for column, width in zip(table.columns, widths):
            for cell in column.cells:
                cell.width = width
    return table


def add_code(doc, text):
    for line in text.splitlines():
        paragraph = doc.add_paragraph()
        fmt = paragraph.paragraph_format
        fmt.space_before = Pt(0)
        fmt.space_after = Pt(0)
        fmt.line_spacing = 1.0
        run = paragraph.add_run(line if line else " ")
        run.font.name = "Consolas"
        run.font.size = Pt(8.5)


def add_footer(doc, text):
    footer = doc.sections[0].footer
    paragraph = footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(text + "    Page ")
    run.font.size = Pt(8.5)
    field = OxmlElement("w:fldChar")
    field.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    page_run = paragraph.add_run()
    page_run.font.size = Pt(8.5)
    page_run._r.append(field)
    page_run._r.append(instr)
    page_run._r.append(end)


def heading(doc, text, level):
    paragraph = doc.add_heading(text, level=level)
    for run in paragraph.runs:
        run.font.color.rgb = HEADING_COLOUR
    return paragraph


def build(output):
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.3)
    section.right_margin = Cm(2.3)
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)

    add_footer(doc, "Online Image Description System - Assignment Report")

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Online Image Description System")
    run.bold = True
    run.font.size = Pt(26)
    run.font.color.rgb = HEADING_COLOUR

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run("Assignment Report")
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(0x44, 0x44, 0x44)

    doc.add_paragraph()
    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = info.add_run("Group project (Group 0XX)  |  November 2026")
    run.font.size = Pt(11)
    run.italic = True

    doc.add_paragraph()
    heading(doc, "Group members", 1)
    table = add_table(
        doc,
        ["Name", "Student ID", "Role"],
        [
            ["[Member 1 name]", "[Student ID]", "Server implementation, testing"],
            ["[Member 2 name]", "[Student ID]", "Client implementation, testing"],
            ["[Member 3 name]", "[Student ID]", "Report, integration testing"],
        ],
        widths=[Cm(6.0), Cm(4.0), Cm(6.5)],
    )

    heading(doc, "1. Introduction", 1)
    doc.add_paragraph(
        "This report documents our implementation of the online image description "
        "system. The system follows a client-server design over one persistent TCP "
        "connection. The server listens on port 18333 by default, stores uploaded "
        "JPEG/PNG images in memory (at most 20 images and 50 MiB), and generates a "
        "two-sentence caption for a stored image with the locally hosted "
        "SmolVLM-256M-Instruct vision-language model. Every message on the wire is "
        "prefixed with a ten-digit ASCII length header, so every payload can be "
        "reconstructed exactly and nothing depends on newline framing."
    )
    doc.add_paragraph(
        "Task 1 is the server: the five socket primitives (create_listener, "
        "accept_client, receive_message, send_message, close_client) and the "
        "already provided storage, AI and command handling around them. Task 2 is "
        "the client: a console program with six commands (UPLOAD, LIST, DESCRIBE, "
        "DOWNLOAD, REMOVE, QUIT) that keeps a single connection alive and displays "
        "every reply the server sends."
    )

    heading(doc, "2. Runtime environment", 1)
    doc.add_paragraph(
        "The system runs on CPU only. A setup script (setup_env.bat) prepares an "
        "isolated environment with the pinned dependency set; no system-wide "
        "installations are required."
    )
    add_table(
        doc,
        ["Component", "Detail"],
        [
            ["Operating system", "Windows 11 (25H2, build 26200), 64-bit"],
            ["Shell", "Windows PowerShell 5.1"],
            ["Python", "3.11.15 (uv-managed CPython, project-local .venv)"],
            ["PyTorch", "2.2.2+cpu (CPU wheel backend)"],
            ["Transformers", "4.49.0"],
            ["Pillow", "10.4.0"],
            ["Model", "SmolVLM-256M-Instruct, stored locally in models\\smolvlm-256m"],
            ["Environment setup", "setup_env.bat (uv 0.10.9, requirements.lock.txt)"],
        ],
        widths=[Cm(4.5), Cm(12.0)],
    )

    doc.add_paragraph(
        "No build step is required: both programs are Python sources executed "
        "with the project's .venv interpreter. The commands used to run the "
        "finished system are:"
    )
    add_code(
        doc,
        "cd image-description-assignment\n"
        ".\\setup_env.bat\n"
        ".\\.venv\\Scripts\\python.exe ImageDescriptionServer_<student_IDs>.py\n"
        "# second terminal (same folder):\n"
        ".\\.venv\\Scripts\\python.exe ImageDescriptionClient_<student_IDs>.py 127.0.0.1 18333",
    )

    heading(doc, "3. Task 1 - Server", 1)
    heading(doc, "3.1 The five socket functions", 2)
    add_table(
        doc,
        ["Function", "Behaviour implemented"],
        [
            [
                "create_listener\n(host, port)",
                "Creates an IPv4 (AF_INET) TCP (SOCK_STREAM) socket, enables "
                "SO_REUSEADDR, binds to (host, port), listens, and closes the "
                "socket again if any step raises OSError before re-raising.",
            ],
            [
                "accept_client\n(listener)",
                "Blocks until a client connects and returns the pair "
                "(conn, address) produced by listener.accept().",
            ],
            [
                "receive_message\n(conn)",
                "Reads exactly 10 header bytes; returns None when the peer closes "
                "the connection between messages. A header that is not 10 ASCII "
                "digits raises ValueError('Invalid length header'); a length "
                "outside 1..5,242,880 raises ValueError('Message size must be 1 "
                "byte to 5 MiB'). The payload is then read with a loop until the "
                "declared byte count is reached; if the connection closes first, "
                "ConnectionError is raised.",
            ],
            [
                "send_message\n(conn, payload)",
                "Accepts bytes, bytearray or memoryview only (TypeError otherwise) "
                "with a length of 1..5,242,880 bytes (ValueError otherwise). "
                "Sends the zero-padded 10-digit ASCII length header followed by "
                "the payload with sendall.",
            ],
            [
                "close_client\n(conn)",
                "Closes the connection socket (no exception on a second close).",
            ],
        ],
        widths=[Cm(4.2), Cm(12.0)],
    )

    heading(doc, "3.2 Protocol and storage rules", 2)
    doc.add_paragraph(
        "Messages are framed as a 10-character decimal length header (zero "
        "padded) followed by exactly that many bytes. A command message is at "
        "most 1024 bytes. File names must be at most 255 characters and must not "
        "contain a path separator, a control character, or be '.' or '..'. "
        "Accepted images are JPEG or PNG, at most 5 MiB, and at most 20 "
        "megapixels; the server stores at most 20 images and 50 MiB in total. "
        "Image identifiers are decimal strings (0000, 0001, ...) that are never "
        "reused within one run of the server."
    )
    add_table(
        doc,
        ["Command", "Server reply"],
        [
            ["UPLOAD <filename> + second message with image bytes", "OK <id>"],
            [
                "LIST",
                "OK, then one line per image: "
                "IMAGE ID: <id> | FILE: <name> | TIME: HH:MM:SS | "
                "DESCRIPTION: yes|no; or the single line No images",
            ],
            ["DESCRIBE <id>", "OK and a new line with the caption (cached after first use)"],
            ["DOWNLOAD <id>", "OK <filename>, then a second message with the image bytes"],
            ["REMOVE <id>", "OK"],
            ["QUIT", "OK, then the connection is closed"],
            [
                "invalid command, id, image, file name or full storage",
                "ERROR - Command not understood | ERROR - Invalid ID | "
                "ERROR - Invalid image | ERROR - Invalid filename | "
                "ERROR - Image storage is full",
            ],
        ],
        widths=[Cm(7.5), Cm(8.5)],
    )

    heading(doc, "3.3 Description backend", 2)
    doc.add_paragraph(
        "Uploaded images are decoded with Pillow, validated as JPEG/PNG below "
        "the megapixel limit, and normalised onto a white 512x512 canvas. "
        "DESCRIBE passes the image to SmolVLM-256M-Instruct with a fixed prompt "
        "asking for the main objects and the setting in two short sentences. The "
        "first description of an image is cached, so repeated DESCRIBE calls "
        "return the same text without running the model again; the LIST command "
        "reports DESCRIPTION: yes once a caption exists. The server can be "
        "started with --backend mock for protocol testing without loading the "
        "model, and with --check-ai <image> to verify the model installation on "
        "its own."
    )

    heading(doc, "4. Task 2 - Client", 1)
    doc.add_paragraph(
        "The client is a single-file Python program that uses only the standard "
        "library (socket, sys, os, pathlib). It opens one IPv4 TCP connection to "
        "the host and port given on the command line and keeps it open for the "
        "whole session. The input prompt is written as client: on its own line, "
        "and every line received from the server is printed with the server: "
        "prefix. Message framing mirrors the server: the client writes the "
        "zero-padded 10-digit header, then the payload, and reads replies with "
        "the same exact-length loop."
    )
    add_table(
        doc,
        ["Command", "Client behaviour"],
        [
            [
                "UPLOAD",
                "Prompts for an image path. The file must exist, be a regular "
                "file of 1 byte to 5 MiB, and be readable; otherwise the client "
                "answers locally with ERROR - File not found or ERROR - Image "
                "must be an existing file of 1 byte to 5 MiB without contacting "
                "the server. Only the base name is sent, followed by a second "
                "message containing the image bytes.",
            ],
            ["LIST", "Sends LIST and prints every reply line prefixed with server:"],
            ["DESCRIBE", "Prompts for an image id, sends DESCRIBE <id>, prints the caption"],
            [
                "DOWNLOAD",
                "Prompts for an image id and an output path. The client refuses "
                "an existing file or a missing parent directory with ERROR - "
                "Choose a new file in an existing directory. The file is created "
                "exclusively and the client prints Saved to <path> only after the "
                "complete image was written.",
            ],
            ["REMOVE", "Prompts for an image id, sends REMOVE <id>, prints OK"],
            ["QUIT", "Sends QUIT, prints the reply and closes the connection with exit code 0"],
            [
                "anything else",
                "Forwarded to the server unchanged so the user sees its ERROR "
                "reply; the connection stays open.",
            ],
        ],
        widths=[Cm(3.2), Cm(13.0)],
    )
    doc.add_paragraph(
        "Error handling keeps the session usable: a server ERROR reply is shown "
        "and the same connection continues. Errors the client detects by itself "
        "(missing file, wrong size, existing download target) are reported "
        "without sending anything. End of input triggers a best-effort QUIT and "
        "exit code 0; an unreachable server exits with code 2; a connection lost "
        "during the session exits with code 1."
    )

    heading(doc, "5. Verification", 1)
    heading(doc, "5.1 Automated server tests (check_sockets.py)", 2)
    doc.add_paragraph(
        "check_sockets.py imports the finished server file, replaces only the AI "
        "backend with a stub, and drives the five socket functions and the "
        "provided command loop over real TCP sockets on 127.0.0.1. The run "
        "reported 40 of 40 checks passed with exit code 0. Covered behaviour: "
        "listener creation, accept, framing of payloads from 1 byte to 5,242,880 "
        "bytes, a header delivered byte by byte, two messages arriving in one "
        "read, a malformed header, a zero and an oversized length, clean EOF, a "
        "truncated payload, rejected send arguments, second close, and the full "
        "command flow (UPLOAD, LIST, DESCRIBE with caching, DOWNLOAD, REMOVE, "
        "QUIT, unknown and overlong commands)."
    )

    heading(doc, "5.2 Client conformance test (client_harness.py)", 2)
    doc.add_paragraph(
        "client_harness.py starts the server with the mock backend on an "
        "ephemeral port and scripts a complete session through the client's "
        "standard input, then compares the whole transcript, the downloaded "
        "file and the exit codes with the expected behaviour. The run finished "
        "with PASS and exit code 0. The verified transcript is:"
    )
    add_code(
        doc,
        "client: UPLOAD\n"
        "client: valid.png\n"
        "server: OK 0000\n"
        "client: LIST\n"
        "server: OK\n"
        "server: IMAGE ID: 0000 | FILE: valid.png | TIME: HH:MM:SS | DESCRIPTION: no\n"
        "client: DESCRIBE\n"
        "client: 0000\n"
        "server: OK\n"
        "server: Mock description: the image was received and decoded successfully.\n"
        "client: DESCRIBE\n"
        "client: 9999\n"
        "server: ERROR - Invalid ID\n"
        "client: DOWNLOAD\n"
        "client: 0000\n"
        "client: out.png\n"
        "server: OK valid.png\n"
        "client: Saved to out.png\n"
        "client: REMOVE\n"
        "client: 0000\n"
        "server: OK\n"
        "client: QUIT\n"
        "server: OK",
    )
    doc.add_paragraph(
        "The same harness also verified the local pre-checks (missing and invalid "
        "image paths), the refusal to overwrite an existing download target, the "
        "byte-for-byte equality of the downloaded file, and exit code 2 when the "
        "server is not running."
    )

    heading(doc, "5.3 Real-AI end-to-end run (e2e_real_ai.py)", 2)
    doc.add_paragraph(
        "The end-to-end script starts the unmodified server with the real model, "
        "uploads the three provided test images through the finished client, "
        "describes each of them, downloads one image and removes another. The "
        "run passed with exit code 0; the transcript was:"
    )
    add_code(
        doc,
        "client: UPLOAD\n"
        "client: cat.jpg\n"
        "server: OK 0000\n"
        "client: UPLOAD\n"
        "client: flower.png\n"
        "server: OK 0001\n"
        "client: UPLOAD\n"
        "client: fruit_bowl.jpg\n"
        "server: OK 0002\n"
        "client: LIST\n"
        "server: OK\n"
        "server: IMAGE ID: 0000 | FILE: cat.jpg | TIME: 10:25:20 | DESCRIPTION: no\n"
        "server: IMAGE ID: 0001 | FILE: flower.png | TIME: 10:25:20 | DESCRIPTION: no\n"
        "server: IMAGE ID: 0002 | FILE: fruit_bowl.jpg | TIME: 10:25:20 | DESCRIPTION: no\n"
        "client: DESCRIBE\n"
        "client: 0000\n"
        "server: OK\n"
        "server: In this image we can see a cat lying on the floor.\n"
        "client: DESCRIBE\n"
        "client: 0001\n"
        "server: OK\n"
        "server: In this image we can see two pink roses and two buds.\n"
        "client: DESCRIBE\n"
        "client: 0002\n"
        "server: OK\n"
        "server: In this image there are apples, oranges, pears, and a white bowl.\n"
        "client: LIST\n"
        "server: OK\n"
        "server: IMAGE ID: 0000 | FILE: cat.jpg | TIME: 10:25:20 | DESCRIPTION: yes\n"
        "server: IMAGE ID: 0001 | FILE: flower.png | TIME: 10:25:20 | DESCRIPTION: yes\n"
        "server: IMAGE ID: 0002 | FILE: fruit_bowl.jpg | TIME: 10:25:20 | DESCRIPTION: yes\n"
        "client: DOWNLOAD\n"
        "client: 0002\n"
        "client: fruit_bowl_copy.jpg\n"
        "server: OK fruit_bowl.jpg\n"
        "client: Saved to fruit_bowl_copy.jpg\n"
        "client: REMOVE\n"
        "client: 0001\n"
        "server: OK\n"
        "client: LIST\n"
        "server: OK\n"
        "server: IMAGE ID: 0000 | FILE: cat.jpg | TIME: 10:25:20 | DESCRIPTION: yes\n"
        "server: IMAGE ID: 0002 | FILE: fruit_bowl.jpg | TIME: 10:25:20 | DESCRIPTION: yes\n"
        "client: QUIT\n"
        "server: OK",
    )

    heading(doc, "5.4 Screenshots from our own runs", 2)
    doc.add_paragraph(
        "The screenshots below were captured on the machine described in "
        "Section 2. They show the environment being checked, the server "
        "printing its READY line, and a complete interactive session."
    )
    shots = Path(__file__).resolve().parent / "screenshots"
    figures = (
        (
            "figure1_setup_checkai.png",
            "Figure 1. The environment check: --check-ai prints a caption for "
            "test_images\\cat.jpg.",
        ),
        (
            "figure2_server_ready.png",
            "Figure 2. The server window after startup: READY host=0.0.0.0 "
            "port=18333.",
        ),
        (
            "figure3_client_session.png",
            "Figure 3. A complete interactive client session: UPLOAD, LIST, "
            "DESCRIBE, DOWNLOAD, REMOVE, QUIT.",
        ),
        (
            "figure4_tests.png",
            "Figure 4. check_sockets.py (40/40) and client_harness.py (PASS) "
            "results.",
        ),
    )
    for name, caption in figures:
        path = shots / name
        if path.is_file():
            picture = doc.add_paragraph()
            picture.alignment = WD_ALIGN_PARAGRAPH.CENTER
            picture.add_run().add_picture(str(path), width=Cm(16.0))
            cap = doc.add_paragraph(caption)
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap.runs[0].font.size = Pt(9)
            cap.runs[0].italic = True
        else:
            doc.add_paragraph("[Screenshot placeholder] " + caption)

    heading(doc, "6. Discussion", 1)
    doc.add_paragraph(
        "The length-prefixed framing removed the usual newline and partial-read "
        "problems and let the same helpers serve both directions. Storing only "
        "the required metadata meant that the listing was cheap, while caching "
        "descriptions kept repeated DESCRIBE calls fast on CPU. The main "
        "limitation is caption quality: the 256M model describes the prominent "
        "objects correctly but occasionally misses details such as small text or "
        "exact counts. Upload, download and removal were validated with the "
        "provided demo client and against our own client, so both ends accept "
        "the same byte stream."
    )

    heading(doc, "7. Conclusion", 1)
    doc.add_paragraph(
        "Both tasks are complete: the five socket functions give the server "
        "reliable, exact message exchange, and the client implements the six "
        "commands with the required prompts, prefixes, error messages and exit "
        "codes over a single persistent connection. Automated checks confirm the "
        "protocol boundaries, and a full run on the real model shows the system "
        "describing uploaded images end to end."
    )

    heading(doc, "Notes (remove before submission)", 1)
    doc.add_paragraph(
        "Replace the member table and the [Student ID] placeholders, then "
        "rename the three files to the "
        "submission pattern ImageDescriptionServer_<student_IDs>.py, "
        "ImageDescriptionClient_<student_IDs>.py and "
        "Report_<student_IDs>.pdf. Submit only the sources and this PDF; do not "
        "upload the model directory, the .venv, the .tools directory, "
        "setup.log or any executables."
    )

    doc.save(output)
    print("wrote", output)


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("Report_STUDENT_IDS.docx"))
