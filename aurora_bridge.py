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

    # ── Connection ────────────────────────────────────────────────────────────

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

    # ── Low-level send/recv ───────────────────────────────────────────────────

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

    # ── High-level helpers ────────────────────────────────────────────────────

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
