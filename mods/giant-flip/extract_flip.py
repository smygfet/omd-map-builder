# Read-only: copy the game's Big Flip Trap files (and the normal Flip Trap for comparison) out of the game paks
# into Claud OMD\notes\giantflip_extract. Nothing in the game folder or the Map Maker is changed.
import os, shutil, subprocess
ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
PAKS = r"C:\Program Files (x86)\Steam\steamapps\common\Orcs Must Die Deathtrap\OMDD\Content\Paks"
RETOC = os.path.join(ROOT, "tools", "retoc.exe")
OUT = os.path.join(ROOT, "extracted_giantflip"); FLAT = os.path.join(ROOT, "notes", "giantflip_extract")
FILTERS = ["Content/Traps/FlipTrap/BP/", "Content/Traps/FlipTrap/Abilities/", "Content/Traps/FlipTrap/FX/", "Content/Traps/FlipTrap/UI/",
           "Content/Traps/FlipTrap/Mesh/", "Content/Traps/Flip_WM/", "Content/Threads/Traps/DA_Thread_FlipTrap",
           "Content/Traps/Max_FlipTrap/BP/", "Content/GameplayCues/GCN_Trap_Fire_FlipTrap", "Content/GameplayCues/GCN_Trap_Place_FlipTrap"]
shutil.rmtree(OUT, ignore_errors=True); shutil.rmtree(FLAT, ignore_errors=True); os.makedirs(FLAT)
args = [RETOC, "to-legacy", "--no-shaders", "--version", "UE5_3"]
for f in FILTERS: args += ["--filter", f]
args += [PAKS, OUT]
with open(os.path.join(FLAT, "retoc.txt"), "w", encoding="utf-8", errors="replace") as f:
    p = subprocess.run(args, stdout=f, stderr=subprocess.STDOUT)
names = []
for root, _, files in os.walk(OUT):
    for fn in files:
        full = os.path.join(root, fn)
        rel = os.path.relpath(full, OUT).replace(os.sep, "~")
        size = os.path.getsize(full)
        names.append("%s %d" % (rel, size))
        if fn.endswith((".ubulk", ".bin")) or size > 3000000: continue      # keep only the package files here
        shutil.copyfile(full, os.path.join(FLAT, rel))
open(os.path.join(FLAT, "done.txt"), "w").write("exit %d\n%s" % (p.returncode, "\n".join(sorted(names))))
