# OMD Map Builder - turns Map Maker files (*.omdmap.json) into custom Deathtrap missions and installs them.
# No Unreal needed: the geometry, tile image, gameplay level, navmesh, lighting and mission definition are all
# written here; retoc packs them for the game and the game's asset index is patched so the missions show up.
import datetime, glob, hashlib, json, os, re, runpy, shutil, struct, subprocess, sys

APP = "OMD Map Builder"
HERE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))    # bundled files (exe) or source dir
TOOLS = os.path.join(HERE, "mapbuild")
BASE = os.path.join(HERE, "base")
DATA = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), APP)
MAPS = os.path.join(DATA, "maps")
WORK = os.path.join(DATA, "build")
LOGS = os.path.join(DATA, "logs")
DOWNLOADS = os.path.join(os.path.expanduser("~"), "Downloads")
MAP_MAKER_URL = "https://claude.ai/artifact/TGdYQmXqC3AbWVpUmXe3Df"
CP = "/Game/Levels/BaseGame/Castle/CastlePlaza/"
SHARED = "/Game/Levels/Custom/JW_Shared"
OUR_MODS = ["zz_JWMaps_P", "zz_JWMaps_Geo_P", "zz_JWRegistry_P"]
OLD_MODS = ["zz_RiftTest_P", "zz_JWMap_Vista_P", "JWMap_P"]
SKIP_INTRO = True
NORMAL_WEIGHT = 15.0      # chance in the run's mission choice, same as Castle Plaza and the other main maps
OFTEN_WEIGHT = 1000.0     # "Show often": offered in nearly every choice (for testing a map)

sys.path.insert(0, TOOLS)
import mapv2, ue53rename as RN, arpatch, tilepng, hideactors, geowriter, dupactors, bases, onslaughtloop, ue53pkg  # noqa: E402

_log_cb = print
NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def log(msg):
    line = "[%s] %s" % (datetime.datetime.now().strftime("%H:%M:%S"), msg)
    _log_cb(line)
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "build_log.txt"), "a", encoding="utf-8") as f: f.write(line + "\n")


def run(args, cwd=None):
    with open(os.path.join(LOGS, "tools.txt"), "a", encoding="utf-8", errors="replace") as out:
        out.write("\n$ %s\n" % " ".join(args)); out.flush()
        p = subprocess.run(args, stdout=out, stderr=subprocess.STDOUT, cwd=cwd, creationflags=NO_WINDOW)
    if p.returncode != 0: raise RuntimeError("%s failed (exit %d), see the tools log" % (os.path.basename(args[0]), p.returncode))


def pyscript(name, args, cwd=None):
    """Run one of the bundled helper scripts in this process (works inside the exe, no python.exe needed)."""
    old_argv, old_cwd = sys.argv, os.getcwd()
    sys.argv = [name] + [str(a) for a in args]
    try:
        if cwd: os.chdir(cwd)
        runpy.run_path(os.path.join(TOOLS, name), run_name="__main__")
    finally:
        sys.argv = old_argv; os.chdir(old_cwd)


def key(s): return hashlib.md5(s.encode()).hexdigest().upper()


