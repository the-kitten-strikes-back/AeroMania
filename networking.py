network_planes = {}
ghost_model = 'models/f167'
network_missiles = {}

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5050

try:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((SERVER_IP, SERVER_PORT))

    buf = ''
    while '\n' not in buf:
        buf += client.recv(4096).decode()
    player_id = json.loads(buf.split('\n', 1)[0])['id']
    print("Connected as player", player_id)
except:
    print("Could not connect to server, running offline")
    client = None
    player_id = "offline"

other_players = {}
net_recv_buffer = ''

def networking_loop():
    global other_players, net_recv_buffer
    if not client:
        return
    
    while True:
        missiles_payload = []
        for m in missiles:
            mid = getattr(m, 'net_id', None)
            if mid is None:
                continue
            missiles_payload.append({
                'id': mid,
                'pos': [m.x, m.y, m.z],
                'forward': [m.forward_vec.x, m.forward_vec.y, m.forward_vec.z],
                'vel': m.velocity,
            })
        
        send_data = {
            "pos": [plane.x, plane.y, plane.z],
            "rot": [plane.rotation_x, plane.rotation_y, plane.rotation_z],
            "missiles": missiles_payload,
        }
        try:
            client.sendall((json.dumps(send_data) + "\n").encode())
        except (BrokenPipeError, ConnectionResetError):
            break

        try:
            data = client.recv(4096)
            if not data:
                break
            net_recv_buffer += data.decode()
            while '\n' in net_recv_buffer:
                line, net_recv_buffer = net_recv_buffer.split('\n', 1)
                if not line:
                    continue
                try:
                    other_players = json.loads(line)
                except json.JSONDecodeError:
                    continue
        except (BrokenPipeError, ConnectionResetError):
            break

        time.sleep(0.066)

if client:
    net_thread = threading.Thread(target=networking_loop, daemon=True)
    net_thread.start()
