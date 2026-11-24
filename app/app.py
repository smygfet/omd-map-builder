# OMD Map Builder - window. Lists your Map Maker maps, builds and installs them into Orcs Must Die! Deathtrap.
import hashlib, http.server, json, os, re, queue, shutil, socketserver, subprocess, sys, threading, time, traceback, urllib.parse, webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import builder as B
import friendpack
import srchash

# the Map Maker's war-room colours: walnut panels, parchment text, brass accents
BG, PANEL, RAISED, LINE = "#17140f", "#241b13", "#33271b", "#4a3a28"
FG, MUTED, ACCENT, ACCENT_HI = "#efe3c6", "#b4a281", "#d9a648", "#e9c06a"
BAD, OK, WARN, LOGBG = "#e0533f", "#86c062", "#e8c34a", "#100d09"
TITLE_FONT, BODY = ("Georgia", 20, "bold"), "Segoe UI"
SETTINGS = os.path.join(B.DATA, "settings.json")
FROZEN = getattr(sys, "frozen", False)
UE_PY = r"C:\Program Files\Epic Games\UE_5.3\Engine\Binaries\ThirdParty\Python3\Win64\python.exe"
BUILD_SCRIPT = os.path.join(srchash.ROOT, "tools", "build_exe_nogame2.py")
JOBS = os.path.join(srchash.ROOT, "jobs")
SHARE = os.path.join(srchash.ROOT, "share")
SHARE_MAPS = os.path.join(SHARE, "maps")                  # map files for friends who have OMD Map Builder
PACK = os.path.join(SHARE, "OMD_VS_mods.zip")             # ready-to-play pack for friends who don't


def file_hash(f):
    try: return hashlib.sha1(open(f, "rb").read()).hexdigest()[:16]
    except OSError: return None


def rev_of(m):
    r = m.get("rev")
    return r if isinstance(r, int) and r > 0 else 0


def reveal(path):
    """Opens Explorer with the file selected."""
    try: subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    except OSError: os.startfile(os.path.dirname(path))


def built_hash():
    try: return open(os.path.join(B.HERE, "version.txt")).read().strip()
    except OSError: return None


def python_for_tools():
    """The Python that builds the exe and runs helper jobs (Unreal's bundled one has PyInstaller installed)."""
    if os.path.exists(UE_PY): return UE_PY
    return shutil.which("python") or shutil.which("py")


def load_settings():
    try: return json.load(open(SETTINGS, encoding="utf-8"))
    except (OSError, ValueError): return {}


def save_settings(s):
    os.makedirs(B.DATA, exist_ok=True); json.dump(s, open(SETTINGS, "w", encoding="utf-8"), indent=1)