# ---------- where things are ----------
def find_game():
    """Deathtrap's folder: the default Steam library, then every library listed in libraryfolders.vdf."""
    cands = [r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"]
    libs = []
    for steam in cands:
        vdf = os.path.join(steam, "steamapps", "libraryfolders.vdf")
        libs.append(steam)
        if os.path.exists(vdf):
            for line in open(vdf, encoding="utf-8", errors="replace"):
                line = line.strip()
                if line.startswith('"path"'):
                    libs.append(line.split('"')[3].replace("\\\\", "\\"))
    for lib in libs:
        g = os.path.join(lib, "steamapps", "common", "Orcs Must Die Deathtrap")
        if os.path.isdir(os.path.join(g, "OMDD", "Content", "Paks")): return g
    return None


def mods_dir(game): return os.path.join(game, "OMDD", "Content", "Paks", "Mods")


def ue4ss_mods(game): return os.path.join(game, "OMDD", "Binaries", "Win64", "Mods")


RULE_DEFAULTS = dict(endless=1, orcs=50, health=15, send=1, prices=[1000, 1200, 1500, 2500, 5000, 6000], rise=5, archers=1, coins=0, rift=0, midkill=0, pvp=0)


def rules_of(d):
    """The Map Maker's VS rules for one map, with defaults for anything missing (older map files have none)."""
    r = dict(RULE_DEFAULTS); r.update({k: v for k, v in (d.get("rules") or {}).items() if k in RULE_DEFAULTS})
    pr = r.get("prices") if isinstance(r.get("prices"), list) else []
    r["prices"] = [int(pr[i]) if i < len(pr) and str(pr[i]).lstrip("-").isdigit() else RULE_DEFAULTS["prices"][i] for i in range(6)]
    if r["prices"] == [400, 500, 600, 1000]: r["prices"] = list(RULE_DEFAULTS["prices"])   # the first defaults (too cheap)
    for k in ("endless", "orcs", "health", "send", "rise", "archers", "coins", "rift", "midkill", "pvp"):
        try: r[k] = int(r[k])
        except (TypeError, ValueError): r[k] = RULE_DEFAULTS[k]
    return r


def rules_text(built):
    """One line per VS level for the referee: Level_JW_<id> key=value ..."""
    lines = []
    for b in built:
        if not b.get("vs"): continue
        r = b["rules"]
        lines.append("%s endless=%d orcs=%d health=%d send=%d prices=%s rise=%d archers=%d coins=%d rift=%d midkill=%d midhalf=%d killz=%d pits=%d bridge0=%d bridge1=%d pvp=%d" % (
            b["level"], r["endless"] if b.get("endless_ok") else 0, r["orcs"], r["health"], r["send"],
            ",".join(str(p) for p in r["prices"]), r["rise"], r["archers"], r["coins"], r["rift"],
            r["midkill"], int(b.get("mid_half") or 0), int(b.get("killz") or -400), int(b.get("pits") or 0),
            int((b.get("bridge") or [0, 0])[0]), int((b.get("bridge") or [0, 0])[1]), r["pvp"]))
    return "\n".join(lines) + "\n"


def install_referee(game, on, built=()):
    """VS maps keep score with a small UE4SS Lua mod (JWVersus). Installed when a VS map is built, removed otherwise.
    The maps' VS rules go next to it (rules.txt), read by the referee when a match starts."""
    dst = os.path.join(ue4ss_mods(game), "JWVersus")
    if not on:
        if os.path.isdir(dst): shutil.rmtree(dst, ignore_errors=True); log("VS referee mod removed (no VS maps)")
        return
    if not os.path.exists(os.path.join(game, "OMDD", "Binaries", "Win64", "UE4SS.dll")):
        log("NOTE: UE4SS is not installed, so VS maps will play but nobody keeps score"); return
    os.makedirs(os.path.join(dst, "Scripts"), exist_ok=True)
    shutil.copyfile(os.path.join(TOOLS, "JWVersus_main.lua"), os.path.join(dst, "Scripts", "main.lua"))
    open(os.path.join(dst, "enabled.txt"), "w").close()
    open(os.path.join(dst, "rules.txt"), "w").write(rules_text(built))
    # team banners: one line each, "Level_JW_<id> side x y z nx ny" (the wall face point, the floor, the face's normal)
    open(os.path.join(dst, "banners.txt"), "w").write("".join(
        "%s %d %.1f %.1f %.1f %d %d\n" % (b["level"], q["side"], q["x"], q["y"], q["z"], q["nx"], q["ny"])
        for b in built if b.get("vs") for q in b.get("banners") or []))
    log("VS referee mod installed (scores for side A / side B), rules for %d VS map(s)" % sum(1 for b in built if b.get("vs")))


def barricades_text(built):
    """For the JWBarricades game mod. 'L <level> <vs> <killz> <pits>' for every custom level (the mod gives orcs the
    door tag on non-VS levels, so they attack barricades at all; with death pits it kills anyone below killz there), 'B <level> x y z yaw g' for each barricade of a barricade wall (g = 0)
    or a gate (g = its number), and 'G <level> g x y z yaw w' for each gate (its portcullis)."""
    lines = []
    for b in built:
        lines.append("L %s %d %d %d" % (b["level"], 1 if b.get("vs") else 0, int(b.get("killz") or -400), int(b.get("pits") or 0)))
        for q in b.get("barricades") or []:
            lines.append("B %s %.1f %.1f %.1f %d %d" % (b["level"], q["x"], q["y"], q["z"], q["yaw"], q.get("g", 0)))
        for g in b.get("gates") or []:
            lines.append("G %s %d %.1f %.1f %.1f %d %.1f" % (b["level"], g["g"], g["x"], g["y"], g["z"], g["yaw"], g["w"]))
    return "\n".join(lines) + "\n"


def install_barricades(game, built=()):
    """Barricade walls from the Map Maker: a small UE4SS Lua mod (JWBarricades) places the game's own barricades on our
    levels when they load, and lets orcs on our non-VS levels attack barricades (the door tag; the VS referee does that
    on VS levels). Installed whenever UE4SS is there and maps are built, removed with the maps."""
    dst = os.path.join(ue4ss_mods(game), "JWBarricades")
    if not built:
        if os.path.isdir(dst): shutil.rmtree(dst, ignore_errors=True); log("barricade mod removed")
        return
    if not os.path.exists(os.path.join(game, "OMDD", "Binaries", "Win64", "UE4SS.dll")):
        if any(b.get("barricades") for b in built): log("NOTE: UE4SS is not installed, so barricade walls stay plain floor")
        return
    os.makedirs(os.path.join(dst, "Scripts"), exist_ok=True)
    shutil.copyfile(os.path.join(TOOLS, "JWBarricades_main.lua"), os.path.join(dst, "Scripts", "main.lua"))
    if not os.path.exists(os.path.join(dst, "enabled.off")): open(os.path.join(dst, "enabled.txt"), "w").close()
    open(os.path.join(dst, "barricades.txt"), "w").write(barricades_text(built))
    n = sum(len(b.get("barricades") or []) for b in built)
    log("barricade mod installed: %d barricade(s) on %d map(s)" % (n, sum(1 for b in built if b.get("barricades"))))


# ---------- extra mods: switched on/off from the app (files moved aside, not deleted) ----------
# paks: names in Paks\Mods (all extensions); ue4ss: folders in Binaries\Win64\Mods (enabled.txt <-> enabled.off).
# Switched-off paks wait in OMDD\JW_disabled_mods, outside Paks, so the game doesn't load them.
MODS = [
    dict(id="archer", name="Guardian archer trap",
         desc="OMD3's guardian archer as a placeable trap (in the trap book; sell with Delete in the build phase)",
         paks=["zz_JWArcherTrap_P"], ue4ss=["JWArcherAuto", "JWArcherGrant"]),
    dict(id="endless", name="Endless mode (game's own maps)",
         desc="The game's own missions repeat wave 1 up to wave 40, harder every wave (+15 % health, more enemies). "
              "Custom maps on those bases loop too, without getting harder",
         paks=["zz_JWEndless_P"], ue4ss=["JWEndless"]),
    dict(id="trapbarricade", name="Trap Barricade",
         desc="A tall wooden barricade that takes a floor trap on top and wall traps on its sides; 1500 gold, 100 health; "
              "if enemies break it, it and its traps are lost.",
         paks=["zz_JWTrapBarricade_P", "zz_JWTrapBarricadeTags_P"], ue4ss=["JWTrapBarricade", "JWTrapBarricadeGrant"], registry=True),
    dict(id="giantflip", name="Giant Flip Trap",
         desc="The huge 2x2 Flip Trap as its own trap in the trap book; throws big enemies too; 1600 gold.",
         paks=["zz_JWGiantFlip_P", "zz_JWGiantFlipTags_P"], ue4ss=["JWGiantFlip", "JWGiantFlipGrant"], registry=True),
]
PAK_EXT = (".pak", ".utoc", ".ucas", ".sig")


def mods_parked(game): return os.path.join(game, "OMDD", "JW_disabled_mods")


def mod_state(game, m):
    """True = on, False = off, None = not installed on this PC."""
    on = any(os.path.exists(os.path.join(mods_dir(game), p + e)) for p in m["paks"] for e in PAK_EXT) or \
         any(os.path.exists(os.path.join(ue4ss_mods(game), u, "enabled.txt")) for u in m["ue4ss"])
    off = any(os.path.exists(os.path.join(mods_parked(game), p + e)) for p in m["paks"] for e in PAK_EXT) or \
          any(os.path.exists(os.path.join(ue4ss_mods(game), u, "enabled.off")) for u in m["ue4ss"])
    return True if on else (False if off else None)


def set_mod(game, m, on):
    if game_running(): raise RuntimeError("Close the game first, then switch mods")
    src, dst = (mods_parked(game), mods_dir(game)) if on else (mods_dir(game), mods_parked(game))
    os.makedirs(dst, exist_ok=True); moved = 0
    for p in m["paks"]:
        for e in PAK_EXT:
            f = os.path.join(src, p + e)
            if os.path.exists(f): os.replace(f, os.path.join(dst, p + e)); moved += 1
    for u in m["ue4ss"]:
        d = os.path.join(ue4ss_mods(game), u)
        a, b = (("enabled.off", "enabled.txt") if on else ("enabled.txt", "enabled.off"))
        if os.path.exists(os.path.join(d, a)): os.replace(os.path.join(d, a), os.path.join(d, b)); moved += 1
    log("%s switched %s (%d file(s))" % (m["name"], "ON" if on else "OFF", moved))
    if m.get("registry"): refresh_registry(game)


# ---------- endless mode settings (Mods page) ----------
ENDLESS_DIR = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD", "tools", "endless")
ENDLESS_SRC = os.path.join(ENDLESS_DIR, "originals")       # the game's own wave scripts, extracted (legacy .uasset/.uexp)
ENDLESS_DEFAULTS = dict(last_wave=40, health=15, extra=0.5, max_alive=200, from_wave=2,
                        newtypes=1, random=1, starttypes=3, perwave=2, newcount=4, oldcount=2)
ENDLESS_LIMITS = dict(last_wave=(5, 99), health=(0, 100), extra=(0, 5), max_alive=(50, 400), from_wave=(2, 50),
                      newtypes=(0, 1), random=(0, 1), starttypes=(1, 16), perwave=(1, 5), newcount=(0, 10), oldcount=(0, 5))


def endless_clean(s):
    out = {}
    for k, d in ENDLESS_DEFAULTS.items():
        lo, hi = ENDLESS_LIMITS[k]
        try: v = float((s or {}).get(k, d))
        except (TypeError, ValueError): v = d
        v = min(max(v, lo), hi)
        out[k] = v if k == "extra" else int(round(v))
    return out


def endless_built_waves():
    try: return int(open(os.path.join(DATA, "endless_waves.txt")).read().strip())
    except (OSError, ValueError): return 40          # the first install (tools\endless) was built for 40


def endless_rebuild(game, waves):
    """Rebuilds zz_JWEndless_P so the game's missions end at wave `waves`, and puts it where the mod is now (on or off)."""
    if game_running(): raise RuntimeError("Close the game first: the last wave is built into the mod")
    if not os.path.isdir(ENDLESS_SRC): raise RuntimeError("The original wave scripts are missing (" + ENDLESS_SRC + ")")
    work = os.path.join(DATA, "endless_work"); shutil.rmtree(work, ignore_errors=True)
    zen_in = os.path.join(work, "zen_in"); n = 0
    for fn in sorted(os.listdir(ENDLESS_SRC)):
        if not fn.endswith(".uasset"): continue
        stem = fn[:-7]; parts = stem.split("~"); on = parts[-1]
        sp = os.path.join(ENDLESS_SRC, stem)
        pk = ue53pkg.Package(sp + ".uasset", sp + ".uexp")
        ub = [e for e in pk.exports if e["name"] == "ExecuteUbergraph_" + on][0]
        old_d = bytes(pk.data(ub)[1])
        new_d = onslaughtloop.loop_wave1(old_d, pk.names, pk.imports, log=lambda m: None, waves=waves)
        hb, xb = RN.rewrite(open(sp + ".uasset", "rb").read(), open(sp + ".uexp", "rb").read(),
                            renames={"NotEqual_IntInt": "Greater_IntInt"}, package_name="/Game/" + "/".join(parts[2:]),
                            export_edits={ub["index"]: [(old_d, new_d)]})
        d = os.path.join(zen_in, *parts[:-1]); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, on + ".uasset"), "wb").write(hb); open(os.path.join(d, on + ".uexp"), "wb").write(xb); n += 1
    out = os.path.join(work, "out"); os.makedirs(out)
    run([os.path.join(TOOLS, "retoc.exe"), "to-zen", "--version", "UE5_3", zen_in, os.path.join(out, "zz_JWEndless_P.utoc")], cwd=TOOLS)
    m = [x for x in MODS if x["id"] == "endless"][0]
    dst = mods_parked(game) if mod_state(game, m) is False else mods_dir(game)
    os.makedirs(dst, exist_ok=True)
    for e in (".pak", ".utoc", ".ucas"): shutil.copyfile(os.path.join(out, "zz_JWEndless_P" + e), os.path.join(dst, "zz_JWEndless_P" + e))
    os.makedirs(DATA, exist_ok=True); open(os.path.join(DATA, "endless_waves.txt"), "w").write(str(waves))
    shutil.rmtree(work, ignore_errors=True)
    log("endless mode: %d wave scripts rebuilt, missions now end at wave %d" % (n, waves))


