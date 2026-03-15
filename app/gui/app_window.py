# main app window
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading, datetime, json, sys, os


def _pick_airport(parent, available):
    """Modal dropdown to choose an airport. Returns selected ICAO."""
    dlg = tk.Toplevel(parent)
    dlg.title("Stand Manager")
    dlg.configure(bg=C['bg3'])
    dlg.resizable(False, False)
    dlg.grab_set()
    dlg.focus_set()

    result = [available[0]]

    tk.Label(dlg, text="Seleccionar aeropuerto", font=FONT_L,
             bg=C['bg3'], fg=C['accent']).pack(padx=30, pady=(20, 10))

    var = tk.StringVar(value=available[0])
    cb = ttk.Combobox(dlg, textvariable=var, values=available,
                      state='readonly', font=FONT, width=18,
                      justify='center')
    cb.pack(padx=30, pady=(0, 16))

    def _ok():
        result[0] = var.get()
        dlg.destroy()

    _btn(dlg, "ACEPTAR", _ok, bg=C['seg_on']).pack(pady=(0, 20))
    dlg.bind('<Return>', lambda _: _ok())

    # center over parent
    parent.update_idletasks()
    px, py = parent.winfo_x(), parent.winfo_y()
    pw, ph = parent.winfo_width(), parent.winfo_height()
    dlg.update_idletasks()
    dw, dh = dlg.winfo_width(), dlg.winfo_height()
    dlg.geometry(f"+{px + (pw - dw)//2}+{py + (ph - dh)//2}")

    dlg.wait_window()
    return result[0]

from app.theme import C, FONT, FONT_S, FONT_L, FONT_X, _btn, SegGroup
from app.aurora_bridge import AuroraBridge, callsign_to_airline
import app.parking_finder as pf
from app.callsign_analyzer import CallsignAnalyzer
from app.core.airport import AirportData
from app.gui.panels import left_panel, right_panel, assignments_dialog, occupied_dialog


class ParkingApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Stand Manager  ·  v2.2")
        self.configure(bg=C['bg3'])
        self.minsize(1020, 700)
        self.geometry('1120x760')

        # select airport
        available = AirportData.available()
        selected_icao = available[0] if available else ''
        if len(available) > 1:
            selected_icao = _pick_airport(self, available)
        
        # load airport data
        airport = AirportData(selected_icao)
        pf.CURRENT_ICAO = selected_icao
        self.airport_icao          = selected_icao
        self.airport_config        = airport.config
        self.terminals             = airport.config.get('terminals', [])
        self.dedicated_airline_map = airport.config.get('dedicated_airline_map', {})
        self.airlines  = airport.airlines
        self.wingspans = airport.wingspans
        self.parkings  = airport.parkings

        # state
        self._cs_analyzer   = CallsignAnalyzer()
        self._ga_forced     : bool  = False  # manual GA toggle

        self.occupied       : set   = set()
        self.occupied_by    : dict  = {}   # {stand: data}
        self.current_cs     : str   = ''
        self.current_dm     : dict  = {}
        self.all_sorted     : list  = []
        self.sch_bool       : bool  = True
        self.acft_ws        : float = 0.0
        self.selected_stand : str   = ''
        self.preassigned    : dict  = {}   # {cs: data}
        self.assignments    : list  = []   # session history
        self._assign_win             = None
        self._occ_win                = None
        self._my_callsign   : str   = ''   # our ATC cs

        # poller
        self._auto_var    = tk.BooleanVar(value=False)
        self._last_polled : str  = ''
        self._poll_job          = None
        self.POLL_MS      = 4000

        # bridge
        self.aurora = AuroraBridge()

        self._build_ui()
        self._log("App started & initialized", 'info')
        self._try_connect_aurora()

        # hotkeys
        self.bind('<F5>', lambda e: self._query_aurora())
        self.bind('<Return>', lambda e: self._assign_stand())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # UI setup

    def _build_ui(self):
        self._build_header()
        tk.Frame(self, bg=C['sep'], height=2).pack(fill=tk.X)
        body = tk.Frame(self, bg=C['bg'])
        body.pack(fill=tk.BOTH, expand=True)
        left_panel.build(self, body)
        tk.Frame(body, bg='#2a2a2a', width=1).pack(side=tk.LEFT, fill=tk.Y)
        right_panel.build(self, body)
        tk.Frame(self, bg='#2a2a2a', height=1).pack(fill=tk.X)
        self._build_log()
        tk.Frame(self, bg=C['sep'], height=2).pack(fill=tk.X)
        self._build_footer()

    # header

    def _build_header(self):
        hdr = tk.Frame(self, bg=C['hdr'], pady=10)
        hdr.pack(fill=tk.X)

        lf = tk.Frame(hdr, bg=C['hdr'])
        lf.pack(side=tk.LEFT, padx=14)
        tk.Label(lf, text="✈", font=('Consolas', 28), bg=C['hdr'], fg=C['accent']).pack(side=tk.LEFT)
        tf = tk.Frame(lf, bg=C['hdr'])
        tf.pack(side=tk.LEFT, padx=10)
        tk.Label(tf, text="Stand Manager", font=FONT_X, bg=C['hdr'], fg=C['fg']).pack(anchor='w')
        tk.Label(tf, text=f"{self.airport_config.get('name', '')}  ·  IVAO Virtual ATC  ·  v2.2", font=FONT_S, bg=C['hdr'], fg=C['fg_dim']).pack(anchor='w')

        rf = tk.Frame(hdr, bg=C['hdr'])
        rf.pack(side=tk.RIGHT, padx=16)

        self.auto_cb = tk.Checkbutton(
            rf, text="Auto", font=FONT_S, variable=self._auto_var,
            bg=C['hdr'], fg=C['fg_dim'], selectcolor=C['bg2'],
            activebackground=C['hdr'], activeforeground=C['fg'],
            command=self._on_auto_toggle)
        self.auto_cb.pack(side=tk.LEFT, padx=(0, 16))

        self.aurora_dot = tk.Label(rf, text="●", font=('Consolas', 14), bg=C['hdr'], fg=C['red'])
        self.aurora_dot.pack(side=tk.LEFT)
        self.aurora_lbl = tk.Label(rf, text="Aurora disconnected", font=FONT_S, bg=C['hdr'], fg=C['red'])
        self.aurora_lbl.pack(side=tk.LEFT, padx=(4, 0))

    # log box

    def _build_log(self):
        wrap = tk.Frame(self, bg=C['bg3'], height=120)
        wrap.pack(fill=tk.X)
        wrap.pack_propagate(False)
        tk.Label(wrap, text=" Log", font=FONT_S, bg=C['bg3'], fg=C['fg_dim'], anchor='w').pack(fill=tk.X, padx=8, pady=(3, 0))
        self.log_box = tk.Text(wrap, bg=C['bg3'], fg=C['fg_dim'], font=FONT_S, relief=tk.FLAT, state=tk.DISABLED, wrap=tk.WORD)
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 4))
        for tag, col in [('info', C['accent']), ('ok', C['green']), ('warn', C['orange']), ('err', C['red'])]:
            self.log_box.tag_config(tag, foreground=col)

    # footer

    def _build_footer(self):
        bar = tk.Frame(self, bg=C['hdr'], pady=7)
        bar.pack(fill=tk.X)
        self.conn_btn = _btn(bar, "CONNECT TO AURORA", self._connect_aurora)
        self.conn_btn.pack(side=tk.LEFT, padx=(10, 4))
        _btn(bar, "QUERY SELECTED  (F5)", self._query_aurora, bg='#0a3d0a').pack(side=tk.LEFT, padx=4)
        _btn(bar, "ASIGNACIONES  ▤", self._open_assignments_panel, bg='#1a2a3a').pack(side=tk.LEFT, padx=4)
        _btn(bar, "CLEAR ALL STANDS", self._clear_occupied, bg='#3d0a0a').pack(side=tk.LEFT, padx=4)

    def _slabel(self, parent, text):
        tk.Label(parent, text=f"  {text}", font=FONT_S, bg=C['bg'], fg=C['fg_dim'], anchor='w').pack(fill=tk.X, pady=(8, 2))

    # strip ops (from left_panel)

    def _strip_empty(self):
        left_panel._strip_empty(self)

    def _strip_update(self, callsign, airline, aircraft, origin, stand, sch_str, terminal):
        left_panel._strip_update(self, callsign, airline, aircraft, origin, stand, sch_str, terminal)

    # aurora

    def _try_connect_aurora(self):
        def _do():
            ok = self.aurora.connect()
            self.after(0, self._on_aurora_ok if ok else self._on_aurora_fail)
        threading.Thread(target=_do, daemon=True).start()

    def _connect_aurora(self):
        self.aurora.disconnect()
        self.aurora_dot.config(fg=C['orange'])
        self.aurora_lbl.config(text="Connecting…", fg=C['orange'])
        self._try_connect_aurora()

    def _on_aurora_ok(self):
        self.aurora_dot.config(fg=C['green'])
        self.aurora_lbl.config(text="Aurora connected", fg=C['green'])
        self.conn_btn.config(text="RECONNECT AURORA")
        self._my_callsign = self.aurora.get_connected_callsign() or ''
        suffix = f"  ({self._my_callsign})" if self._my_callsign else ''
        self._log(f"Connected to Aurora  (localhost:1130){suffix}", 'ok')
        self._sync_occupied_aurora()
        if self._auto_var.get(): self._poll()

    def _on_aurora_fail(self):
        self.aurora_dot.config(fg=C['red'])
        self.aurora_lbl.config(text="Aurora disconnected", fg=C['red'])
        self._log("Aurora not available — running standalone", 'warn')

    # query ops

    def _query_aurora(self):
        # fetch selected traffic from aurora
        if not self.aurora.connected:
            self._log("Aurora not connected", 'warn'); return
        cs = self.aurora.get_selected_callsign()
        if not cs:
            self._log("No traffic selected in Aurora", 'warn'); return
        fp = self.aurora.get_flight_plan(cs)
        if not fp:
            self._log(f"No flight plan for {cs}", 'warn'); return
        airline, aircraft, origin = callsign_to_airline(cs) or '', fp.get('aircraft', ''), fp.get('departure', '')
        self._ga_forced = False
        self.v_callsign.set(cs); self.v_airline.set(airline); self.v_aircraft.set(aircraft); self.v_origin.set(origin)
        self._log(f"Aurora FP: {cs} → {airline} {aircraft} from {origin}", 'info')
        self._run_query(cs, airline or None, aircraft or None, origin or None)

    def _on_callsign_change(self):
        # auto-ga detection on typing
        cs = self.v_callsign.get().strip()
        if not cs: self._set_ga_indicator(False, ''); return
        res = self._cs_analyzer.check(cs)
        if res['is_private']: self._set_ga_indicator(True, res['countries'][0] if res['countries'] else '')
        else: self._set_ga_indicator(False, '')

    def _set_ga_indicator(self, is_private: bool, country: str):
        # update ga badge
        if is_private:
            self._ga_btn.config(fg=C['green'], bg=C['seg_on'])
            short = country[:12] if country else 'GA/Privado'
            self._country_lbl.config(text=short, fg=C['green'])
            if not self._ga_forced: self._ga_var.set(True)
        else:
            if not self._ga_forced:
                self._ga_var.set(False); self._ga_btn.config(fg=C['fg_dim'], bg=C['bg2'])
            self._country_lbl.config(text='', fg=C['fg_dim'])

    def _on_ga_toggle(self):
        # manual ga override
        self._ga_forced = self._ga_var.get()
        if self._ga_forced:
            self._ga_btn.config(fg=C['green'], bg=C['seg_on'])
            self._country_lbl.config(text='manual', fg=C['orange'])
        else:
            self._ga_btn.config(fg=C['fg_dim'], bg=C['bg2']); self._country_lbl.config(text='', fg=C['fg_dim'])
            self._on_callsign_change()

    def _clear_query(self):
        for v in (self.v_callsign, self.v_airline, self.v_aircraft, self.v_origin): v.set('')
        self.current_cs = ''; self._ga_forced = False; self._ga_var.set(False)
        self._ga_btn.config(fg=C['fg_dim'], bg=C['bg2']); self._country_lbl.config(text='', fg=C['fg_dim'])

    def _query_manual(self):
        # query with manual input
        cs, air, acft, dep = self.v_callsign.get().strip().upper() or None, self.v_airline.get().strip().upper() or None, self.v_aircraft.get().strip().upper() or None, self.v_origin.get().strip().upper() or None
        if not air and not acft:
            messagebox.showwarning("Faltan campos", "Escribe al menos Airline o Aircraft.", parent=self); return
        self._run_query(cs, air, acft, dep)

    def _run_query(self, cs, airline, acft, origin):
        # core search engine
        self.current_cs, self.selected_stand = cs or '', ''
        self.assign_btn.config(state=tk.DISABLED, text="Assign Stand  ↵")

        # wingspan
        ws = None
        if acft:
            acft = pf.resolve_aircraft_type(acft, self.wingspans)
            ws = self.wingspans.get(acft)
            if ws is None:
                ws = simpledialog.askfloat("Avión desconocido", f"'{acft}' missing in db.\nWingspan (m):", parent=self, minvalue=5.0, maxvalue=110.0)
                if ws:
                    self.wingspans[acft] = ws
                    try:
                        with open(pf.WINGSPANS_JSON, 'w', encoding='utf-8') as f: json.dump(dict(sorted(self.wingspans.items())), f, indent=2)
                    except: pass
                ws = ws or 36.0
        self.acft_ws = ws or 0.0

        # schengen
        sch_over = self.seg['Schengen'].get()
        if sch_over == 'yes': sch = True
        elif sch_over == 'no': sch = False
        elif origin: sch = origin[:2].upper() in pf.SCHENGEN_PREFIXES
        else: sch = None
        self.sch_bool = sch if sch is not None else True
        sch_str = ("SCHENGEN" if sch else "NON-SCHENGEN") if sch is not None else ""

        # term / ga
        term_over, ga_mode = self.seg['Terminal'].get(), self._ga_var.get()

        # build pool
        pool, term, lbl, fallbk = self._build_pool(airline, acft, ws, sch, origin, term_over, ga_mode=ga_mode)

        # filter type
        type_f = self.seg['Tipo'].get()
        if not ga_mode:
            if type_f == 'gates': pool = {k: v for k, v in pool.items() if not v.get('remote', False)}
            elif type_f == 'remote': pool = {k: v for k, v in pool.items() if v.get('remote', False)}

        self.current_dm = pool
        self._populate_table(pool, self.sch_bool, ws or 0.0, fallback=fallbk)

        # log it
        extra = []
        if ws: extra.append(f"{ws}m")
        if sch_str: extra.append(sch_str)
        if ga_mode: extra.append("GA/Privado")
        elif type_f != 'all': extra.append(type_f)
        self._log(f"{'FALLBACK  ' if fallbk else ''}{lbl}  →  {len(pool)} stands", 'warn' if fallbk else 'info')
        self._strip_update(cs or airline or '—', airline or '', acft or '', origin or '', '', sch_str, term or '—')

    def _build_pool(self, airline, acft, ws, sch, origin, term_over, ga_mode=False):
        # find candidates by logic
        occ, pks = self.occupied, self.parkings

        # GA logic
        if ga_mode:
            ws_req, lbl_base = ws or 0, f"GA {acft}" if acft else "GA Privado"
            def _ga_pool(p): return {id: d for id, d in pks.items() if id not in occ and (d.get('max_wingspan') or 0) >= ws_req and p(id, d)}
            # order: GA -> MTO -> Cargo -> terminals remote -> terminals all
            pool = _ga_pool(lambda i, d: d.get('schengen') == 'ga')
            if pool: return pool, 'GA', lbl_base, False
            pool = _ga_pool(lambda i, d: d.get('schengen') == 'maintenance')
            if pool: return pool, 'MTO', f"{lbl_base} → Mantenimiento", True
            pool = _ga_pool(lambda i, d: d.get('schengen') == 'cargo')
            if pool: return pool, 'CARGO', f"{lbl_base} → Cargo", True
            _is_comm = lambda i, d: d.get('schengen') not in ('ga', 'maintenance', 'cargo')
            for t in reversed(self.terminals):
                pool = _ga_pool(lambda i, d, t=t: _is_comm(i, d) and d.get('terminal') == t and d.get('remote'))
                if pool: return pool, t, f"{lbl_base} → {t} Remote", True
                pool = _ga_pool(lambda i, d, t=t: _is_comm(i, d) and d.get('terminal') == t)
                if pool: return pool, t, f"{lbl_base} → {t}", True
            return {}, self.terminals[-1], f"{lbl_base} → {self.terminals[-1]}", True

        # aircraft only
        if not airline:
            pool = {}
            for i, d in pks.items():
                if i in occ: continue
                if d.get('schengen') in ('ga', 'maintenance'): continue
                if ws and (d.get('max_wingspan') or 999) < ws: continue
                if sch is not None and not pf.schengen_ok(d, sch): continue
                if term_over in self.terminals and d.get('terminal') != term_over: continue
                pool[i] = d
            return pool, term_over or 'ALL', f"Aircraft {acft}", False

        # cargo
        if pf.get_airline_terminal(self.airlines, airline) == 'CARGO' and airline not in pf.DEDICATED:
            pool = {i: d for i, d in pks.items() if d.get('schengen') == 'cargo' and i not in occ and (d.get('max_wingspan') or 999) >= (ws or 0)}
            return pool, 'CARGO', f"CARGO {airline}", False

        # dedicated
        if airline in pf.DEDICATED:
            dt, dl = pf.DEDICATED_TERMINAL.get(airline, self.terminals[0]), pf.DEDICATED_LABEL.get(airline, airline)
            pool = {i: pks[i] for i in pf.DEDICATED[airline] if i in pks and i not in occ and (pks[i].get('max_wingspan') or 0) >= (ws or 0) and (sch is None or pf.schengen_ok(pks[i], sch))}
            if pool: return pool, dt, dl, False
            t = term_over if term_over in self.terminals else dt
            pool = pf.filter_parkings(pks, t, airline, ws or 0, sch if sch is not None else True, occ, dedicated_map=self.dedicated_airline_map)
            if not pool:
                o = next((x for x in self.terminals if x != t), self.terminals[0])
                pool = pf.filter_parkings(pks, o, airline, ws or 0, sch if sch is not None else True, occ, dedicated_map=self.dedicated_airline_map)
                return pool, o, f"{airline} fallback→{o}", True
            return pool, t, f"{airline} fallback→{t}", True

        # standard
        terminals = pf.get_airline_terminals(self.airlines, airline)
        if terminals is None:
            opts = '/'.join(self.terminals) + '/CARGO'
            ans = simpledialog.askstring("Airline missing", f"'{airline}' missing in db.\nTerminal ({opts}):", parent=self)
            entered = (ans or self.terminals[0]).strip().upper(); self.airlines[airline] = entered
            terminals = [entered]
        if terminals == ['CARGO']:
            pool = {i: d for i, d in pks.items() if d.get('schengen') == 'cargo' and i not in occ and (d.get('max_wingspan') or 999) >= (ws or 0)}
            return pool, 'CARGO', f"CARGO {airline}", False
        active = [term_over] if term_over in self.terminals else terminals
        ews, esch = ws or 0, sch if sch is not None else True
        for t in active:
            pool = pf.filter_parkings(pks, t, airline, ews, esch, occ, dedicated_map=self.dedicated_airline_map)
            if pool: return pool, t, airline, False
        for t in self.terminals:
            if t in active: continue
            pool = pf.filter_parkings(pks, t, airline, ews, esch, occ, dedicated_map=self.dedicated_airline_map)
            if pool: return pool, t, f"{airline} fallback→{t}", True
        return {}, self.terminals[0], f"{airline} fallback→{self.terminals[0]}", True

    # results table

    def _populate_table(self, dm, sch, aws, fallback=False):
        for r in self.tree.get_children(): self.tree.delete(r)
        self.all_sorted = []
        if not dm: self._clear_info(); return
        pref = 'schengen_only' if sch else 'non_schengen_only'
        self.all_sorted = sorted(dm, key=lambda p: pf._sort_key(p, dm[p], pref, sch))
        for i in self.all_sorted:
            d = dm[i]
            ws, rem, exc, st = d.get('max_wingspan'), d.get('remote', False), d.get('excludes', []), d.get('schengen', 'mixed')
            fit = aws and ws == aws
            tag = 'perfect' if fit else ('fallbk' if fallback else ('remote' if rem else 'gate'))
            self.tree.insert('', 'end', iid=i, values=(i, (f"{ws}m★" if fit else f"{ws}m") if ws else "?", 'Remote' if rem else 'Gate', pf.SCHENGEN_LABELS.get(st, st), d.get('max_acft', '?'), ', '.join(exc) if exc else '—'), tags=(tag,))
        if self.all_sorted: self.tree.selection_set(self.all_sorted[0]); self.tree.focus(self.all_sorted[0]); self.tree.see(self.all_sorted[0])

    # selection

    def _on_stand_select(self, _=None):
        sel = self.tree.selection()
        if not sel: return
        i = sel[0]; self.selected_stand = i
        self.assign_btn.config(state=tk.NORMAL, text=f"Assign Stand  {i}  ↵"); self._show_stand_info(i)

    def _lookup_stand(self):
        i = self.v_stand_search.get().strip().upper()
        if not i: return
        if i not in self.parkings: self._log(f"Stand '{i}' not found", 'warn'); self._clear_info(); return
        if self.tree.exists(i): self.tree.selection_set(i); self.tree.see(i)
        self._show_stand_info(i); self._log(f"Info stand {i}", 'info')

    def _show_stand_info(self, i):
        d = self.parkings.get(i)
        if not d: self._clear_info(); return
        ws, rem, st, term, exc, mac = d.get('max_wingspan'), d.get('remote', False), d.get('schengen', 'mixed'), d.get('terminal', '?'), d.get('excludes', []), d.get('max_acft', '?')
        occ = i in self.occupied
        self._info_lbl['Stand'].config(text=i, fg=C['accent']); self._info_lbl['Terminal'].config(text=term, fg=C['fg'])
        self._info_lbl['Tipo'].config(text='Remote' if rem else 'Gate', fg=C['orange'] if rem else '#a5d6a7')
        self._info_lbl['Max WS'].config(text=f"{ws} m" if ws else "?", fg=C['fg'])
        self._info_lbl['Max Acft'].config(text=str(mac), fg=C['fg']); self._info_lbl['Zona'].config(text=pf.SCHENGEN_LABELS.get(st, st), fg=C['fg_dim'])
        self._info_lbl['Excluye'].config(text=', '.join(exc) if exc else '—', fg=C['orange'] if exc else C['fg_dim'])
        self._info_lbl['Estado'].config(text="OCCUPIED" if occ else "Free", fg=C['red'] if occ else C['green'])

        air, aws, sch = self.v_airline.get().strip().upper(), self.acft_ws, self.sch_bool
        def _ok(t): return (t, C['green'])
        def _wn(t): return (t, C['orange'])
        def _na(): return ('—', C['fg_dim'])

        if aws and ws: wr = _ok("★ perfect" if aws == ws else f"✓ fits ({aws}m ≤ {ws}m)") if aws <= ws else _wn(f"✗ too big ({aws}m > {ws}m)")
        else: wr = _ok("✓ no limit") if aws and ws is None else _na()
        sr = _ok("✓ OK") if (air or aws) and pf.schengen_ok(d, sch) else (_wn(f"✗ zone {pf.SCHENGEN_LABELS.get(st, st)}") if (air or aws) else _na())
        al_ts = pf.get_airline_terminals(self.airlines, air) if air else None
        tr = _ok(f"✓ {term}") if al_ts and (term in al_ts or 'CARGO' in al_ts) else (_wn(f"✗ {air} → {'/'.join(al_ts)}") if al_ts else _na())
        cat_airlines = {}
        for a, c in self.dedicated_airline_map.items():
            cat_airlines.setdefault(c, set()).add(a)
        if st in cat_airlines:
            allowed = cat_airlines[st]
            dr = _ok("✓ yours") if air in allowed else _wn(f"✗ only {'/'.join(sorted(allowed))}")
        else:
            dr = _ok("✓ no restriction") if air else _na()
        for k, (t, c) in [('ws', wr), ('sch', sr), ('term', tr), ('ded', dr)]: self._suit_rows[k].config(text=t, fg=c)

    def _clear_info(self):
        for v in self._info_lbl.values(): v.config(text='—', fg=C['fg_dim'])
        for v in self._suit_rows.values(): v.config(text='—', fg=C['fg_dim'])

    # assign logic

    def _assign_stand(self):
        if not self.selected_stand: return
        i = self.selected_stand; d = self.parkings.get(i, {}); excs = [ex for ex in d.get('excludes', []) if ex not in self.occupied]
        cs = self.current_cs or self.v_callsign.get().strip().upper() or '—'

        if cs != '—':
            for r in self.assignments:
                if r['cs'] == cs and r['status'] in ('ASIGNADO', 'ASIGNADO(auto)', 'PRE-ASIGNADO'):
                    old = r['stand']
                    if old != i:
                        self.occupied.discard(old); self.occupied_by.pop(old, None)
                        for ex in self.parkings.get(old, {}).get('excludes', []): self.occupied.discard(ex)
                        self._log(f"[RE] {cs}: old stand {old} released", 'warn'); r['status'] = 'REPLACED'; self.preassigned.pop(cs, None)
                    break

        self.occupied.add(i)
        for ex in d.get('excludes', []): self.occupied.add(ex)
        air, acft, dep = self.v_airline.get().strip().upper(), self.v_aircraft.get().strip().upper(), self.v_origin.get().strip().upper()
        self.occupied_by[i] = {'cs': cs, 'acft': acft, 'airline': air}
        term = pf.get_airline_terminal(self.airlines, air) or d.get('terminal', self.terminals[0])
        self._strip_update(cs, air, acft, dep, i, "SCHENGEN" if self.sch_bool else "NON-SCHENGEN", term)

        for it in list(self.tree.get_children()):
            if it in ({i} | set(d.get('excludes', []))): self.tree.delete(it)

        self.assign_btn.config(state=tk.DISABLED, text="Assign Stand  ↵"); self.selected_stand = ''; self._update_occupied(); self._clear_info()
        blkd, assm = f"  (blocked: {', '.join(excs)})" if excs else "", True
        if self.aurora.connected and cs != '—':
            pos = self.aurora.get_traffic_position(cs); assm = bool(pos.get('assumed_station', '').strip()) if pos else True

        if self.aurora.connected and cs != '—' and assm:
            ok, det = self.aurora.assign_gate(cs, i); self._log(f"[OK] {cs} → Stand {i}{blkd}", 'ok')
            self._log(f"Aurora: {cs} gate {i} {'set' if ok else 'fail: '+det}", 'ok' if ok else 'warn'); self._record_assignment(cs, air, acft, dep, i, 'ASIGNADO')
        elif self.aurora.connected and cs != '—' and not assm:
            self.preassigned[cs] = {'stand': i, 'airline': air, 'aircraft': acft, 'origin': dep, 'time': datetime.datetime.now().strftime('%H:%M:%S')}
            self._log(f"[PRE] {cs} → Stand {i}{blkd} (waiting assumption)", 'warn'); self._record_assignment(cs, air, acft, dep, i, 'PRE-ASIGNADO')
        else: self._log(f"[OK] {cs} → Stand {i}{blkd}", 'ok'); self._record_assignment(cs, air, acft, dep, i, 'ASIGNADO')
        self._refresh_assignments_panel(); self._refresh_occupied_panel()

    # helpers

    def _update_occupied(self):
        if self.occupied:
            occ = sorted(self.occupied, key=lambda x: (pf.get_numeric_id(x), x))
            self.occ_label.config(text='  '.join(occ))
        else: self.occ_label.config(text='—')

    def _sync_occupied_aurora(self):
        # get busy gates from aurora
        if not self.aurora.connected: self._log("Aurora disconnected", 'warn'); return
        self._log("Querying Aurora for occupied gates…", 'info')
        def _do():
            gs = self.aurora.get_occupied_gates(); self.after(0, lambda: self._apply_aurora_gates(gs))
        threading.Thread(target=_do, daemon=True).start()

    def _apply_aurora_gates(self, gs):
        if not gs: self._log("Aurora: no traffic on ground with gate", 'warn'); return
        add = []
        for g, cs in gs.items():
            g = g.strip().upper()
            if g not in self.occupied:
                self.occupied.add(g); self.occupied_by[g] = {'cs': cs, 'acft': '', 'airline': callsign_to_airline(cs) or ''}; add.append(f"{g}({cs})")
        self._update_occupied(); self._refresh_occupied_panel()
        for it in list(self.tree.get_children()):
            if it in self.occupied: self.tree.delete(it)
        if add: self._log(f"Sync Aurora: {len(add)} gates → {', '.join(add)}", 'ok')

    def _clear_occupied(self):
        self.occupied.clear(); self.occupied_by.clear(); self._update_occupied(); self._refresh_occupied_panel(); self._log("All stands cleared", 'info')

    def _release_dialog(self):
        s = simpledialog.askstring("Release stand", "Stand ID:", parent=self)
        if not s: return
        s = s.strip().upper()
        if s in self.occupied:
            self.occupied.discard(s); self.occupied_by.pop(s, None); self._update_occupied(); self._log(f"Released: {s}", 'info')
            if self._occ_win and self._occ_win.winfo_exists(): self._refresh_occupied_panel()
        else: self._log(f"{s} not occupied", 'warn')

    def _open_occupied_panel(self): occupied_dialog.open(self)
    def _refresh_occupied_panel(self): occupied_dialog.refresh(self)

    def _log(self, m, l='info'):
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        self.log_box.config(state=tk.NORMAL); self.log_box.insert(tk.END, f"{ts}  {m}\n", l); self.log_box.see(tk.END); self.log_box.config(state=tk.DISABLED)

    def _record_assignment(self, cs, air, acft, dep, st, stat):
        self.assignments.append({'cs': cs, 'airline': air, 'aircraft': acft, 'origin': dep, 'stand': st, 'status': stat, 'time': datetime.datetime.now().strftime('%H:%M:%S')})

    def _open_assignments_panel(self): assignments_dialog.open(self)
    def _refresh_assignments_panel(self): assignments_dialog.refresh(self)

    # auto poll logic

    def _poll_preassigned(self):
        if not self.preassigned or not self.aurora.connected: return
        for cs, i in list(self.preassigned.items()):
            pos = self.aurora.get_traffic_position(cs)
            if pos and pos.get('assumed_station', '').strip():
                st = i['stand']; ok, det = self.aurora.assign_gate(cs, st)
                if ok: self.after(0, lambda c=cs, s=st: (self._log(f"[AUTO] {c} assumed → gate {s}", 'ok'), self._promote_preassigned(c)))

    def _promote_preassigned(self, cs):
        if cs in self.preassigned:
            self.preassigned.pop(cs)
            for a in self.assignments:
                if a['cs'] == cs and a['status'] == 'PRE-ASIGNADO': a['status'] = 'ASIGNADO (auto)'
            self._refresh_assignments_panel()

    def _on_auto_toggle(self):
        if self._auto_var.get():
            if not self.aurora.connected: self._log("Needs Aurora", 'warn'); self._auto_var.set(False); return
            self.auto_cb.config(fg=C['green']); self._log(f"Auto-refresh ON ({self.POLL_MS//1000}s)", 'info'); self._poll()
        else: self.auto_cb.config(fg=C['fg_dim']); self._stop_poll(); self._log("Auto-refresh OFF", 'info')

    def _poll(self):
        if not self._auto_var.get() or not self.aurora.connected: return
        def _do():
            cs = self.aurora.get_selected_callsign(); self.after(0, lambda: self._handle_poll(cs)); self._poll_preassigned()
        threading.Thread(target=_do, daemon=True).start()
        self._poll_job = self.after(self.POLL_MS, self._poll)

    def _handle_poll(self, cs):
        if not cs or cs == self._last_polled: return
        self._last_polled = cs; fp = self.aurora.get_flight_plan(cs)
        if not fp: return
        air, acft, dep = callsign_to_airline(cs) or '', fp.get('aircraft', ''), fp.get('departure', '')
        if not air and not acft: return
        self._ga_forced = False; self.v_callsign.set(cs); self.v_airline.set(air); self.v_aircraft.set(acft); self.v_origin.set(dep)
        self._log(f"Auto: {cs} → {air} {acft}", 'info'); self._run_query(cs, air or None, acft or None, dep or None)

    def _stop_poll(self):
        if self._poll_job: self.after_cancel(self._poll_job); self._poll_job = None

    def _on_close(self): self._stop_poll(); self.aurora.disconnect(); self.destroy()
