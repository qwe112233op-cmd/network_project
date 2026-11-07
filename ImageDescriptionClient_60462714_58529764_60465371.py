import os
import socket
import sys

HEADER_SIZE = 10
MAX_MESSAGE_BYTES = 5 * 1024 * 1024
MAX_COMMAND_BYTES = 1024


def _recv_exact(sock, count):
    data = b""
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            if not data:
                return None
            raise ConnectionError("connection closed during a message")
        data += chunk
    return data


def _send_message(sock, payload):
    payload = bytes(payload)
    if not 1 <= len(payload) <= MAX_MESSAGE_BYTES:
        raise ValueError("message length must be 1..5 MiB")
    header = f"{len(payload):0{HEADER_SIZE}d}".encode("ascii")
    sock.sendall(header + payload)


def _receive_message(sock):
    header = _recv_exact(sock, HEADER_SIZE)
    if header is None:
        return None
    if not header.isdigit():
        raise ConnectionError("invalid message length header from server")
    length = int(header)
    if not 1 <= length <= MAX_MESSAGE_BYTES:
        raise ConnectionError("invalid message length from server")
    payload = _recv_exact(sock, length)
    if payload is None:
        raise ConnectionError("connection closed during a message")
    return payload


def _print_client(text):
    print("client: " + text, flush=True)


def _print_server(payload):
    text = payload.decode("utf-8", "replace")
    for line in text.splitlines() or [""]:
        print("server: " + line, flush=True)


def _read_input(interactive):
    print("client: ", end="", flush=True)
    line = sys.stdin.readline()
    if line == "":
        print()
        return None
    line = line.rstrip("\r\n")
    if not interactive:
        print(line, flush=True)
    return line


def _upload(sock, path):
    if not os.path.exists(path):
        _print_client("ERROR - File not found")
        return
    if os.path.isdir(path):
        _print_client("ERROR - Image must be an existing file of 1 byte to 5 MiB")
        return
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError:
        _print_client("ERROR - File not found")
        return
    if size < 1 or len(data) != size or len(data) > MAX_MESSAGE_BYTES:
        _print_client("ERROR - Image must be an existing file of 1 byte to 5 MiB")
        return

    command = ("UPLOAD " + os.path.basename(path)).encode("utf-8")
    if len(command) > MAX_COMMAND_BYTES:
        _print_client("ERROR - Invalid filename")
        return
    _send_message(sock, command)
    _send_message(sock, data)
    reply = _receive_message(sock)
    if reply is not None:
        _print_server(reply)


def _download(sock, image_id, out_path):
    _send_message(sock, ("DOWNLOAD " + image_id).encode("utf-8"))
    reply = _receive_message(sock)
    if reply is None:
        return
    first = reply.decode("utf-8", "replace").splitlines()
    first = first[0] if first else ""
    _print_server(reply)
    if not first.startswith("OK "):
        return
    image = _receive_message(sock)
    if image is None:
        return
    directory = os.path.dirname(out_path) or "."
    if not os.path.isdir(directory) or os.path.exists(out_path):
        _print_client("ERROR - Choose a new file in an existing directory")
        return
    try:
        with open(out_path, "xb") as handle:
            handle.write(image)
    except OSError:
        _print_client("ERROR - Choose a new file in an existing directory")
        return
    _print_client("Saved to " + out_path)


def _quit(sock):
    try:
        _send_message(sock, b"QUIT")
        reply = _receive_message(sock)
        if reply is not None:
            _print_server(reply)
    except (OSError, ConnectionError):
        pass


def main(argv=None):
    argv = sys.argv if argv is None else argv
    if len(argv) != 3:
        print("Usage: python ImageDescriptionClient.py <host> <port>", file=sys.stderr)
        return 2
    host = argv[1]
    try:
        port = int(argv[2])
    except ValueError:
        print("ERROR - Invalid port: " + argv[2], file=sys.stderr)
        return 2

    try:
        sock = socket.create_connection((host, port), timeout=10)
    except OSError as error:
        print("ERROR - Could not connect to %s:%s (%s)" % (host, port, error),
              file=sys.stderr)
        return 2
    sock.settimeout(None)
    interactive = sys.stdin.isatty()

    try:
        while True:
            command_line = _read_input(interactive)
            if command_line is None:
                _quit(sock)
                return 0
            command_line = command_line.strip()
            if not command_line:
                continue
            parts = command_line.split(maxsplit=1)
            command = parts[0].upper()
            argument = parts[1].strip() if len(parts) > 1 else ""

            if command == "UPLOAD":
                path = _read_input(interactive)
                if path is None:
                    _quit(sock)
                    return 0
                _upload(sock, path.strip())

            elif command == "LIST" and not argument:
                _send_message(sock, b"LIST")
                reply = _receive_message(sock)
                if reply is not None:
                    _print_server(reply)

            elif command in ("DESCRIBE", "REMOVE"):
                image_id = _read_input(interactive)
                if image_id is None:
                    _quit(sock)
                    return 0
                _send_message(sock, (command + " " + image_id.strip()).encode("utf-8"))
                reply = _receive_message(sock)
                if reply is not None:
                    _print_server(reply)

            elif command == "DOWNLOAD":
                image_id = _read_input(interactive)
                if image_id is None:
                    _quit(sock)
                    return 0
                out_path = _read_input(interactive)
                if out_path is None:
                    _quit(sock)
                    return 0
                _download(sock, image_id.strip(), out_path.strip())

            elif command == "QUIT" and not argument:
                _send_message(sock, b"QUIT")
                reply = _receive_message(sock)
                if reply is not None:
                    _print_server(reply)
                return 0

            else:
                _send_message(sock, command_line.encode("utf-8"))
                reply = _receive_message(sock)
                if reply is not None:
                    _print_server(reply)

    except OSError as error:
        print("ERROR - Connection lost: %s" % error, file=sys.stderr)
        return 1
    finally:
        try:
            sock.close()
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