def endless_apply(game, s):
    """Writes the settings the JWEndless script reads at each mission start; rebuilds the pak if the last wave changed."""
    s = endless_clean(s)
    d = os.path.join(ue4ss_mods(game), "JWEndless"); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "settings.txt"), "w", encoding="utf-8") as f:
        for k in ENDLESS_DEFAULTS: f.write("%s=%s\n" % (k, s[k]))
    log("endless mode settings: health +%d%% per wave, %.2f extra enemies per wave, max %d alive, harder from wave %d, last wave %d"
        % (s["health"], s["extra"], s["max_alive"], s["from_wave"], s["last_wave"]))
    log("   new enemy types %s (%s order): %d from wave 1, +%d per wave, %d of each new, %d of each earlier"
        % ("on" if s["newtypes"] else "off", "random" if s["random"] else "fixed", s["starttypes"], s["perwave"], s["newcount"], s["oldcount"]))
    if s["last_wave"] != endless_built_waves(): endless_rebuild(game, s["last_wave"])
    return s


# ---------- Giant Flip Trap settings (Mods page) ----------
GIANTFLIP_DEFAULTS = dict(max_weight=2, light=100, heavy=55, veryheavy=35, immovable=20)
GIANTFLIP_LIMITS = dict(max_weight=(0, 3), light=(0, 300), heavy=(0, 300), veryheavy=(0, 300), immovable=(0, 300))
GIANTFLIP_WEIGHTS = ["Light", "Heavy", "Very heavy", "Bosses too"]


def giantflip_clean(s):
    out = {}
    for k, d in GIANTFLIP_DEFAULTS.items():
        lo, hi = GIANTFLIP_LIMITS[k]
        try: v = float((s or {}).get(k, d))
        except (TypeError, ValueError): v = d
        out[k] = int(round(min(max(v, lo), hi)))
    return out


def giantflip_apply(game, s):
    """Writes the settings JWGiantFlip reads every 10 s (works mid-game too)."""
    s = giantflip_clean(s)
    d = os.path.join(ue4ss_mods(game), "JWGiantFlip"); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "settings.txt"), "w", encoding="utf-8") as f:
        for k in GIANTFLIP_DEFAULTS: f.write("%s = %d\n" % (k, s[k]))
    log("giant flip settings: throws up to %s; light %d%%, heavy %d%%, very heavy %d%%, bosses %d%%"
        % (GIANTFLIP_WEIGHTS[s["max_weight"]], s["light"], s["heavy"], s["veryheavy"], s["immovable"]))
    return s


