# Read-only: list the game's legacy pak(s) and unpack their Config files -> Claud OMD\notes\game_config
import os, shutil, subprocess, glob
ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
PAKS = r"C:\Program Files (x86)\Steam\steamapps\common\Orcs Must Die Deathtrap\OMDD\Content\Paks"
REPAK = os.path.join(ROOT, "tools", "mapbuild", "repak.exe")
OUT = os.path.join(ROOT, "notes", "game_config"); shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
log = open(os.path.join(OUT, "log.txt"), "w", encoding="utf-8", errors="replace")
for pak in sorted(glob.glob(os.path.join(PAKS, "*.pak"))):
    r = subprocess.run([REPAK, "list", pak], capture_output=True, text=True, errors="replace")
    files = r.stdout.splitlines()
    cfg = [f for f in files if "Config/" in f or f.endswith((".ini", ".json"))]
    log.write("== %s: %d files, %d config\n%s\n" % (os.path.basename(pak), len(files), len(cfg), "\n".join(cfg[:400]))); log.flush()
    if cfg:
        dst = os.path.join(OUT, os.path.basename(pak)[:-4])
        subprocess.run([REPAK, "unpack", "-o", dst, "-i", "Config/", pak], capture_output=True)
        subprocess.run([REPAK, "unpack", "-o", dst + "_all", pak], capture_output=True) if len(files) < 200 else None
log.write("DONE\n"); log.close()
