# Extract the Rift Barricade look (materials, glow FX) to find its colour parameters (read-only).
import os, shutil, subprocess
ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
PAKS = r"C:\Program Files (x86)\Steam\steamapps\common\Orcs Must Die Deathtrap\OMDD\Content\Paks"
RETOC = os.path.join(ROOT, "tools", "retoc.exe")
OUT = os.path.join(ROOT, "extracted_tbred"); FLAT = os.path.join(ROOT, "notes", "tbred_extract")
FILTERS = ["Content/MasterMaterials/Traps/Master_Trap_Rift_Barricade", "Content/MasterMaterials/MaterialFunctions/MF_Rift_Barricade_InnerChaos", "Content/Traps/Barricade/FX/NS_Rift_Barricade_Idle", "Content/Traps/Barricade/BP/BP_Rift_Barricade", "Content/Traps/Barricade/Mat/"]
shutil.rmtree(OUT, ignore_errors=True); shutil.rmtree(FLAT, ignore_errors=True); os.makedirs(FLAT)
args = [RETOC, "to-legacy", "--no-shaders", "--version", "UE5_3"]
for f in FILTERS: args += ["--filter", f]
args += [PAKS, OUT]
with open(os.path.join(FLAT, "retoc.txt"), "w", encoding="utf-8", errors="replace") as f:
    p = subprocess.run(args, stdout=f, stderr=subprocess.STDOUT)
names = []
for root, _, files in os.walk(OUT):
    for fn in files:
        if fn.endswith((".ubulk", ".bin")): continue           # skip mesh/texture payloads, keep the small package files
        rel = os.path.relpath(os.path.join(root, fn), OUT).replace(os.sep, "~")
        shutil.copyfile(os.path.join(root, fn), os.path.join(FLAT, rel)); names.append(rel)
open(os.path.join(FLAT, "done.txt"), "w").write("exit %d\n%s" % (p.returncode, "\n".join(sorted(names))))