def game_running():
    if os.name != "nt": return False
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq OMDDSteam-Win64-Shipping.exe"], capture_output=True, text=True, creationflags=NO_WINDOW).stdout
        return "OMDDSteam-Win64-Shipping.exe" in out
    except OSError:
        return False


def map_id(name):
    """Internal id used in package and asset names. Unreal reads a trailing '_<number>' in a name as a separate
    number (MD_JW_test_3 -> MD_JW_test + 3), which breaks the lookup of the mission, so such underscores go."""
    i = "".join(c if c.isalnum() else "_" for c in name).strip("_")[:32] or "Map"
    while "__" in i: i = i.replace("__", "_")
    return re.sub(r"_(?=\d+$)", "", i)


LEGACY_MAPS = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD", "maps")


def collect_maps(ignored=None):
    """All map files. New or newer ones in Downloads (and the old Claud OMD/maps folder) are copied into the app's
    maps folder first. ignored: {file name: time removed}; such a file is only taken again if saved after that."""
    ignored = ignored or {}
    os.makedirs(MAPS, exist_ok=True)
    for src in (LEGACY_MAPS, DOWNLOADS):
        for f in glob.glob(os.path.join(src, "*.omdmap.json")):
            name = os.path.basename(f); dst = os.path.join(MAPS, name); mt = os.path.getmtime(f)
            if name in ignored and mt <= ignored[name]: continue
            if not os.path.exists(dst) or mt > os.path.getmtime(dst) + 1:
                shutil.copyfile(f, dst); log("new map: " + name)
    out = []
    for f in sorted(glob.glob(os.path.join(MAPS, "*.omdmap.json"))):
        try:
            d = json.load(open(f, encoding="utf-8"))
            mapv2.plan(mapv2.Map(d)); err = None
        except AssertionError as e: err = str(e)
        except Exception as e: err = "not a Map Maker v2 file (%s)" % e; d = {"name": os.path.basename(f)}
        d["id"] = map_id(d.get("name", "Map")); d["_file"] = f; d["_error"] = err
        out.append(d)
    # two files with the same map name (e.g. saved under two file names): the newest one is built, the others are left
    # out with a note in the list (the game can't have two missions with one name; this used to stop the whole build)
    newest = {}
    for d in out:
        if d["_error"]: continue
        k = d["id"]
        if k not in newest or os.path.getmtime(d["_file"]) > os.path.getmtime(newest[k]["_file"]): newest[k] = d
    for d in out:
        if not d["_error"] and newest[d["id"]] is not d:
            d["_error"] = "same name as %s (newer), left out - rename it or remove one" % os.path.basename(newest[d["id"]]["_file"])
    return out


# ---------- minimap ----------
MM_W, MM_H = 1000, 564                 # the tile template's size (B8G8R8A8): the minimap picture uses it too


