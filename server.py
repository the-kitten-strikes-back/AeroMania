import socket, json, threading

players = {}  # {player_id: {'pos': [...], 'rot': [...], 'missiles': [...]}}
players_lock = threading.Lock()


def client_thread(conn, addr, player_id):
    """Handle a single client connection. Uses newline-framed JSON and a shared lock for players."""
    global players

    # send id framed with newline
    try:
        conn.sendall((json.dumps({'id': player_id}) + "\n").encode())
    except Exception:
        conn.close()
        return

    buffer = ""
    try:
        while True:
            try:
                data = conn.recv(4096)
            except ConnectionResetError:
                break
            if not data:
                break

            buffer += data.decode()
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line:
                    continue
                try:
                    player_data = json.loads(line)
                except json.JSONDecodeError:
                    # malformed JSON, skip
                    continue

                with players_lock:
                    players[player_id] = player_data
                    # Send all players except yourself
                    send_data = {pid: pdata for pid, pdata in players.items() if pid != player_id}
                try:
                    conn.sendall((json.dumps(send_data) + "\n").encode())
                except (BrokenPipeError, ConnectionResetError):
                    break

    finally:
        with players_lock:
            players.pop(player_id, None)
        try:
            conn.close()
        except Exception:
            pass


def start_server(host="0.0.0.0", port=5050):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    s.listen()

    print(f"[SERVER] Listening on {host}:{port}")
    player_id = 0

    while True:
        conn, addr = s.accept()
        print("[CONNECTED]", addr)
        t = threading.Thread(target=client_thread, args=(conn, addr, player_id), daemon=True)
        t.start()
        player_id += 1


if __name__ == "__main__":
    start_server()
