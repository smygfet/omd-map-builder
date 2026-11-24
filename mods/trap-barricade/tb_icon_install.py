# Installs the Trap Barricade pak with its new icon (a stretched wooden barricade). Waits while the game is running
# (it locks its paks). Keeps the old pak in tools\trapbarricade\pak_before_icon. Log: notes\trapbarricade_icon.txt
import os, shutil, subprocess, time
ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
HERE = os.path.join(ROOT, "tools", "trapbarricade")
MODS = r"C:\Program Files (x86)\Steam\steamapps\common\Orcs Must Die Deathtrap\OMDD\Content\Paks\Mods"
NOWIN = 0x08000000
log = open(os.path.join(ROOT, "notes", "trapbarricade_icon.txt"), "w", encoding="utf-8")
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
    old = os.path.join(HERE, "pak_before_icon"); os.makedirs(old, exist_ok=True)
    for ext in (".pak", ".utoc", ".ucas"):
        n = "zz_JWTrapBarricade_P" + ext
        if os.path.exists(os.path.join(MODS, n)): shutil.copyfile(os.path.join(MODS, n), os.path.join(old, n))
        shutil.copyfile(os.path.join(HERE, "pak_icon", n), os.path.join(MODS, n))
        shutil.copyfile(os.path.join(HERE, "pak_icon", n), os.path.join(HERE, "pak", n))
        p("installed " + n)
    p("DONE")
except Exception as e:
    import traceback; p("FAILED %r\n%s" % (e, traceback.format_exc()))