def minimap_bgra(M, yaw=0.0):
    """Top view of the built map for the in-game minimap: floors (lighter when higher), walls, rifts (VS: blue / red).
    The picture is laid on the base level's map volume, which is turned by 'yaw' (degrees): picture x runs along the
    volume's local X, picture y (down) along its local Y. Returns (pixels, (centre x, centre y), (half X, half Y)):
    the volume's centre and half sizes (its Extent) in the volume's own axes."""
    import math
    CELL, OX, OY = mapv2.CELL, mapv2.OX, mapv2.OY
    cx, cy = OX + M.cols * CELL / 2, OY + M.rows * CELL / 2
    hw, hh = (M.cols * CELL / 2 + 600) * 1.3, (M.rows * CELL / 2 + 600) * 1.3   # half sizes in world X / Y: the map plus 30 % room (it overfilled the minimap)
    c, s_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    # the volume's local half sizes: whatever world box the turned volume must cover
    ex, ey = abs(c) * hw + abs(s_) * hh, abs(s_) * hw + abs(c) * hh
    rifts = {}
    for m in M.markers:
        if m.get("k") == "rift": rifts[(m["x"], m["y"])] = m.get("s", 0)
    maxh = max([g.get("h", 0) for g in M.g] + [1])
    px = bytearray(MM_W * MM_H * 4)
    for j in range(MM_H):
        ly = ((j + 0.5) / MM_H - 0.5) * 2 * ey
        for i in range(MM_W):
            lx = ((i + 0.5) / MM_W - 0.5) * 2 * ex
            wx, wy = cx + lx * c - ly * s_, cy + lx * s_ + ly * c
            gx, gy = int((wx - OX) // CELL), int((wy - OY) // CELL)
            col = (18, 20, 24); alpha = 0                        # outside the map: see-through (the game's tint shows)
            if 0 <= gx < M.cols and 0 <= gy < M.rows and M.at(gx, gy)["t"] != "v": alpha = 255
            if 0 <= gx < M.cols and 0 <= gy < M.rows:
                g = M.at(gx, gy)
                if g["t"] == "w": col = (205, 198, 182)
                elif g["t"] in ("f", "r"):
                    k = 70 + int(70 * g.get("h", 0) / maxh)
                    col = (k, k, k + 6)
                    if g.get("c") or M.deck(g): col = (k - 15, k - 18, k - 20)
                if (gx, gy) in rifts:
                    fx, fy = (wx - OX) / CELL - gx - 0.5, (wy - OY) / CELL - gy - 0.5
                    if fx * fx + fy * fy < 0.2:
                        col = (60, 140, 255) if (M.vs and rifts[(gx, gy)] == 0) else (235, 70, 70) if M.vs else (120, 200, 255)
            o = (j * MM_W + i) * 4
            px[o:o + 4] = bytes((col[2], col[1], col[0], alpha))
    return bytes(px), (cx, cy), (ex, ey)


def write_minimap(M, B, dirpath, mid, out):
    """The level's minimap: our own picture + a copy of the base level's MapData placed over our map. Returns the level
    renames (base MapData -> ours), or {} when the base's MapData isn't in the base files."""
    import math
    src = os.path.join(BASE, B["level"] + "_MapData")
    if not os.path.exists(src + ".uasset"): log("   minimap: no MapData for %s, left as is" % B["key"]); return {}
    H = open(src + ".uasset", "rb").read(); X = open(src + ".uexp", "rb").read()
    data = X[:-4]
    o = data.find(b"\x00\x07\x00\x07")
    qx, qy, qz, qw = struct.unpack_from("<4d", data, o + 4)
    yaw = math.degrees(2 * math.atan2(qz, qw))                   # the base volume's turn (Arboretum: 90)
    px, (cx, cy), (ex, ey) = minimap_bgra(M, yaw)
    tn = "MinimapImage_JW_" + mid
    h, x = geowriter.write_tile(os.path.join(BASE, "tile_template.uasset"), os.path.join(BASE, "tile_template.uexp"), dirpath + "/" + tn, px)
    open(os.path.join(out, tn + ".uasset"), "wb").write(h); open(os.path.join(out, tn + ".uexp"), "wb").write(x)
    pk = ue53pkg.Package(src + ".uasset", src + ".uexp")
    tex = [n for n in pk.names if n.startswith("/Game/UI/")]
    mdn = "MapData_JW_" + mid
    ren = {B["dir"] + B["level"] + "_MapData": dirpath + "/" + mdn, B["level"] + "_MapData": mdn}
    if tex:
        ren[tex[0]] = dirpath + "/" + tn; ren[tex[0].rsplit("/", 1)[1]] = tn
    # each floor entry (MapVolumes[]): Transform (rotation, translation, scale) then Extent (half sizes) then the
    # picture. We keep the base's rotation and height, put our map's middle and half sizes, and no XY scale.
    new = bytearray(data); n = 0
    while o >= 0:
        e = o + 4
        if e + 104 > len(data): break
        struct.pack_into("<2d", new, e + 32, cx, cy)
        struct.pack_into("<2d", new, e + 80, ex, ey)
        struct.pack_into("<2d", new, e + 56, 1.0, 1.0)          # no XY scale: the picture follows the Extent alone, and
                                                                 # the player markers did not show with the base's scale
        # the picture: package name and asset name as (name index, number). The base's pictures are numbered copies
        # (Level_Castle_CastlePlaza_1, _2: number 2, 3); ours has no number, else the game looked for "..._1"
        struct.pack_into("<i", new, e + 108, 0); struct.pack_into("<i", new, e + 116, 0)
        n += 1
        o = data.find(b"\x00\x07\x00\x07", e + 104)
    h2, x2 = RN.rewrite(H, X, renames=ren, package_name=dirpath + "/" + mdn, export_edits={1: [(data, bytes(new))]})
    open(os.path.join(out, mdn + ".uasset"), "wb").write(h2); open(os.path.join(out, mdn + ".uexp"), "wb").write(x2)
    log("   minimap: our picture (%d volume%s, turned %.0f, half sizes %.0f x %.0f m)" % (n, "" if n == 1 else "s", yaw, ex / 100, ey / 100))
    return {B["dir"] + B["level"] + "_MapData": dirpath + "/" + mdn, B["level"] + "_MapData": mdn}


# ---------- one map ----------
def build_one(d, zen_in):
    mid = d["id"]; work = os.path.join(WORK, mid); os.makedirs(work, exist_ok=True)
    dirpath = "/Game/Levels/Custom/JW_" + mid; L = "Level_JW_" + mid
    out = os.path.join(zen_in, "OMDD", "Content", "Levels", "Custom", "JW_" + mid); os.makedirs(out, exist_ok=True)
    log("== %s" % d["name"])
    M = mapv2.Map(d); P = mapv2.plan(M)
    if M.vs:                                       # the tile image and anything else reading d see the mirrored map
        d = dict(d, cols=M.cols, rows=M.rows, grid=M.g, markers=M.markers)
        log("   VS map: side A on the left, mirrored side B on the right")
    json.dump(P, open(os.path.join(work, "plan.json"), "w"))
    # geometry + tile image
    h, x = geowriter.write_geo(os.path.join(BASE, "geo_template.umap"), os.path.join(BASE, "geo_template.uexp"),
                               dirpath + "/" + L + "_Geo", P["pieces"], label=mid + "_")
    open(os.path.join(out, L + "_Geo.umap"), "wb").write(h); open(os.path.join(out, L + "_Geo.uexp"), "wb").write(x)
    h, x = geowriter.write_tile(os.path.join(BASE, "tile_template.uasset"), os.path.join(BASE, "tile_template.uexp"),
                                dirpath + "/MissionImage_JW_" + mid, tilepng.bgra(d))
    open(os.path.join(out, "MissionImage_JW_%s.uasset" % mid), "wb").write(h); open(os.path.join(out, "MissionImage_JW_%s.uexp" % mid), "wb").write(x)
    log("   %d kit pieces, tile image" % len(P["pieces"]))
    # navmesh
    json.dump({"boxes": P["nav_boxes"]}, open(os.path.join(work, "navboxes.json"), "w"))
    W = lambda n: os.path.join(work, n)
    pyscript("boxes2tris.py", [W("navboxes.json"), W("map.tris"), "30000", "-2400", "0"])
    run([os.path.join(TOOLS, "navbuild.exe"), W("map.tris"), W("raw.navp.json")])
    pyscript("prune.py", [W("raw.navp.json"), W("pruned.json")] + [v for r in P["rifts"] for v in r[:2]])
    run([os.path.join(TOOLS, "navtool.exe"), "json", W("pruned.json"), W("nk.navp")])
    pyscript("deathtrapify.py", [W("nk.navp"), W("map.navp")])
    log("   navmesh")
    # gameplay level = a patched base level (Castle Plaza: crystal rift, Castle Colosseum: normal rift), renamed
    B = bases.BASES[d.get("_base", "plaza")]; BD, BL = B["dir"], B["level"]
    src, actors = os.path.join(BASE, BL), os.path.join(TOOLS, B["actors"])
    cfg = bases.patch_config(B)
    if P.get("vs") and not B["vs_copies"]:         # a base with two rifts of its own: nothing to copy
        cfg = bases.patch_config(B, vs=True)
        log("   two rifts of %s" % B["key"])
    elif P.get("vs"):                              # + a second rift (rift, platform, rift path point) and a copy of every spawner
        h, x, ren_vs, act = dupactors.duplicate(src + ".umap", src + ".uexp", B["vs_copies"], json.load(open(actors)),
                                                log=lambda m: None)
        open(W("vsbase.umap"), "wb").write(h); open(W("vsbase.uexp"), "wb").write(x)
        json.dump(act, open(W("vs_actors.json"), "w")); src, actors = W("vsbase"), W("vs_actors.json")
        cfg = bases.patch_config(B, ren_vs)
        log("   second rift added (%s)" % B["key"])
    # not enough trap grids in the base level (Arboretum has 58 usable ones): copy one so every trap area gets its own
    # grid. Without this the smallest areas (tunnel roofs, short walls, corners) silently got no traps.
    pk = ue53pkg.Package(src + ".umap", src + ".uexp")
    usable = []
    for g in [e for e in pk.exports if pk.class_name(e) == 'BP_OMDTrapGrid_Blank_C']:
        kids = [e for e in pk.exports if e['outer'] == g['index']]
        if any(pk.class_name(e) == 'RSTTrapGridBoxComponent' and e['size'] == 76 for e in kids) and \
           any(e['name'] == 'RootComponent' and e['size'] == 58 for e in kids):
            usable.append(g['name'])
    need = len(P["surfaces"]) - len(usable)
    if need > 0 and usable:
        h, x, _, act = dupactors.duplicate(src + ".umap", src + ".uexp", [(usable[0], 3001 + i) for i in range(need)],
                                           json.load(open(actors)), log=lambda m: None)
        open(W("grids.umap"), "wb").write(h); open(W("grids.uexp"), "wb").write(x)
        json.dump(act, open(W("grid_actors.json"), "w")); src, actors = W("grids"), W("grid_actors.json")
        log("   %d trap areas: %d extra trap grids (the base level has %d)" % (len(P["surfaces"]), need, len(usable)))
    json.dump(cfg, open(W("base_cfg.json"), "w"))
    pyscript("patch_plaza2.py", [src, W("plaza"), W("map.navp"), W("plan.json"), W("pruned.json"), actors, W("base_cfg.json")], cwd=TOOLS)
    drop = B["drop"] | ({"BP_IntroSequencePlayer_Base_C"} if SKIP_INTRO else set())
    hideactors.hide(W("plaza.umap"), W("plaza.uexp"), drop)
    H = open(W("plaza.umap"), "rb").read(); X = open(W("plaza.uexp"), "rb").read()
    ren = {BD + BL: dirpath + "/" + L, BL: L,
           BD + BL + "_Vista": dirpath + "/" + L + "_Geo", BL + "_Vista": L + "_Geo",
           BD + BL + "_Lighting": dirpath + "/" + L + "_Lighting", BL + "_Lighting": L + "_Lighting"}
    for sub, emp in B["empty_subs"].items():                   # the base's own scenery sublevels -> empty
        ren[BD + BL + "_" + sub] = SHARED + "/Level_JW_Empty_" + emp
        ren[BL + "_" + sub] = "Level_JW_Empty_" + emp
    try: ren.update(write_minimap(M, B, dirpath, mid, out))
    except Exception as e: log("   minimap failed, the base's map stays: %s" % e)
    R = rules_of(d)
    endless_ok = bool(P.get("vs") and B.get("loop_script") and R["endless"])
    if P.get("vs") and B.get("loop_script") and not R["endless"]: log("   endless off (VS rules): the mission's own waves")
    if endless_ok:                                  # endless: the map's own copy of the wave script, wave 1 every wave
        LS = B["loop_script"]; on, nn = LS["name"], "BP_Onslaught_JW_" + mid
        sp = os.path.join(BASE, on)
        pk = ue53pkg.Package(sp + ".uasset", sp + ".uexp")
        ub = [e for e in pk.exports if e["name"] == "ExecuteUbergraph_" + on][0]
        old_d = bytes(pk.data(ub)[1])
        new_d = onslaughtloop.loop_wave1(old_d, pk.names, pk.imports, log=log)
        bren = {LS["path"] + on: dirpath + "/" + nn, on + "_C": nn + "_C", "Default__" + on + "_C": "Default__" + nn + "_C",
                "ExecuteUbergraph_" + on: "ExecuteUbergraph_" + nn, "NotEqual_IntInt": "Greater_IntInt"}
        hb, xb = RN.rewrite(open(sp + ".uasset", "rb").read(), open(sp + ".uexp", "rb").read(), renames=bren,
                            package_name=dirpath + "/" + nn, export_edits={ub["index"]: [(old_d, new_d)]})
        open(os.path.join(out, nn + ".uasset"), "wb").write(hb); open(os.path.join(out, nn + ".uexp"), "wb").write(xb)
        ren.update({LS["path"] + on: dirpath + "/" + nn, on + "_C": nn + "_C", "Default__" + on + "_C": "Default__" + nn + "_C"})
        log("   wave script: own copy, %d waves of wave 1 (endless)" % onslaughtloop.WAVES)
    h2, x2 = RN.rewrite(H, X, renames=ren, package_name=dirpath + "/" + L)
    open(os.path.join(out, L + ".umap"), "wb").write(h2); open(os.path.join(out, L + ".uexp"), "wb").write(x2)
    # lighting
    for e in (".umap", ".uexp"): shutil.copyfile(os.path.join(BASE, "Level_Castle_CastlePlaza_Lighting" + e), W("light" + e))
    hideactors.hide(W("light.umap"), W("light.uexp"), hideactors.DROP_LIGHTING)
    H = open(W("light.umap"), "rb").read(); X = open(W("light.uexp"), "rb").read()
    h2, x2 = RN.rewrite(H, X, renames={CP + "Level_Castle_CastlePlaza_Lighting": dirpath + "/" + L + "_Lighting",
                                         "Level_Castle_CastlePlaza_Lighting": L + "_Lighting"}, package_name=dirpath + "/" + L + "_Lighting")
    open(os.path.join(out, L + "_Lighting.umap"), "wb").write(h2); open(os.path.join(out, L + "_Lighting.uexp"), "wb").write(x2)
    # mission definition (own title and localisation keys)
    H = open(os.path.join(BASE, "MD_Castle_CastlePlaza.uasset"), "rb").read(); X = open(os.path.join(BASE, "MD_Castle_CastlePlaza.uexp"), "rb").read()
    k1, k2 = key(mid + ":title"), key(mid + ":sub")
    edits = {1: [(b"ABF99EE84A3B338A8EED3BB3A5AB84C9", k1.encode()), (RN.fstring("Town Plaza"), RN.fstring(("VS: " if M.vs else "") + d["name"])),
                 (b"5EF300CF4359A44249886CB6AE08D9F1", k2.encode()), (RN.fstring("Map: Castle Plaza"), RN.fstring("Map: %s (custom)" % d["name"]))]}
    if d.get("_often"):        # the mission's own Weight (last property, float 15.0) - the game reads this one
        edits[1].append((b"\x00\x00\x70\x41\x00\x00\x00\x00", struct.pack("<f", OFTEN_WEIGHT) + b"\x00\x00\x00\x00"))
    h2, x2 = RN.rewrite(H, X, renames={CP + "Level_Castle_CastlePlaza": dirpath + "/" + L, "MD_Castle_CastlePlaza": "MD_JW_" + mid,
                                         CP + "MD_Castle_CastlePlaza": dirpath + "/MD_JW_" + mid,
                                         CP + "MissionImage_CastlePlaza": dirpath + "/MissionImage_JW_" + mid, "MissionImage_CastlePlaza": "MissionImage_JW_" + mid},
                        package_name=dirpath + "/MD_JW_" + mid, export_edits=edits)
    open(os.path.join(out, "MD_JW_" + mid + ".uasset"), "wb").write(h2); open(os.path.join(out, "MD_JW_" + mid + ".uexp"), "wb").write(x2)
    return dict(id=mid, name=("VS: " if M.vs else "") + d["name"], dir=dirpath, level=L, key=k1, often=bool(d.get("_often")),
                vs=M.vs, mid_x=P.get("mid_x"), mid_half=P.get("mid_half"), killz=P.get("killz"), pits=P.get("pits") or 0, bridge=P.get("bridge"), banners=P.get("banners") or [], barricades=P.get("barricades") or [], gates=P.get("gates") or [], base=B["key"], rules=R, endless_ok=endless_ok)


def write_send_icons(zen_in):
    """The send strip's pictures (the game's enemy and curse icons, backgrounds cut out), one 1000 x 564 sheet that every
    map shares: /Game/Levels/Custom/JW_Shared/JWSendIcons. The referee shows a part of it on each send tile."""
    src = os.path.join(TOOLS, "send_icons.bgra.z")
    if not os.path.exists(src): log("   send icons: no picture sheet, the tiles show names"); return
    import zlib
    px = zlib.decompress(open(src, "rb").read())
    out = os.path.join(zen_in, "OMDD", "Content", "Levels", "Custom", "JW_Shared"); os.makedirs(out, exist_ok=True)
    h, x = geowriter.write_tile(os.path.join(BASE, "tile_template.uasset"), os.path.join(BASE, "tile_template.uexp"), SHARED + "/JWSendIcons", px)
    open(os.path.join(out, "JWSendIcons.uasset"), "wb").write(h); open(os.path.join(out, "JWSendIcons.uexp"), "wb").write(x)
    log("send icons: picture sheet")


# the Trap Barricade's two trap-book entries (made by the trap chat's tb_install3.add_trap): copies of the Rift
# Barricade definition's and the Tar Trap item's records, under /Game/Traps/TrapBarricade, with their own name and
# identifier. They go into the registry only while the mod is on.
TB_DIR = "/Game/Traps/TrapBarricade"
TB_TAG = '(TagName="Item.Identifier.Trap.JWTrapBarricade")'


def add_trapbarricade(r):
    for srcdir, src, new, cls in (("/Game/Traps/Barricade/BP/", "DA_Rift_Barricade_Definition", "DA_TrapBarricade_Definition", "RSTTrapDefinition"),
                                  ("/Game/Traps/TarTrap/BP/", "DA_TarTrap_InventoryItem", "DA_TrapBarricade_InventoryItem", "RSTInventoryItemDefinition")):
        try:
            if r.find_asset(TB_DIR + "/" + new, new): continue
        except KeyError:
            pass
        a = r.find_asset(srcdir + src, src)
        o = a["start"] + 28; assert struct.unpack_from("<I", r.b, o)[0] == 0, "bundles"; o += 4      # no bundles
        nc = struct.unpack_from("<I", r.b, o)[0]
        chunks = struct.unpack_from("<%di" % nc, r.b, o + 4); flags = struct.unpack_from("<I", r.b, o + 4 + 4 * nc)[0]
        pairs = []
        for k, v in r.pairs_of(a["handle"]):
            kn = r.names[k]
            if kn == "PrimaryAssetName": v = r.v_nlname(new)
            elif kn == "Identifier" and cls == "RSTInventoryItemDefinition": v = r.v_ansi(TB_TAG)
            pairs.append((kn, v))
        r.add_asset(TB_DIR, "/Script/OMD4", cls, TB_DIR + "/" + new, new, r.add_pairs(pairs), tuple(chunks), flags)


GF_DIR = "/Game/Traps/GiantFlip"
GF_ITEM_TAG = '(TagName="Item.Identifier.Trap.JWGiantFlip")'
GF_DEF_TAG = "Gameplay.Property.Trap.JWGiantFlip"


def add_giantflip(r):
    """the Giant Flip's two trap-book entries, as tools\\giantflip\\gf_install.py add_trap() makes them:
    the definition copied from the Big Flip Trap's (its PrimaryAssetName is its identifier tag),
    the item copied from the Tar Trap's (purchasable)"""
    for srcdir, src, new, cls in (("/Game/Traps/FlipTrap/BP/", "DA_FlipTrap_Big_Definition", "DA_GiantFlip_Definition", "RSTTrapDefinition"),
                                  ("/Game/Traps/TarTrap/BP/", "DA_TarTrap_InventoryItem", "DA_GiantFlip_InventoryItem", "RSTInventoryItemDefinition")):
        try:
            if r.find_asset(GF_DIR + "/" + new, new): continue
        except KeyError:
            pass
        a = r.find_asset(srcdir + src, src)
        o = a["start"] + 28; assert struct.unpack_from("<I", r.b, o)[0] == 0, "bundles"; o += 4
        nc = struct.unpack_from("<I", r.b, o)[0]
        chunks = struct.unpack_from("<%di" % nc, r.b, o + 4); flags = struct.unpack_from("<I", r.b, o + 4 + 4 * nc)[0]
        is_def = cls == "RSTTrapDefinition"
        pairs = []
        for k, v in r.pairs_of(a["handle"]):
            kn = r.names[k]
            if kn == "PrimaryAssetName": v = r.v_nlname(GF_DEF_TAG if is_def else new)
            elif kn == "Identifier": v = r.v_ansi('(TagName="%s")' % GF_DEF_TAG if is_def else GF_ITEM_TAG)
            pairs.append((kn, v))
        r.add_asset(GF_DIR, "/Script/OMD4", cls, GF_DIR + "/" + new, new, r.add_pairs(pairs), tuple(chunks), flags)


def registry_mods_on(game):
    return [m for m in MODS if m.get("registry") and game and mod_state(game, m)]


def write_registry(built, path, game=None):
    r = arpatch.Registry(os.path.join(BASE, "AssetRegistry.bin"))
    md = r.find_asset(CP + "MD_Castle_CastlePlaza", "MD_Castle_CastlePlaza")
    old = r.pairs_of(md["handle"])
    for b in built:
        newv = {"MapID": r.v_ansi("Map:%s/%s" % (b["dir"], b["level"])), "PrimaryAssetName": r.v_nlname("MD_JW_" + b["id"]),
                "Weight": r.v_ansi("%f" % (OFTEN_WEIGHT if b["often"] else NORMAL_WEIGHT)),
                "TileTitle": r.v_text('NSLOCTEXT("[E99028492E63468C0FB1188FE9EC9432]", "%s", "%s")' % (b["key"], b["name"].replace('"', "'")))}
        h_md = r.add_pairs([(r.names[k], newv.get(r.names[k], v)) for k, v in old])
        h_w = r.add_pairs([("PrimaryAssetName", r.v_nlname("%s/%s" % (b["dir"], b["level"]))), ("PrimaryAssetType", r.v_nlname("Map"))])
        r.add_asset(b["dir"], "/Script/OMD4", "RSTMissionDefinition", b["dir"] + "/MD_JW_" + b["id"], "MD_JW_" + b["id"], h_md, (240,), 0x80042200)
        r.add_asset(b["dir"], "/Script/Engine", "World", "%s/%s" % (b["dir"], b["level"]), b["level"], h_w, (240,), 0x80022200)
    # the send strip's picture sheet: listed so the referee can load it by name (nothing else refers to it)
    if os.path.exists(os.path.join(TOOLS, "send_icons.bgra.z")):
        r.add_asset(SHARED, "/Script/Engine", "Texture2D", SHARED + "/JWSendIcons", "JWSendIcons", r.add_pairs([]), (240,), 0x80002200)
    for m in registry_mods_on(game):
        if m["id"] == "trapbarricade": add_trapbarricade(r); log("trap book: Trap Barricade added")
        if m["id"] == "giantflip": add_giantflip(r); log("trap book: Giant Flip Trap added")
    r.save(path)


REG_BUILT = os.path.join(DATA, "registry_maps.json")      # the last build's maps, so a mod switch can rebuild the index


def pack_registry(built, game, out_pak):
    regdir = os.path.join(WORK, "regpak"); shutil.rmtree(regdir, ignore_errors=True); os.makedirs(os.path.join(regdir, "OMDD"))
    write_registry(built, os.path.join(regdir, "OMDD", "AssetRegistry.bin"), game)
    run([os.path.join(TOOLS, "repak.exe"), "pack", "-q", "--version", "V11", "-m", "../../../", "-p", str(0xF6052F54), regdir, out_pak])
    os.makedirs(DATA, exist_ok=True)
    json.dump([{k: b[k] for k in ("dir", "level", "id", "key", "name", "often")} for b in built], open(REG_BUILT, "w"))


def refresh_registry(game):
    """After a mod with trap-book entries is switched: rebuilds the installed index from the last build's maps."""
    pak = os.path.join(mods_dir(game), "zz_JWRegistry_P.pak")
    if not os.path.exists(pak): log("   no maps installed yet: the trap book follows at the next Build & install"); return
    if not os.path.exists(REG_BUILT): log("   the trap book follows at the next Build & install"); return
    os.makedirs(WORK, exist_ok=True); tmp = os.path.join(WORK, "zz_JWRegistry_P.pak")
    pack_registry(json.load(open(REG_BUILT)), game, tmp)
    shutil.copyfile(tmp, pak); log("   trap book updated (installed index rebuilt)")


def remove_mods(game, names):
    gone = []
    for name in names:
        for ext in (".pak", ".utoc", ".ucas", ".sig"):
            p = os.path.join(mods_dir(game), name + ext)
            if os.path.exists(p): os.remove(p); gone.append(name + ext)
    return gone


# ---------- everything ----------
def build_all(maps=None, game=None):
    os.makedirs(LOGS, exist_ok=True); open(os.path.join(LOGS, "build_log.txt"), "w").close()
    open(os.path.join(LOGS, "tools.txt"), "w").close()
    log("=== Build maps ===")
    game = game or find_game()
    if not game: raise RuntimeError("Orcs Must Die! Deathtrap was not found in any Steam library")
    if game_running(): raise RuntimeError("Close the game first, then build again")
    maps = [m for m in (maps if maps is not None else collect_maps()) if not m.get("_error")]
    if not maps: raise RuntimeError("No valid maps. Make one in the Map Maker and save it (it lands in Downloads)")
    ids = [m["id"] for m in maps]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup: raise RuntimeError("Two maps have the same name (%s). Rename one in the Map Maker" % ", ".join(sorted(dup)))
    # rift type from the Map Maker ("rift"): crystal = Castle Plaza (orcs attack the crystal), normal = orcs walk into the
    # rift (Castle Colosseum; VS maps: Order Arboretum, two rifts of its own). VS maps without a choice get both.
    out = []
    for m in maps:
        rt = m.get("rift") or ("both" if m.get("vs") else "crystal")
        if m.get("vs"):
            has_arb = os.path.exists(os.path.join(BASE, bases.ARBORETUM["level"] + ".umap"))
            if rt in ("crystal", "both") or not has_arb: out.append(m)
            if rt in ("normal", "both") and has_arb:
                out.append(dict(m, id=m["id"] + "_NR", name=m["name"] + " (normal rift)", _base="arboretum"))
        elif rt == "normal" and os.path.exists(os.path.join(BASE, bases.COLOSSEUM["level"] + ".umap")):
            out.append(dict(m, _base="colosseum"))
        else:
            out.append(m)
    maps = out
    shutil.rmtree(WORK, ignore_errors=True)
    zen_in = os.path.join(WORK, "zen_in")
    built = [build_one(d, zen_in) for d in maps]
    try: write_send_icons(zen_in)
    except Exception as e: log("send icons failed: %s" % e)
    log("packing")
    stage = os.path.join(WORK, "install"); os.makedirs(stage)
    run([os.path.join(TOOLS, "retoc.exe"), "to-zen", "--version", "UE5_3", zen_in, os.path.join(stage, "zz_JWMaps_P.utoc")], cwd=TOOLS)
    pack_registry(built, game, os.path.join(stage, "zz_JWRegistry_P.pak"))
    log("installing into " + mods_dir(game))
    os.makedirs(mods_dir(game), exist_ok=True)
    for n in remove_mods(game, OUR_MODS + OLD_MODS): pass
    for f in os.listdir(stage): shutil.copyfile(os.path.join(stage, f), os.path.join(mods_dir(game), f))
    install_referee(game, any(b.get("vs") for b in built), built)
    install_barricades(game, built)
    often = [b["name"] for b in built if b["often"]]
    if often: log("shown often in the mission choice: " + ", ".join(often))
    log("=== DONE: %d map(s) installed: %s. Start the game. ===" % (len(built), ", ".join(b["name"] for b in built)))
    return built


def uninstall(game=None):
    game = game or find_game()
    if not game: raise RuntimeError("Orcs Must Die! Deathtrap was not found")
    if game_running(): raise RuntimeError("Close the game first")
    gone = remove_mods(game, OUR_MODS + OLD_MODS)
    install_referee(game, False)
    install_barricades(game, ())
    log("removed %d file(s): the game is back to its own missions" % len(gone))
