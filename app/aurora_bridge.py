# aurora tcp bridge (localhost:1130)
import socket
import threading

AURORA_HOST = '127.0.0.1'
AURORA_PORT = 1130
TIMEOUT     = 3.0


class AuroraBridge:
    def __init__(self):
        self._sock  = None
        self._lock  = threading.Lock()
        self.connected = False

    # Connection

    def connect(self):
        # try to connect
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(TIMEOUT)
            s.connect((AURORA_HOST, AURORA_PORT))
            self._sock     = s
            self.connected = True
            return True
        except OSError:
            self._sock     = None
            self.connected = False
            return False

    def disconnect(self):
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
        self._sock     = None
        self.connected = False

    # low-level send/recv

    def _send(self, cmd: str) -> str | None:
        # send cmd, get response line
        if not self.connected or not self._sock:
            return None
        with self._lock:
            try:
                self._sock.sendall((cmd.strip() + '\r\n').encode('ascii'))
                buf = b''
                while True:
                    try:
                        chunk = self._sock.recv(4096)
                    except socket.timeout:
                        break
                    if not chunk:
                        self.connected = False
                        break
                    buf += chunk
                    if b'\n' in buf:
                        break
                if not buf:
                    return None
                return buf.decode('ascii', errors='replace').split('\n')[0].strip('\r\n ')
            except OSError:
                self.connected = False
                return None

    # aurora helpers

    def get_selected_callsign(self) -> str | None:
        # get selected traffic cs
        resp = self._send('#SELTFC')
        if resp and resp.startswith('#SELTFC;'):
            cs = resp.split(';')[1].strip()
            return cs or None
        return None

    def get_flight_plan(self, callsign: str) -> dict | None:
        # get fp fields (dep, acft)
        resp = self._send(f'#FP;{callsign.upper()}')
        if not resp or not resp.startswith('#FP;'):
            return None
        parts = resp.split(';')
        if len(parts) < 7:
            return None
        return {
            'callsign':  parts[1].strip(),
            'departure': parts[2].strip(),
            'arrival':   parts[3].strip(),
            'aircraft':  parts[6].strip(),
        }

    def get_traffic_in_range(self) -> list[str]:
        # list all cs in range
        resp = self._send('#TR')
        if not resp or not resp.startswith('#TR'):
            return []
        parts = resp.split(';')[1:]
        return [p.strip() for p in parts if p.strip()]

    def get_traffic_position(self, callsign: str) -> dict | None:
        # get assumed, on_ground, gates
        resp = self._send(f'#TRPOS;{callsign.upper()}')
        if not resp or not resp.startswith('#TRPOS;'):
            return None
        parts = resp.split(';')
        return {
            'callsign':         parts[1].strip()  if len(parts) > 1  else '',
            'assumed_station':  parts[13].strip() if len(parts) > 13 else '',
            'on_ground':        parts[15].strip() if len(parts) > 15 else '',
            'current_gate':     parts[18].strip() if len(parts) > 18 else '',
            'assigned_gate':    parts[22].strip() if len(parts) > 22 else '',
        }

    def get_connected_callsign(self) -> str | None:
        # get our connected cs
        resp = self._send('#CONN')
        if not resp:
            return None
        parts = resp.split(';')
        return parts[1].strip() if len(parts) > 1 else None

    def get_occupied_gates(self) -> dict[str, str]:
        # traffic on ground with gate
        result: dict[str, str] = {}
        callsigns = self.get_traffic_in_range()
        for cs in callsigns:
            pos = self.get_traffic_position(cs)
            if not pos:
                continue
            gate = pos['assigned_gate'] or pos['current_gate']
            if gate:
                result[gate] = cs
        return result

    def assign_gate(self, callsign: str, gate: str) -> tuple[bool, str]:
        # push gate label (#LBGTE)
        resp = self._send(f'#LBGTE;{callsign.upper()};{gate}')
        if resp is None:
            reason = 'no response'
            return False, reason
        if resp.startswith('#LBGTE'):
            return True, resp
        return False, resp


def callsign_to_airline(callsign: str) -> str | None:
    # extract 3-letter icao
    cs = callsign.strip().upper()
    if len(cs) >= 3 and cs[:3].isalpha():
        return cs[:3]
    return None
