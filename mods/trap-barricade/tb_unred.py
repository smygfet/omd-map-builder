# Take the red Rift Barricade pak out of the game (moved, not deleted), so ordinary Rift Barricades are blue again.
import os, shutil
ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
MODS = r"C:\Program Files (x86)\Steam\steamapps\common\Orcs Must Die Deathtrap\OMDD\Content\Paks\Mods"
DST = os.path.join(ROOT, "tools", "trapbarricade", "disabled"); os.makedirs(DST, exist_ok=True)
log = []
for ext in (".pak", ".ucas", ".utoc"):
    f = os.path.join(MODS, "zz_JWTrapBarricadeRed_P" + ext)
    if os.path.exists(f): shutil.move(f, os.path.join(DST, os.path.basename(f))); log.append("moved " + f)
    else: log.append("not there " + f)
os.makedirs(os.path.join(ROOT, "notes"), exist_ok=True)
open(os.path.join(ROOT, "notes", "trapbarricade_unred.txt"), "w").write("\n".join(log) + "\ndone\n")
