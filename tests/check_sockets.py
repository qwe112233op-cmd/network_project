"""Optional self-check for the five Part 1 socket functions of the assignment.

Standard library only: no torch, no PIL, no model needed. It imports the server
file, stubs just prepare_image (image decoding is not what Part 1 is about), and
drives both the raw socket functions and the provided command flow over real
TCP connections on 127.0.0.1.

Usage:
    python check_sockets.py [path\\to\\ImageDescriptionServer.py]
Exit code 0 means every check passed.
"""
import importlib.util
import pathlib
import socket
import sys
import threading
import time

DEFAULT_SERVER = pathlib.Path(
    r"C:\Users\qwe11\Downloads\image-description-assignment"
    r"\image-description-assignment\ImageDescriptionServer.py")
SERVER_FILE = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SERVER

if not SERVER_FILE.is_file():
    sys.exit(f"server file not found: {SERVER_FILE}")

spec = importlib.util.spec_from_file_location("ImageDescriptionServer", SERVER_FILE)
srv = importlib.util.module_from_spec(spec)
sys.modules["ImageDescriptionServer"] = srv
spec.loader.exec_module(srv)

CHECKS = []


def check(name, condition, detail=""):
    CHECKS.append((name, bool(condition)))
    if condition:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name}  <- {detail!r}")


# --------------------------------------------------------------- client helpers
def send_frame(conn, payload):
    conn.sendall(f"{len(payload):010d}".encode("ascii") + payload)


def recv_frame(conn):
    header = b""
    while len(header) < 10:
        chunk = conn.recv(10 - len(header))
        if not chunk:
            raise EOFError("closed while reading header")
        header += chunk
    size = int(header)
    data = b""
    while len(data) < size:
        chunk = conn.recv(size - len(data))
        if not chunk:
            raise EOFError("closed while reading payload")
        data += chunk
    return data


def recv_or_eof(conn):
    try:
        return recv_frame(conn)
    except EOFError:
        return None


def new_connection(timeout=10):
    """create_listener + accept_client + a real client, on an ephemeral port."""
    listener = srv.create_listener("127.0.0.1", 0)
    port = listener.getsockname()[1]
    box = {}

    def accept():
        box["conn"], box["addr"] = srv.accept_client(listener)

    thread = threading.Thread(target=accept, daemon=True)
    thread.start()
    client = socket.create_connection(("127.0.0.1", port), timeout=timeout)
    thread.join(timeout)
    listener.close()
    if "conn" not in box:
        raise RuntimeError("accept_client did not return a connection")
    box["conn"].settimeout(timeout)
    return box["conn"], client, box["addr"]


