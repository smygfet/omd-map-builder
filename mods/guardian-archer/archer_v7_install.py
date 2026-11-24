# Guardian Archer v7 (2026-11-17): its own icon (ICON_GuardianArcher) + JWArcherAuto v7 (selling the normal way).
#  1. packs tools\trap\zen_in_v7 into zz_JWArcherTrap_P (.pak/.utoc/.ucas) with retoc; the old pak is kept in tools\trap\pak_before_v7
#  2. puts it where the mod is now: Paks\Mods (on) or OMDD\JW_disabled_mods (switched off in the app)
#  3. JWArcherAuto v7 main.lua into the game's UE4SS mod (enabled.txt / enabled.off left as they are)
# Waits while the game is running (it locks its paks). Log: notes\archer_v7.txt
import os, shutil, subprocess, time
ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
HERE = os.path.join(ROOT, "tools", "trap")
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Orcs Must Die Deathtrap\OMDD"
MODS = os.path.join(GAME, "Content", "Paks", "Mods"); PARKED = os.path.join(GAME, "JW_disabled_mods")
UE = os.path.join(GAME, "Binaries", "Win64", "Mods", "JWArcherAuto")
RETOC = os.path.join(ROOT, "tools", "mapbuild", "retoc.exe")
NOWIN = 0x08000000
P = "zz_JWArcherTrap_P"
log = open(os.path.join(ROOT, "notes", "archer_v7.txt"), "w", encoding="utf-8")
def p(m): log.write(time.strftime("%H:%M:%S ") + m + "\n"); log.flush()
def game_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq OMDDSteam-Win64-Shipping.exe"], capture_output=True, text=True, creationflags=NOWIN).stdout
    return "OMDDSteam-Win64-Shipping.exe" in out
try:
    t0 = time.time(); said = False
    while game_running():
        if not said: p("waiting for the game to close..."); said = True
        if time.time() - t0 > 3 * 3600: p("gave up after 3 h"); raise SystemExit
        time.sleep(15)
    out = os.path.join(HERE, "pak_v7"); shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
    r = subprocess.run([RETOC, "to-zen", "--version", "UE5_3", os.path.join(HERE, "zen_in_v7"), os.path.join(out, P + ".utoc")],
                       capture_output=True, text=True, cwd=os.path.dirname(RETOC), creationflags=NOWIN)
    p("retoc exit %d %s" % (r.returncode, (r.stdout + r.stderr).strip()[-400:]))
    if r.returncode != 0: raise RuntimeError("retoc failed")
    for e in (".pak", ".utoc", ".ucas"): assert os.path.exists(os.path.join(out, P + e)), "missing " + P + e
    parked = any(os.path.exists(os.path.join(PARKED, P + e)) for e in (".pak", ".utoc", ".ucas"))
    dst = PARKED if parked else MODS
    old = os.path.join(HERE, "pak_before_v7"); os.makedirs(old, exist_ok=True)
    for e in (".pak", ".utoc", ".ucas"):
        n = P + e
        if os.path.exists(os.path.join(dst, n)): shutil.copyfile(os.path.join(dst, n), os.path.join(old, n))
        shutil.copyfile(os.path.join(out, n), os.path.join(dst, n))
        shutil.copyfile(os.path.join(out, n), os.path.join(HERE, "pak", n))
        p("installed %s (%d bytes) in %s" % (n, os.path.getsize(os.path.join(dst, n)), "JW_disabled_mods (mod is off)" if parked else "Paks\\Mods"))
    os.makedirs(os.path.join(UE, "Scripts"), exist_ok=True)
    shutil.copyfile(os.path.join(HERE, "JWArcherAuto", "main.lua"), os.path.join(UE, "Scripts", "main.lua"))
    p("installed JWArcherAuto v7")
    p("DONE")
except Exception as e:
    import traceback; p("FAILED %r\n%s" % (e, traceback.format_exc()))