class WebServer(threading.Thread):
    """Serves the Map Maker at http://127.0.0.1:<port>/omd/ - its Save goes straight into the maps folder and its
    Build button runs the same build as the window."""
    def __init__(self, app):
        super().__init__(daemon=True); self.app = app
        page = open(os.path.join(B.HERE, "mapmaker.html"), "rb").read()
        A = app
        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def reply(self, code, body, ctype="application/json"):
                if isinstance(body, (dict, list)): body = json.dumps(body).encode()
                self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(body)
            def do_GET(self):
                u = urllib.parse.urlparse(self.path)
                if u.path in ("/omd", "/omd/", "/omd/index.html"): return self.reply(200, page, "text/html; charset=utf-8")
                if u.path == "/omd/log":
                    n = int(urllib.parse.parse_qs(u.query).get("from", ["0"])[0]); lines = list(A.lines)
                    return self.reply(200, {"lines": lines[n:], "next": len(lines), "busy": A.busy, "ok": A.last_ok})
                if u.path == "/omd/map":                    # 'Open Map Maker' with a map selected: the Map Maker loads this file
                    f = os.path.basename(urllib.parse.parse_qs(u.query).get("f", [""])[0])
                    for m in list(getattr(A, "maps", [])):
                        if os.path.basename(m["_file"]) == f and os.path.exists(m["_file"]):
                            return self.reply(200, open(m["_file"], "rb").read())
                    return self.reply(404, {"error": "no map " + f})
                self.reply(404, {"error": "not found"})
            def do_POST(self):
                u = urllib.parse.urlparse(self.path)
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                if u.path == "/omd/save":
                    name = os.path.basename(urllib.parse.parse_qs(u.query).get("name", ["map.omdmap.json"])[0])
                    if not name.endswith(".omdmap.json"): name = name.rsplit(".", 1)[0] + ".omdmap.json"
                    try: json.loads(body.decode("utf-8"))
                    except ValueError: return self.reply(400, {"ok": False, "error": "not a map"})
                    os.makedirs(B.MAPS, exist_ok=True); open(os.path.join(B.MAPS, name), "wb").write(body)
                    A.settings.get("ignored", {}).pop(name, None)
                    A.q.put((A.refresh,)); A.q.put("saved from the Map Maker: " + name)
                    return self.reply(200, {"ok": True})
                if u.path == "/omd/pack":
                    if A.busy: return self.reply(200, {"ok": False, "error": "A build is already running"})
                    A.busy = True
                    A.q.put((A.pack_from_web,))
                    return self.reply(200, {"ok": True})
                if u.path == "/omd/build":
                    if A.busy: return self.reply(200, {"ok": False, "error": "A build is already running"})
                    A.busy = True                                   # claimed here; the window thread starts it
                    A.q.put((lambda: A.build(from_web=True),))
                    return self.reply(200, {"ok": True})
                self.reply(404, {"error": "not found"})
        class S(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads = True
        for port in (8765, 8766, 8767, 0):
            try: self.httpd = S(("127.0.0.1", port), H); break
            except OSError: continue
        self.url = "http://127.0.0.1:%d/omd/" % self.httpd.server_address[1]

    def run(self): self.httpd.serve_forever()


class JobRunner(threading.Thread):
    """While the app is open it runs helper jobs: a *.job file in Claud OMD\\jobs holds the path of a script, which is
    run with the tools Python. (This used to need the Unreal editor open.)"""
    def __init__(self, app):
        super().__init__(daemon=True); self.app = app

    def run(self):
        logf = os.path.join(srchash.ROOT, "notes", "jobs_log.txt")
        while True:
            try:
                for f in sorted(os.listdir(JOBS)) if os.path.isdir(JOBS) else []:
                    if not f.endswith(".job"): continue
                    job = os.path.join(JOBS, f); script = open(job, encoding="utf-8").read().strip().strip('"')
                    os.replace(job, job + ".done")
                    py = python_for_tools()
                    with open(logf, "a", encoding="utf-8") as L: L.write("%s app runs %s -> %s\n" % (time.strftime("%H:%M:%S"), f, script))
                    if py and os.path.exists(script):
                        subprocess.Popen([py, script], cwd=os.path.dirname(script), creationflags=B.NO_WINDOW)
            except Exception as e:
                try: open(logf, "a").write("job error %r\n" % e)
                except OSError: pass
            time.sleep(3)


class App:
    def __init__(self, root):
        self.root = root; self.q = queue.Queue(); self.busy = False; self.lines = []; self.last_ok = None
        self.settings = load_settings()
        root.title("OMD Map Builder"); root.geometry("1060x760"); root.minsize(880, 600); root.configure(bg=BG)
        st = ttk.Style(root); st.theme_use("clam")
        st.configure(".", background=BG, foreground=FG, fieldbackground=PANEL, font=(BODY, 10))
        st.configure("TButton", background=RAISED, foreground=FG, bordercolor=LINE, lightcolor=RAISED, darkcolor=RAISED, borderwidth=1, padding=(12, 6))
        st.map("TButton", background=[("active", "#433324"), ("disabled", PANEL)], foreground=[("disabled", "#6e624f")])
        st.configure("Big.TButton", background=ACCENT, foreground="#1d1408", bordercolor=ACCENT, lightcolor=ACCENT, darkcolor=ACCENT, font=(BODY, 11, "bold"), padding=(20, 9))
        st.map("Big.TButton", background=[("active", ACCENT_HI), ("disabled", "#5a4a2a")])
        st.configure("Accent.TButton", background=PANEL, foreground=ACCENT_HI, bordercolor=ACCENT, font=(BODY, 10, "bold"))
        st.map("Accent.TButton", background=[("active", RAISED)])
        st.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=FG, rowheight=30, borderwidth=1, bordercolor=LINE,
                     lightcolor=LINE, darkcolor=LINE, font=(BODY, 10))
        st.configure("Treeview.Heading", background=RAISED, foreground=MUTED, relief="flat", font=(BODY, 9, "bold"), padding=(6, 5))
        st.map("Treeview.Heading", background=[("active", RAISED)])
        st.map("Treeview", background=[("selected", "#4d3b26")], foreground=[("selected", FG)])
        st.configure("TCheckbutton", background=PANEL, foreground=FG)
        st.map("TCheckbutton", background=[("active", PANEL)])
        for sbs in ("TScrollbar", "Vertical.TScrollbar"):
            st.configure(sbs, background=RAISED, troughcolor=PANEL, bordercolor=PANEL, lightcolor=RAISED, darkcolor=RAISED, arrowcolor=MUTED, gripcount=0)
        st.map("Vertical.TScrollbar", background=[("active", "#433324")])

        # ---- header: name, game folder, Map Maker ----
        top = tk.Frame(root, bg=BG); top.pack(fill="x", padx=20, pady=(16, 10))
        tk.Label(top, text="OMD Map Builder", bg=BG, fg=ACCENT_HI, font=TITLE_FONT).pack(side="left")
        tk.Label(top, text="custom missions for Orcs Must Die! Deathtrap", bg=BG, fg=MUTED, font=(BODY, 10)).pack(side="left", padx=(12, 0), pady=(10, 0))
        self.web = WebServer(self); self.web.start()
        ttk.Button(top, text="Open Map Maker", style="Big.TButton", command=self.open_map_maker).pack(side="right")
        tk.Frame(root, bg=LINE, height=1).pack(fill="x")

        # ---- bottom bar (every page): Build & install, status, the log ----
        bot = tk.Frame(root, bg=PANEL); bot.pack(side="bottom", fill="x")
        tk.Frame(bot, bg=LINE, height=1).pack(fill="x")
        barrow = tk.Frame(bot, bg=PANEL); barrow.pack(fill="x", padx=20, pady=10)
        self.build_btn = ttk.Button(barrow, text="Build & install", style="Big.TButton", command=self.build)
        self.build_btn.pack(side="left")
        self.status = tk.Label(barrow, text="", bg=PANEL, fg=FG, font=(BODY, 10, "bold")); self.status.pack(side="left", padx=(16, 0))
        self.activity = tk.Label(barrow, text="", bg=PANEL, fg=MUTED, anchor="w"); self.activity.pack(side="left", fill="x", expand=True, padx=(12, 8))
        self.log_btn = ttk.Button(barrow, text="Show log", command=self.toggle_log); self.log_btn.pack(side="right")
        self.logwrap = tk.Frame(bot, bg=PANEL)
        self.logbox = tk.Text(self.logwrap, bg=LOGBG, fg=FG, insertbackground=FG, relief="flat", font=("Consolas", 9), height=11, wrap="word",
                              padx=10, pady=8, highlightthickness=0)
        sb = ttk.Scrollbar(self.logwrap, orient="vertical", command=self.logbox.yview); self.logbox.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); self.logbox.pack(fill="both", expand=True)
        self.logbox.tag_configure("bad", foreground=BAD); self.logbox.tag_configure("ok", foreground=OK)
        self.log_shown = False

        # ---- body: sidebar + pages ----
        body = tk.Frame(root, bg=BG); body.pack(fill="both", expand=True)
        side = tk.Frame(body, bg=PANEL, width=170); side.pack(side="left", fill="y"); side.pack_propagate(False)
        tk.Frame(body, bg=LINE, width=1).pack(side="left", fill="y")
        self.pages_box = tk.Frame(body, bg=BG); self.pages_box.pack(side="left", fill="both", expand=True)
        self.pages, self.nav = {}, {}
        tk.Frame(side, bg=PANEL, height=14).pack()
        for key, label, sub in (("maps", "Maps", "your Map Maker maps"), ("mods", "Mods", "extras in the game"),
                                ("share", "Share", "send to a friend"), ("game", "Game", "folder and settings")):
            item = tk.Frame(side, bg=PANEL, cursor="hand2"); item.pack(fill="x")
            bar = tk.Frame(item, bg=PANEL, width=4); bar.pack(side="left", fill="y")
            txt = tk.Frame(item, bg=PANEL); txt.pack(side="left", fill="x", padx=(14, 8), pady=8)
            t1 = tk.Label(txt, text=label, bg=PANEL, fg=FG, font=(BODY, 12, "bold"), anchor="w"); t1.pack(fill="x")
            t2 = tk.Label(txt, text=sub, bg=PANEL, fg=MUTED, font=(BODY, 9), anchor="w"); t2.pack(fill="x")
            for w in (item, bar, txt, t1, t2): w.bind("<Button-1>", lambda e, k=key: self.show_page(k))
            self.nav[key] = (item, bar, txt, t1, t2)
            self.pages[key] = tk.Frame(self.pages_box, bg=BG)
        self.version_lbl = tk.Label(side, text="", bg=PANEL, fg="#7d6f57", font=(BODY, 8), anchor="w", justify="left")
        self.version_lbl.pack(side="bottom", fill="x", padx=14, pady=10)

        self.skip_intro = tk.BooleanVar(value=self.settings.get("skip_intro", True))
        self.start_after = tk.BooleanVar(value=self.settings.get("start_after", False))
        self.build_maps_page(self.pages["maps"])
        self.build_mods_page(self.pages["mods"])
        self.build_share_page(self.pages["share"])
        self.build_game_page(self.pages["game"])
        self.show_page("maps")
        self.version_lbl.configure(text="app version\n%s" % ((built_hash() or "dev")[:12]))

        B._log_cb = lambda line: (self.lines.append(line), self.q.put(line))
        self.find_game(); self.refresh(); self.sync_mods(); self.root.after(100, self.pump)
        JobRunner(self).start()
        self.root.after(800, self.check_update)

    # ----- pages -----
    def page_head(self, parent, title, text):
        h = tk.Frame(parent, bg=BG); h.pack(fill="x", padx=24, pady=(18, 10))
        tk.Label(h, text=title, bg=BG, fg=FG, font=("Georgia", 16, "bold"), anchor="w").pack(fill="x")
        tk.Label(h, text=text, bg=BG, fg=MUTED, font=(BODY, 10), anchor="w", justify="left", wraplength=760).pack(fill="x", pady=(2, 0))
        return h

    def card(self, parent, pady=(0, 8)):
        c = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=LINE); c.pack(fill="x", padx=24, pady=pady)
        inner = tk.Frame(c, bg=PANEL); inner.pack(fill="x", padx=16, pady=11)
        return inner

    def scroll_area(self, parent):
        """a vertically scrolling frame filling `parent` (mouse wheel works while the pointer is over it)"""
        wrap = tk.Frame(parent, bg=BG); wrap.pack(fill="both", expand=True)
        cv = tk.Canvas(wrap, bg=BG, highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=cv.yview); cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); cv.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(cv, bg=BG); win = cv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>", lambda e: cv.itemconfigure(win, width=e.width))

        def wheel(e):
            w = cv.winfo_containing(e.x_root, e.y_root)
            if w is None or not str(w).startswith(str(wrap)): return
            if inner.winfo_height() <= cv.winfo_height(): return
            if getattr(e, "num", 0) == 4: d = -1
            elif getattr(e, "num", 0) == 5: d = 1
            else: d = -1 if e.delta > 0 else 1
            cv.yview_scroll(d * 3, "units")
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"): cv.bind_all(ev, wheel, add="+")
        return inner

    def pill(self, parent, text, color):
        return tk.Label(parent, text=" %s " % text, bg=color, fg="#1d1408", font=(BODY, 9, "bold"), padx=4, pady=1)

    def show_page(self, key):
        for k, f in self.pages.items(): f.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        for k, (item, bar, txt, t1, t2) in self.nav.items():
            on = k == key; bgc = RAISED if on else PANEL
            for w in (item, txt, t1, t2): w.configure(bg=bgc)
            bar.configure(bg=ACCENT if on else PANEL); t1.configure(fg=ACCENT_HI if on else FG)
        self.page = key
        if key == "mods": self.sync_mods()
        if key == "share": self.update_share_sel()

    def toggle_log(self, show=None):
        show = (not self.log_shown) if show is None else show
        if show and not self.log_shown: self.logwrap.pack(fill="both", padx=20, pady=(0, 12))
        if not show and self.log_shown: self.logwrap.pack_forget()
        self.log_shown = show; self.log_btn.configure(text="Hide log" if show else "Show log")

    def build_maps_page(self, pg):
        self.page_head(pg, "Maps", "Every map you save in the Map Maker shows up here. Build & install puts all of them into the game; "
                       "they turn up in the run's mission choice.")
        box = tk.Frame(pg, bg=BG); box.pack(fill="both", expand=True, padx=24)
        cols = ("size", "often", "version", "status")
        self.tree = ttk.Treeview(box, columns=cols, show="tree headings", selectmode="extended")
        for c_, t_ in (("#0", "Map"), ("size", "Size"), ("often", "Show often"), ("version", "Version"), ("status", "Status")): self.tree.heading(c_, text=t_)
        self.tree.column("#0", width=250); self.tree.column("size", width=80, anchor="center"); self.tree.column("often", width=90, anchor="center")
        self.tree.column("version", width=70, anchor="center"); self.tree.column("status", width=300)
        self.tree.tag_configure("bad", foreground=BAD); self.tree.tag_configure("ok", foreground=FG); self.tree.tag_configure("changed", foreground=ACCENT_HI)
        self.tree.tag_configure("odd", background="#2a2016")
        sb = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.update_share_sel())
        row = tk.Frame(pg, bg=BG); row.pack(fill="x", padx=24, pady=(10, 16))
        ttk.Button(row, text="Add map file...", command=self.add_map).pack(side="left")
        ttk.Button(row, text="Show often on/off", command=self.toggle_often).pack(side="left", padx=6)
        ttk.Button(row, text="Remove selected", command=self.remove_selected).pack(side="left")
        ttk.Button(row, text="Refresh", command=self.refresh).pack(side="right")
        ttk.Button(row, text="Open maps folder", command=lambda: os.startfile(B.MAPS)).pack(side="right", padx=6)

    def build_mods_page(self, pg):
        pg = self.scroll_area(pg)
        self.page_head(pg, "Mods", "Extras that go into the game alongside your maps. Switch a mod off to leave it out of the game "
                       "(and out of the ready-to-play pack you send a friend). Close the game before switching.")
        self.mod_cards = {}
        for m in B.MODS:
            c = self.card(pg)
            row = tk.Frame(c, bg=PANEL); row.pack(fill="x")
            tk.Label(row, text=m["name"], bg=PANEL, fg=FG, font=(BODY, 12, "bold")).pack(side="left")
            pl = self.pill(row, "", MUTED); pl.pack(side="left", padx=10)
            btn = ttk.Button(row, text="", command=lambda m=m: self.toggle_mod(m)); btn.pack(side="right")
            tk.Label(c, text=m.get("desc", ""), bg=PANEL, fg=MUTED, anchor="w", justify="left", wraplength=640).pack(fill="x", pady=(6, 0))
            self.mod_cards[m["id"]] = (pl, btn)
            if m["id"] == "endless": self.endless_panel(c)
            if m["id"] == "giantflip": self.giantflip_panel(c)
        tk.Label(pg, text="Come with your maps (put in automatically when you build)", bg=BG, fg=MUTED, font=(BODY, 10, "bold"), anchor="w").pack(fill="x", padx=24, pady=(6, 6))
        self.auto_cards = {}
        for key, name, desc in (("vs", "VS referee", "Keeps score in VS maps: sides, sending enemies, curses, endless waves and the map's VS rules."),
                                ("bk", "Barricade walls", "Makes the wooden barricade walls breakable, and lets orcs attack barricades on normal custom maps."),
                                ("ue4ss", "UE4SS (mod loader)", "Runs the script mods above. Without it maps still play, but VS scoring and barricade walls don't work.")):
            c = self.card(pg)
            row = tk.Frame(c, bg=PANEL); row.pack(fill="x")
            tk.Label(row, text=name, bg=PANEL, fg=FG, font=(BODY, 11, "bold")).pack(side="left")
            pl = self.pill(row, "", MUTED); pl.pack(side="left", padx=10)
            tk.Label(c, text=desc, bg=PANEL, fg=MUTED, anchor="w", justify="left", wraplength=780).pack(fill="x", pady=(3, 0))
            self.auto_cards[key] = pl
        self.mod_note = tk.Label(pg, text="", bg=BG, fg=WARN, anchor="w"); self.mod_note.pack(fill="x", padx=24)

    def endless_panel(self, c):
        cur = B.endless_clean(self.settings.get("endless"))
        self.endless_vars = {}
        grid = tk.Frame(c, bg=PANEL); grid.pack(fill="x", pady=(10, 0))
        fields = (("last_wave", "Last wave (mission won)", 1), ("health", "Enemy health + % per wave", 1),
                  ("extra", "Extra enemies per wave", 0.25), ("max_alive", "Max enemies alive", 10),
                  ("from_wave", "Gets harder from wave", 1), (None, None, None),
                  ("newtypes", "New enemy types", None), ("random", "Random order", None),
                  ("starttypes", "Types from wave 1", 1), ("perwave", "New types per wave", 1),
                  ("newcount", "Count of each new type", 1), ("oldcount", "Count of each earlier type", 1))
        for i, (k, label, step) in enumerate(fields):
            if k is None: continue
            r_, c_ = i // 2, (i % 2) * 2
            v = tk.StringVar(value=str(cur[k])); self.endless_vars[k] = v
            if step is None:
                ttk.Checkbutton(grid, text=label, variable=v, onvalue="1", offvalue="0").grid(row=r_, column=c_, columnspan=2, sticky="w", pady=3)
                continue
            lo, hi = B.ENDLESS_LIMITS[k]
            tk.Label(grid, text=label, bg=PANEL, fg=FG, anchor="w").grid(row=r_, column=c_, sticky="w", padx=(0, 8), pady=3)
            ttk.Spinbox(grid, from_=lo, to=hi, increment=step, textvariable=v, width=7).grid(row=r_, column=c_ + 1, sticky="w", padx=(0, 28), pady=3)
        row = tk.Frame(c, bg=PANEL); row.pack(fill="x", pady=(8, 0))
        ttk.Button(row, text="Save settings", command=self.save_endless).pack(side="left")
        ttk.Button(row, text="Defaults", command=self.endless_defaults).pack(side="left", padx=6)
        tk.Label(row, text="Used from the next mission start. Changing the last wave rebuilds the mod (close the game first).",
                 bg=PANEL, fg=MUTED, anchor="w", justify="left", wraplength=430).pack(side="left", padx=8)

    def endless_defaults(self):
        for k, v in B.ENDLESS_DEFAULTS.items(): self.endless_vars[k].set(str(v))

    def save_endless(self):
        if not self.game: messagebox.showinfo("OMD Map Builder", "Set the game folder on the Game page first."); return
        raw = {k: v.get().replace(",", ".") for k, v in self.endless_vars.items()}
        try:
            s = B.endless_clean(raw)
            rebuild = s["last_wave"] != B.endless_built_waves()
            if rebuild and B.game_running(): raise RuntimeError("Close the game first: changing the last wave rebuilds the mod")
        except Exception as e:
            messagebox.showerror("OMD Map Builder", str(e)); return
        for k, v in s.items(): self.endless_vars[k].set(str(v))
        self.settings["endless"] = s; save_settings(self.settings)
        if rebuild:
            self.worker(lambda: B.endless_apply(self.game, s), "Endless mode saved. The missions now end at wave %d." % s["last_wave"])
        else:
            try: B.endless_apply(self.game, s); self.say("Endless mode settings saved (used from the next mission start).", "ok")
            except Exception as e: messagebox.showerror("OMD Map Builder", str(e))

    def giantflip_panel(self, c):
        cur = B.giantflip_clean(self.settings.get("giantflip"))
        self.gf_vars = {}
        grid = tk.Frame(c, bg=PANEL); grid.pack(fill="x", pady=(10, 0))
        tk.Label(grid, text="Throws up to", bg=PANEL, fg=FG, anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=3)
        v = tk.StringVar(value=B.GIANTFLIP_WEIGHTS[cur["max_weight"]]); self.gf_vars["max_weight"] = v
        ttk.Combobox(grid, values=B.GIANTFLIP_WEIGHTS, textvariable=v, state="readonly", width=12).grid(row=0, column=1, sticky="w", padx=(0, 28), pady=3)
        fields = (("light", "Light enemies %"), ("heavy", "Heavy enemies %"), ("veryheavy", "Very heavy enemies %"), ("immovable", "Bosses %"))
        for i, (k, label) in enumerate(fields):
            lo, hi = B.GIANTFLIP_LIMITS[k]
            v = tk.StringVar(value=str(cur[k])); self.gf_vars[k] = v
            r_, c_ = 1 + i // 2, (i % 2) * 2
            tk.Label(grid, text=label, bg=PANEL, fg=FG, anchor="w").grid(row=r_, column=c_, sticky="w", padx=(0, 8), pady=3)
            ttk.Spinbox(grid, from_=lo, to=hi, increment=5, textvariable=v, width=7).grid(row=r_, column=c_ + 1, sticky="w", padx=(0, 28), pady=3)
        row = tk.Frame(c, bg=PANEL); row.pack(fill="x", pady=(8, 0))
        ttk.Button(row, text="Save settings", command=self.save_giantflip).pack(side="left")
        ttk.Button(row, text="Defaults", command=self.giantflip_defaults).pack(side="left", padx=6)
        tk.Label(row, text="How far it throws each weight class (100 % = a light enemy's full throw). Picked up within 10 seconds, even mid-game.",
                 bg=PANEL, fg=MUTED, anchor="w", justify="left", wraplength=430).pack(side="left", padx=8)

    def giantflip_defaults(self):
        for k, v in B.GIANTFLIP_DEFAULTS.items():
            self.gf_vars[k].set(B.GIANTFLIP_WEIGHTS[v] if k == "max_weight" else str(v))

    def save_giantflip(self):
        if not self.game: messagebox.showinfo("OMD Map Builder", "Set the game folder on the Game page first."); return
        raw = {k: v.get().replace(",", ".") for k, v in self.gf_vars.items()}
        w = raw["max_weight"]
        raw["max_weight"] = B.GIANTFLIP_WEIGHTS.index(w) if w in B.GIANTFLIP_WEIGHTS else B.GIANTFLIP_DEFAULTS["max_weight"]
        try: s = B.giantflip_apply(self.game, raw)
        except Exception as e: messagebox.showerror("OMD Map Builder", str(e)); return
        for k, v in s.items(): self.gf_vars[k].set(B.GIANTFLIP_WEIGHTS[v] if k == "max_weight" else str(v))
        self.settings["giantflip"] = s; save_settings(self.settings)
        self.say("Giant Flip settings saved (the game picks them up within 10 seconds).", "ok")

    def build_share_page(self, pg):
        self.page_head(pg, "Share", "Two ways to get your maps to a friend, depending on whether they have OMD Map Builder too.")
        c = self.card(pg)
        tk.Label(c, text="Friend has OMD Map Builder", bg=PANEL, fg=FG, font=(BODY, 12, "bold"), anchor="w").pack(fill="x")
        tk.Label(c, text="Sends the map file itself. They add it with 'Add map file...', can change it in the Map Maker, and build it themselves.",
                 bg=PANEL, fg=MUTED, anchor="w", justify="left", wraplength=640).pack(fill="x", pady=(4, 10))
        row = tk.Frame(c, bg=PANEL); row.pack(fill="x")
        ttk.Button(row, text="Send the selected maps", style="Accent.TButton", command=self.share_maps).pack(side="left")
        self.share_sel = tk.Label(row, text="", bg=PANEL, fg=MUTED); self.share_sel.pack(side="left", padx=12)
        c = self.card(pg)
        tk.Label(c, text="Friend doesn't have it", bg=PANEL, fg=FG, font=(BODY, 12, "bold"), anchor="w").pack(fill="x")
        tk.Label(c, text="Makes a ready-to-play pack: all your built maps plus the mods, with install.bat and uninstall.bat. "
                         "It's also what you both need for a VS game. Builds your latest maps first if needed.",
                 bg=PANEL, fg=MUTED, anchor="w", justify="left", wraplength=640).pack(fill="x", pady=(4, 10))
        self.pack_btn = ttk.Button(c, text="Make a ready-to-play pack", style="Accent.TButton", command=self.share_pack)
        self.pack_btn.pack(anchor="w")
        tk.Label(pg, text="Files go to Claud OMD\\share. Explorer opens with the new file selected, ready to send.", bg=BG, fg=MUTED, anchor="w").pack(fill="x", padx=24, pady=(4, 0))

    def update_share_sel(self):
        if not hasattr(self, "share_sel"): return
        sel = [self.maps[int(i)].get("name", "?") for i in self.tree.selection()] if hasattr(self, "maps") else []
        self.share_sel.configure(text=("Selected: " + ", ".join(sel)) if sel else "Select maps on the Maps page first",
                                 fg=FG if sel else MUTED)

    def build_game_page(self, pg):
        self.page_head(pg, "Game", "Where the game is, and how your maps start.")
        c = self.card(pg)
        tk.Label(c, text="Game folder", bg=PANEL, fg=FG, font=(BODY, 11, "bold"), anchor="w").pack(fill="x")
        self.game_var = tk.StringVar()
        tk.Label(c, textvariable=self.game_var, bg=PANEL, fg=MUTED, anchor="w", justify="left", wraplength=640).pack(fill="x", pady=(4, 10))
        ttk.Button(c, text="Change game folder...", command=self.pick_game).pack(anchor="w")
        c = self.card(pg)
        ttk.Checkbutton(c, text="Skip the intro camera when a map starts", variable=self.skip_intro, command=self.store).pack(anchor="w")
        tk.Label(c, text="Takes effect at the next Build & install.", bg=PANEL, fg=MUTED, anchor="w").pack(fill="x", pady=(4, 0))
        ttk.Checkbutton(c, text="Start the game when Build & install is done", variable=self.start_after, command=self.store).pack(anchor="w", pady=(10, 0))
        tk.Label(c, text="Starts it through Steam (not when it is already running).", bg=PANEL, fg=MUTED, anchor="w").pack(fill="x", pady=(4, 0))
        c = self.card(pg)
        tk.Label(c, text="Take everything out", bg=PANEL, fg=FG, font=(BODY, 11, "bold"), anchor="w").pack(fill="x")
        tk.Label(c, text="Removes all custom maps from the game. Your map files stay here; build again to put them back.",
                 bg=PANEL, fg=MUTED, anchor="w", justify="left", wraplength=640).pack(fill="x", pady=(4, 10))
        row = tk.Frame(c, bg=PANEL); row.pack(fill="x")
        ttk.Button(row, text="Remove custom maps from the game", command=self.uninstall).pack(side="left")
        ttk.Button(row, text="Open logs folder", command=lambda: os.startfile(B.LOGS) if os.path.isdir(B.LOGS) else None).pack(side="right")

    # ----- self update -----
    def check_update(self):
        if not FROZEN or "--no-update" in sys.argv: return
        mine, now = built_hash(), srchash.source_hash()
        if not mine or mine == now or not os.path.exists(BUILD_SCRIPT) or not python_for_tools(): return
        self.say("A newer version of the app is ready - updating (about a minute, the app restarts by itself)...")
        self.build_btn.state(["disabled"]); self.busy = True
        def go():
            env = dict(os.environ, OMD_NO_COPY="1")
            r = subprocess.run([python_for_tools(), BUILD_SCRIPT], cwd=os.path.dirname(BUILD_SCRIPT), env=env,
                               capture_output=True, text=True, creationflags=B.NO_WINDOW)
            new = os.path.join(srchash.ROOT, "exe_build", "dist", "OMD Map Builder.exe")
            self.q.put((lambda: self.swap(new) if os.path.exists(new) and r.returncode == 0 else self.update_failed(),))
        threading.Thread(target=go, daemon=True).start()

    def update_failed(self):
        self.busy = False; self.build_btn.state(["!disabled"])
        self.say("Update failed, keeping this version (log: Claud OMD\\notes\\build_exe.txt)", "bad")

    def swap(self, new):
        me = sys.executable
        bat = os.path.join(B.DATA, "update.bat")
        spots = {os.path.normcase(me): me}             # update this copy plus the usual ones (app folder, Desktop)
        for d in (os.path.join(srchash.ROOT, "OMD Map Builder.exe"), os.path.join(os.path.expanduser("~"), "Desktop", "OMD Map Builder.exe")):
            if os.path.exists(d): spots[os.path.normcase(d)] = d
        lines = ['@echo off', 'timeout /t 2 /nobreak >nul'] + ['copy /y "%s" "%s" >nul' % (new, d) for d in spots.values()] + ['start "" "%s"' % me]
        open(bat, "w").write("\r\n".join(lines) + "\r\n")
        subprocess.Popen(["cmd", "/c", bat], creationflags=B.NO_WINDOW)
        self.root.destroy()

    # ----- helpers -----
    def store(self):
        self.settings["skip_intro"] = bool(self.skip_intro.get()); self.settings["start_after"] = bool(self.start_after.get()); save_settings(self.settings)

    def find_game(self):
        g = self.settings.get("game")
        if not (g and os.path.isdir(os.path.join(g, "OMDD", "Content", "Paks"))): g = B.find_game()
        self.game = g
        self.game_var.set(g if g else "Not found. Press 'Change game folder...' and pick the Orcs Must Die Deathtrap folder.")

    def pick_game(self):
        d = filedialog.askdirectory(title="Pick the 'Orcs Must Die Deathtrap' folder (it contains OMDD)")
        if not d: return
        d = os.path.normpath(d)
        if os.path.basename(d).upper() == "OMDD": d = os.path.dirname(d)
        if not os.path.isdir(os.path.join(d, "OMDD", "Content", "Paks")):
            messagebox.showerror("OMD Map Builder", "That folder does not contain OMDD\\Content\\Paks."); return
        self.settings["game"] = d; save_settings(self.settings); self.find_game(); self.sync_mods()

    def say(self, text, tag=None):
        self.logbox.insert("end", text + "\n", tag or ()); self.logbox.see("end")
        short = text.strip().splitlines()[-1] if text.strip() else ""
        self.activity.configure(text=short[:110], fg=BAD if tag == "bad" else OK if tag == "ok" else MUTED)
        if tag == "bad": self.toggle_log(True)

    def pump(self):
        try:
            while True:
                line = self.q.get_nowait()
                if isinstance(line, tuple): line[0]()
                else: self.say(line, "ok" if "DONE" in line else "bad" if ("FAILED" in line or "SKIPPED" in line) else None)
        except queue.Empty: pass
        self.root.after(100, self.pump)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        self.maps = B.collect_maps(self.settings.get("ignored", {}))
        often = set(self.settings.get("often", []))
        for m in self.maps: m["_often"] = m.get("id") in often
        built = self.settings.get("built", {})
        for i, m in enumerate(self.maps):
            size = "%d x %d" % (m.get("cols", 0), m.get("rows", 0)) if m.get("cols") else ""
            rev = rev_of(m); state = self.build_state(m)
            if m["_error"]: status, tag = "problem: " + m["_error"], "bad"
            elif state == "built": status, tag = "in the game", "ok"
            elif state == "changed":
                b = built.get(os.path.basename(m["_file"]), {}).get("rev")
                status, tag = "changed since the last build%s" % (" (game has v%d)" % b if b else ""), "changed"
            elif state == "unknown": status, tag = "ready", "ok"
            else: status, tag = "ready - not built yet", "changed"
            self.tree.insert("", "end", iid=str(i), text="  " + m.get("name", "?"), values=(size, "yes" if m["_often"] else "", "v%d" % rev if rev else "-", status), tags=(tag,) + (("odd",) if i % 2 else ()))
        n = sum(1 for m in self.maps if not m["_error"])
        self.status.configure(text="%d map%s ready" % (n, "" if n == 1 else "s"), fg=FG)
        if not self.maps: self.say("No maps yet. Press 'Open Map Maker', draw a map and press Save map: it lands in Downloads and shows up here.")
        self.update_share_sel()

    def add_map(self):
        for f in filedialog.askopenfilenames(title="Map Maker file", filetypes=[("Map Maker map", "*.omdmap.json *.omdshare.json"), ("JSON", "*.json")]):
            os.makedirs(B.MAPS, exist_ok=True)
            if f.endswith(".omdshare.json"):
                # a map shared by a friend (Name_v3.omdshare.json): file it under its map id, like the Map Maker saves it
                try: name = (re.sub(r"[^A-Za-z0-9]+", "_", str(json.load(open(f, encoding="utf-8")).get("name", "Map"))).strip("_") or "Map")[:32] + ".omdmap.json"
                except Exception: name = os.path.basename(f)[:-len(".omdshare.json")] + ".omdmap.json"
            else:
                name = os.path.basename(f) if f.endswith(".omdmap.json") else os.path.splitext(os.path.basename(f))[0] + ".omdmap.json"
            shutil.copyfile(f, os.path.join(B.MAPS, name))
        self.refresh()

    def remove_selected(self):
        sel = [self.maps[int(i)] for i in self.tree.selection()]
        if not sel: return
        if not messagebox.askyesno("OMD Map Builder", "Remove %s from the list?\nThe file goes to the 'removed' folder; the next build leaves it out." % ", ".join(m.get("name", "?") for m in sel)): return
        ign = dict(self.settings.get("ignored", {}))
        rem = os.path.join(B.MAPS, "removed"); os.makedirs(rem, exist_ok=True)
        for m in sel:
            ign[os.path.basename(m["_file"])] = time.time()
            shutil.move(m["_file"], os.path.join(rem, os.path.basename(m["_file"])))
        self.settings["ignored"] = ign; save_settings(self.settings); self.refresh()

    def toggle_often(self):
        sel = [self.maps[int(i)] for i in self.tree.selection()]
        if not sel: messagebox.showinfo("OMD Map Builder", "Select a map first. 'Show often' makes the game offer it in almost every mission choice, handy for testing. Build again after changing it."); return
        often = set(self.settings.get("often", []))
        for m in sel: often.symmetric_difference_update({m["id"]})
        self.settings["often"] = sorted(often); save_settings(self.settings); self.refresh()
        self.say("Show often changed. Press Build & install to apply it.")

    # ----- actions -----
    def sync_mods(self):
        missing = []
        for m in B.MODS:
            st = B.mod_state(self.game, m) if self.game else None
            pl, btn = self.mod_cards[m["id"]]
            if st is None:
                pl.configure(text=" not on this PC ", bg="#6e624f"); btn.configure(text="Turn on"); btn.state(["disabled"]); missing.append(m["name"])
            else:
                pl.configure(text=" ON " if st else " OFF ", bg=OK if st else "#8a7a60")
                btn.configure(text="Turn off" if st else "Turn on"); btn.state(["!disabled"])
        mods = B.ue4ss_mods(self.game) if self.game else ""
        has = lambda d: bool(mods) and os.path.exists(os.path.join(mods, d, "enabled.txt"))
        ue = bool(self.game) and os.path.exists(os.path.join(self.game, "OMDD", "Binaries", "Win64", "UE4SS.dll"))
        for key, on, yes, no in (("vs", has("JWVersus"), "installed", "not installed (no VS maps built)"),
                                 ("bk", has("JWBarricades"), "installed", "not installed yet (build once)"),
                                 ("ue4ss", ue, "installed", "missing")):
            self.auto_cards[key].configure(text=" %s " % (yes if on else no), bg=OK if on else ("#e0533f" if key == "ue4ss" else "#8a7a60"))
        self.mod_note.config(text=("Not installed on this PC: " + ", ".join(missing)) if missing else "")

    def toggle_mod(self, m):
        want = not B.mod_state(self.game, m)
        try:
            B.set_mod(self.game, m, want)
        except Exception as e:
            messagebox.showerror("OMD Map Builder", str(e))
        self.sync_mods()

    def worker(self, fn, done_msg, popup=True):
        def go():
            try: fn(); ok = True
            except Exception as e:
                B.log("FAILED: %s" % e)
                with open(os.path.join(B.LOGS, "error.txt"), "w", encoding="utf-8") as f: f.write(traceback.format_exc())
                ok = False
            self.last_ok = ok
            self.q.put((lambda: self.finish(ok, done_msg if popup else None),))
        self.busy = True; self.last_ok = None; self.build_btn.state(["disabled"]); self.pack_btn.state(["disabled"]); self.toggle_log(True)
        self.status.configure(text="Working...", fg=ACCENT_HI)
        threading.Thread(target=go, daemon=True).start()

    def finish(self, ok, msg):
        self.busy = False; self.build_btn.state(["!disabled"]); self.pack_btn.state(["!disabled"]); self.refresh()
        if ok and msg: messagebox.showinfo("OMD Map Builder", msg)

    def build(self, from_web=False):
        if self.busy and not from_web: return
        if not self.game and not from_web: self.pick_game()
        if not self.game:
            self.busy = False; self.lines.append("FAILED: the game folder is not set - set it on the Game page in OMD Map Builder"); self.last_ok = False; return
        self.refresh(); self.logbox.delete("1.0", "end"); self.lines.clear(); B.SKIP_INTRO = bool(self.skip_intro.get())
        maps = [m for m in self.maps if not m["_error"]]
        start = bool(self.start_after.get())
        def go():
            self.build_and_mark(maps)
            if start: self.start_game()
        self.worker(go, "Done! The game is starting: your maps are in the run's mission choice." if start else
                    "Done! Start the game: your maps are in the run's mission choice.", popup=not from_web and not start)

    def open_map_maker(self):
        """Opens the Map Maker; with a map selected in the Maps list, with that map loaded."""
        sel = [self.maps[int(i)] for i in self.tree.selection()] if hasattr(self, "maps") else []
        url = self.web.url + ("?open=" + urllib.parse.quote(os.path.basename(sel[0]["_file"])) if sel else "")
        webbrowser.open(url)

    def start_game(self):
        """Starts the game through Steam (its app id from the library's appmanifest for this game folder)."""
        if B.game_running(): B.log("the game is already running"); return
        game = os.path.normpath(self.game); common = os.path.dirname(game); apps = os.path.dirname(common)
        appid = None
        for f in os.listdir(apps) if os.path.isdir(apps) else []:
            if not (f.startswith("appmanifest_") and f.endswith(".acf")): continue
            try: txt = open(os.path.join(apps, f), encoding="utf-8", errors="replace").read()
            except OSError: continue
            if re.search(r'"installdir"\s+"%s"' % re.escape(os.path.basename(game)), txt, re.I): appid = f[len("appmanifest_"):-4]; break
        if not appid: B.log("could not start the game: no Steam app id found for " + game); return
        B.log("starting the game (Steam app %s)..." % appid); os.startfile("steam://rungameid/" + appid)

    def build_and_mark(self, maps):
        B.build_all(maps, self.game); self.mark_built(maps)

    def mark_built(self, maps):
        """Remembers which version of each map file is in the game now (the list shows 'changed since the last build')."""
        self.settings["built"] = {os.path.basename(m["_file"]): {"h": file_hash(m["_file"]), "rev": rev_of(m)} for m in maps}
        save_settings(self.settings)

    def build_state(self, m):
        """'built' (this file is in the game), 'changed' (an older version is) or 'new' (never built)."""
        if "built" not in self.settings: return "unknown"          # built before the app kept track
        b = self.settings["built"].get(os.path.basename(m["_file"]))
        if not b: return "new"
        return "built" if b.get("h") == file_hash(m["_file"]) else "changed"

    # ----- share -----
    def share_maps(self):
        """Friend has OMD Map Builder: the selected maps as share files (Name_v3.omdshare.json) in Claud OMD\\share\\maps."""
        sel = [self.maps[int(i)] for i in self.tree.selection()]
        if not sel:
            messagebox.showinfo("OMD Map Builder", "Select the map (or maps) to send in the list first."); return
        os.makedirs(SHARE_MAPS, exist_ok=True); out = []
        for m in sel:
            stem = os.path.basename(m["_file"])[:-len(".omdmap.json")]
            dst = os.path.join(SHARE_MAPS, stem + ("_v%d" % rev_of(m) if rev_of(m) else "") + ".omdshare.json")
            shutil.copyfile(m["_file"], dst); out.append(dst)
            self.say("share file: " + dst, "ok")
        reveal(out[-1])
        messagebox.showinfo("OMD Map Builder",
            "Send %s to your friend (it's selected in the Explorer window).\n\n"
            "Your friend: OMD Map Builder > Add map file... > pick it > Build & install. "
            "They can also open it in the Map Maker (Open file...) to look at it or change it.\n\n"
            "Playing VS together: you both need the same build. Simplest is the ready-to-play pack (other button), "
            "or both of you build the same map version." % ("this file" if len(out) == 1 else "these %d files" % len(out)))

    def pack_from_web(self):
        """The Map Maker's 'Make ready-to-play pack': builds first when a map is not in the game as it is now, no dialogs."""
        if not self.game:
            self.busy = False; self.lines.append("FAILED: the game folder is not set - set it on the Game page in OMD Map Builder"); self.last_ok = False; return
        self.refresh(); self.logbox.delete("1.0", "end"); self.lines.clear(); B.SKIP_INTRO = bool(self.skip_intro.get())
        ready = [m for m in self.maps if not m["_error"]]
        build_first = any(self.build_state(m) != "built" for m in ready)
        def go():
            if build_first: self.build_and_mark(ready)
            B.log("making the friend pack...")
            friendpack.make(self.game, PACK, B.log)
            B.log("DONE: pack ready - " + PACK)
            reveal(PACK)
        self.worker(go, None, popup=False)

    def share_pack(self):
        """Friend has no OMD Map Builder: zip what is in the game now (all built maps + mods + installer)."""
        if self.busy: return
        if not self.game:
            messagebox.showerror("OMD Map Builder", "Set the game folder first (Game page)."); return
        self.refresh()
        ready = [m for m in self.maps if not m["_error"]]
        stale = [m for m in ready if self.build_state(m) != "built"]
        build_first = False
        if stale:
            names = ", ".join("%s%s" % (m.get("name", "?"), " v%d" % rev_of(m) if rev_of(m) else "") for m in stale[:6]) + (" and more" if len(stale) > 6 else "")
            a = messagebox.askyesnocancel("OMD Map Builder",
                "Not in the game yet, changed since the last build, or not tracked yet: %s.\n\n"
                "Build & install first, so the pack has your latest maps?\n\n"
                "Yes = build, then make the pack\nNo = make the pack from what is in the game now" % names)
            if a is None: return
            build_first = a
        if build_first:
            self.logbox.delete("1.0", "end"); self.lines.clear(); B.SKIP_INTRO = bool(self.skip_intro.get())
        def go():
            if build_first: self.build_and_mark(ready)
            B.log("making the friend pack...")
            friendpack.make(self.game, PACK, B.log)
            reveal(PACK)
        self.worker(go, "The pack is ready: OMD_VS_mods.zip (selected in the Explorer window).\n\n"
                        "Send it to your friend. They close the game, unzip it and double-click install.bat, "
                        "then start the game (for VS: join you from the Steam invite).\n\n"
                        "After you build new maps, make and send a new pack.")

    def uninstall(self):
        if self.busy or not self.game: return
        if messagebox.askyesno("OMD Map Builder", "Take all custom maps out of the game?\nYour map files stay here; build again to put them back."):
            def go():
                B.uninstall(self.game); self.settings["built"] = {}; save_settings(self.settings)
            self.worker(go, "Custom maps removed. The game is back to normal.")


def main():
    if "--build" in sys.argv or "--uninstall" in sys.argv:          # no window: for scripts and testing
        os.makedirs(B.LOGS, exist_ok=True)
        try:
            s = load_settings(); B.SKIP_INTRO = s.get("skip_intro", True)
            game = s.get("game") or B.find_game()
            if "--build" in sys.argv:
                maps = B.collect_maps(s.get("ignored", {}))
                for m in maps: m["_often"] = m.get("id") in set(s.get("often", []))
                B.build_all(maps, game)
                s["built"] = {os.path.basename(m["_file"]): {"h": file_hash(m["_file"]), "rev": rev_of(m)} for m in maps if not m["_error"]}
                save_settings(s)
            else: B.uninstall(game)
            rc = 0
        except Exception as e:
            B.log("FAILED: %s" % e); open(os.path.join(B.LOGS, "error.txt"), "w").write(traceback.format_exc()); rc = 1
        sys.exit(rc)
    root = tk.Tk()
    try: root.iconbitmap(os.path.join(B.HERE, "icon.ico"))
    except tk.TclError: pass
    App(root); root.mainloop()


if __name__ == "__main__":
    main()
