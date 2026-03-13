"""aurora_bridge.py
TCP bridge to Aurora 3rd Party API (localhost:1130).
"""
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
        """Try to connect to Aurora. Returns True on success."""
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

    # Low-level send/recv

    def _send(self, cmd: str) -> str | None:
        """Send one command, return the first response line (stripped), or None.

        Returns None only on hard connection errors (not on timeout).
        Caller should check for '$ERR' prefix in the response for Aurora errors.
        """
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
                        # Timeout waiting for response — connection still alive.
                        break
                    if not chunk:
                        # Server closed connection.
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

    # High-level helpers

    def get_selected_callsign(self) -> str | None:
        """Return the callsign selected in Aurora, or None."""
        resp = self._send('#SELTFC')
        if resp and resp.startswith('#SELTFC;'):
            cs = resp.split(';')[1].strip()
            return cs or None
        return None

    def get_flight_plan(self, callsign: str) -> dict | None:
        """
        Return a dict with 'departure' and 'aircraft' keys from the FP, or None.

        Response format (1-based fields after CALLSIGN):
            #FP;CALLSIGN;DEP;ARR;ALT;ETD;AIRCRAFT;WAKE;TYPE;RULES;...
        """
        resp = self._send(f'#FP;{callsign.upper()}')
        if not resp or not resp.startswith('#FP;'):
            return None
        parts = resp.split(';')
        # parts[0]='#FP' parts[1]=callsign parts[2]=dep ... parts[6]=aircraft
        if len(parts) < 7:
            return None
        return {
            'callsign':  parts[1].strip(),
            'departure': parts[2].strip(),   # origin airport ICAO
            'arrival':   parts[3].strip(),
            'aircraft':  parts[6].strip(),   # aircraft ICAO type
        }

    def get_traffic_in_range(self) -> list[str]:
        """Return list of callsigns currently in Aurora's radar range."""
        resp = self._send('#TR')
        if not resp or not resp.startswith('#TR'):
            return []
        # Response: #TR;CS1;CS2;CS3;...
        parts = resp.split(';')[1:]
        return [p.strip() for p in parts if p.strip()]

    def get_traffic_position(self, callsign: str) -> dict | None:
        """
        Return position dict for a callsign, or None.

        Traffic Position Record (fields 1-21 after CALLSIGN):
          12 = assumed_station (parts[13])
          14 = on_ground       (parts[15])  '1' = on ground
          17 = current_gate    (parts[18])
          21 = assigned_gate   (parts[22])
        """
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
        """Return the ATC callsign currently connected in Aurora."""
        resp = self._send('#CONN')
        if not resp:
            return None
        parts = resp.split(';')
        return parts[1].strip() if len(parts) > 1 else None

    def get_occupied_gates(self) -> dict[str, str]:
        """
        Query all traffic in range and return {gate: callsign} for aircraft
        that are on the ground and have a gate (current or assigned).
        Only returns non-empty gate values.
        """
        result: dict[str, str] = {}
        callsigns = self.get_traffic_in_range()
        for cs in callsigns:
            pos = self.get_traffic_position(cs)
            if not pos:
                continue
            # Take assigned_gate first, fall back to current_gate
            gate = pos['assigned_gate'] or pos['current_gate']
            if gate:
                result[gate] = cs
        return result

    def assign_gate(self, callsign: str, gate: str) -> tuple[bool, str]:
        """Send #LBGTE to label the traffic with the assigned gate.
        Returns (success, raw_response_or_reason)."""
        resp = self._send(f'#LBGTE;{callsign.upper()};{gate}')
        if resp is None:
            reason = 'no response (timeout or disconnected)'
            return False, reason
        if resp.startswith('#LBGTE'):
            return True, resp
        return False, resp  # e.g. '$ERR ...' from Aurora


def callsign_to_airline(callsign: str) -> str | None:
    """
    Extract the 3-letter ICAO airline code from a callsign.
    e.g. 'IBE1234' -> 'IBE', 'VLG456' -> 'VLG'
    Returns None if the callsign doesn't start with 3 alpha chars.
    """
    cs = callsign.strip().upper()
    if len(cs) >= 3 and cs[:3].isalpha():
        return cs[:3]
    return None