def payload_of(size):
    return (b"abc\x00\xff" * (size // 5 + 1))[:size]


# ------------------------------------------------------- 1. framing round trips
server_conn, client, address = new_connection()
check("accept_client returns an (IP, port) pair",
      isinstance(address, tuple) and address[0] == "127.0.0.1" and isinstance(address[1], int),
      address)

for size in (1, 5, 1000, 65536, srv.MAX_MESSAGE_BYTES):
    data = payload_of(size)
    send_frame(client, data)
    check(f"receive_message returns {size} payload bytes",
          srv.receive_message(server_conn) == data)
    srv.send_message(server_conn, data)
    check(f"send_message frames {size} payload bytes",
          recv_frame(client) == data)

# --------------------------------------------- 2. split arrival and coalescing
message = b"fragmented message \xe4\xbd\xa0\xe5\xa5\xbd"
frame = f"{len(message):010d}".encode("ascii") + message


def dribble_frame():
    for index in range(10):
        client.sendall(frame[index:index + 1])
        time.sleep(0.001)
    for index in range(10, len(frame), 3):
        client.sendall(frame[index:index + 3])
        time.sleep(0.001)


threading.Thread(target=dribble_frame, daemon=True).start()
check("receive_message handles a byte-by-byte header",
      srv.receive_message(server_conn) == message)

client.sendall(f"{5:010d}".encode("ascii") + b"first" + f"{6:010d}".encode("ascii") + b"second")
check("first message of a coalesced pair", srv.receive_message(server_conn) == b"first")
check("second message of a coalesced pair", srv.receive_message(server_conn) == b"second")

# ------------------------------------------------------ 3. invalid length fields
for label, header in (("a non-digit header", b"00000000X5"),
                      ("a zero length", b"0000000000"),
                      ("an oversized length", b"9999999999")):
    bad_conn, bad_client, _ = new_connection()
    bad_client.sendall(header)
    try:
        srv.receive_message(bad_conn)
        check(f"receive_message rejects {label}", False, "no exception raised")
    except ValueError:
        check(f"receive_message rejects {label}", True)
    except Exception as error:  # noqa: BLE001 - report the wrong exception type
        check(f"receive_message rejects {label}", False, error)
    finally:
        bad_client.close()
        bad_conn.close()

# ------------------------------------------------- 4. close before / during data
closed_conn, closed_client, _ = new_connection()
closed_client.shutdown(socket.SHUT_WR)
check("receive_message returns None when the peer closes between messages",
      srv.receive_message(closed_conn) is None)
closed_conn.close()
closed_client.close()

truncated_conn, truncated_client, _ = new_connection()
truncated_client.sendall(b"0000000005HE")
truncated_client.shutdown(socket.SHUT_WR)
try:
    srv.receive_message(truncated_conn)
    check("receive_message raises when the payload is truncated", False, "no exception raised")
except ConnectionError:
    check("receive_message raises when the payload is truncated", True)
except Exception as error:  # noqa: BLE001 - report the wrong exception type
    check("receive_message raises when the payload is truncated", False, error)
finally:
    truncated_conn.close()
    truncated_client.close()

# ------------------------------------------------------ 5. send/close validation
for label, bad_payload in (("an empty payload", b""),
                           ("an oversized payload", b"x" * (srv.MAX_MESSAGE_BYTES + 1))):
    try:
        srv.send_message(server_conn, bad_payload)
        check(f"send_message rejects {label}", False, "no exception raised")
    except ValueError:
        check(f"send_message rejects {label}", True)
    except Exception as error:  # noqa: BLE001 - report the wrong exception type
        check(f"send_message rejects {label}", False, error)

srv.send_message(server_conn, b"HELLO")
check("send_message writes exactly 10 header digits",
      client.recv(10) == b"0000000005", "header was not b'0000000005'")
check("send_message writes the payload after the header", client.recv(5) == b"HELLO")

srv.close_client(server_conn)
check("close_client releases the socket", server_conn.fileno() == -1, server_conn.fileno())
check("the peer sees EOF after close_client", client.recv(1) == b"")
client.close()

# ------------------------------------------- 6. the provided command flow, end to end
class FakeImage:
    def close(self):
        pass


original_prepare_image = srv.prepare_image
srv.prepare_image = lambda data: FakeImage()  # image decoding is not part of Part 1
try:
    caption_calls = []

    def caption_image(data):
        caption_calls.append(data)
        return "A cat sitting on a blue sofa."

    store = {"images": {}, "next_id": 0, "stopping": False}
    store_lock = threading.Lock()
    listener = srv.create_listener("127.0.0.1", 0)
    port = listener.getsockname()[1]
    accepted = {}

    def accept():
        accepted["conn"], _ = srv.accept_client(listener)

    threading.Thread(target=accept, daemon=True).start()
    flow_client = socket.create_connection(("127.0.0.1", port), timeout=10)
    deadline = time.time() + 10
    while "conn" not in accepted and time.time() < deadline:
        time.sleep(0.01)
    flow_conn = accepted["conn"]
    flow_conn.settimeout(20)
    worker = threading.Thread(target=srv.handle_client,
                              args=(flow_conn, store, store_lock, caption_image),
                              daemon=True)
    worker.start()
    listener.close()

    image_bytes = b"\x89PNG fake image bytes"
    send_frame(flow_client, b"UPLOAD cat.jpg")
    send_frame(flow_client, image_bytes)
    check("UPLOAD stores the image and returns its id", recv_or_eof(flow_client) == b"OK 0000")

    send_frame(flow_client, b"LIST")
    reply = recv_or_eof(flow_client)
    check("LIST shows the image as not yet described",
          reply is not None and b"IMAGE ID: 0000" in reply and b"FILE: cat.jpg" in reply
          and b"DESCRIPTION: no" in reply, reply)

    send_frame(flow_client, b"describe 0000")
    check("DESCRIBE (mixed case) returns the caption",
          recv_or_eof(flow_client) == b"OK\nA cat sitting on a blue sofa.")

    send_frame(flow_client, b"DESCRIBE 0000")
    check("a second DESCRIBE reuses the cached caption",
          recv_or_eof(flow_client) == b"OK\nA cat sitting on a blue sofa."
          and len(caption_calls) == 1, f"caption calls: {len(caption_calls)}")

    send_frame(flow_client, b"DOWNLOAD 0000")
    check("DOWNLOAD replies with the filename", recv_or_eof(flow_client) == b"OK cat.jpg")
    check("DOWNLOAD sends the stored bytes", recv_or_eof(flow_client) == image_bytes)

    send_frame(flow_client, b"REMOVE 0000")
    check("REMOVE deletes the image", recv_or_eof(flow_client) == b"OK")
    send_frame(flow_client, b"LIST")
    check("LIST is empty after REMOVE", recv_or_eof(flow_client) == b"OK\nNo images")

    send_frame(flow_client, b"NOPE")
    check("an unknown command is rejected",
          recv_or_eof(flow_client) == b"ERROR - Command not understood")

    send_frame(flow_client, b"QUIT")
    check("QUIT replies OK", recv_or_eof(flow_client) == b"OK")
    check("the handler closes the connection after QUIT", recv_or_eof(flow_client) is None)
    worker.join(10)
    check("the handler thread finished", not worker.is_alive())
    flow_client.close()

    # a bad header must produce an error reply and end that connection
    listener = srv.create_listener("127.0.0.1", 0)
    port = listener.getsockname()[1]
    accepted = {}

    def accept_bad():
        accepted["conn"], _ = srv.accept_client(listener)

    threading.Thread(target=accept_bad, daemon=True).start()
    bad_client = socket.create_connection(("127.0.0.1", port), timeout=10)
    deadline = time.time() + 10
    while "conn" not in accepted and time.time() < deadline:
        time.sleep(0.01)
    bad_conn = accepted["conn"]
    bad_conn.settimeout(20)
    bad_worker = threading.Thread(target=srv.handle_client,
                                  args=(bad_conn, {"images": {}, "next_id": 0, "stopping": False},
                                        threading.Lock(), caption_image),
                                  daemon=True)
    bad_worker.start()
    listener.close()

    bad_client.sendall(b"00000000X5")
    check("a malformed header gets an ERROR reply",
          recv_or_eof(bad_client) == b"ERROR - Invalid length header")
    check("the connection ends after a malformed header", recv_or_eof(bad_client) is None)
    bad_client.close()

    # an over-long command must also be refused
    listener = srv.create_listener("127.0.0.1", 0)
    port = listener.getsockname()[1]
    accepted = {}

    def accept_long():
        accepted["conn"], _ = srv.accept_client(listener)

    threading.Thread(target=accept_long, daemon=True).start()
    long_client = socket.create_connection(("127.0.0.1", port), timeout=10)
    deadline = time.time() + 10
    while "conn" not in accepted and time.time() < deadline:
        time.sleep(0.01)
    long_conn = accepted["conn"]
    long_conn.settimeout(20)
    long_worker = threading.Thread(target=srv.handle_client,
                                   args=(long_conn, {"images": {}, "next_id": 0, "stopping": False},
                                         threading.Lock(), caption_image),
                                   daemon=True)
    long_worker.start()
    listener.close()

    send_frame(long_client, b"X" * 2000)
    check("an over-long command gets an ERROR reply",
          recv_or_eof(long_client) == b"ERROR - Command is too long")
    long_client.close()
finally:
    srv.prepare_image = original_prepare_image

failed = [name for name, ok in CHECKS if not ok]
print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
if failed:
    print("Failed: " + ", ".join(failed))
sys.exit(1 if failed else 0)
