# Extract the files needed for a placeable Guardian Archer trap (read-only: game paks -> Claud OMD\notes\trap_extract).
import os, shutil, subprocess
ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
PAKS = r"C:\Program Files (x86)\Steam\steamapps\common\Orcs Must Die Deathtrap\OMDD\Content\Paks"
RETOC = os.path.join(ROOT, "tools", "retoc.exe")
OUT = os.path.join(ROOT, "extracted_icons"); FLAT = os.path.join(ROOT, "notes", "icon_extract")
FILTERS = ["UI/Icons/Blessings/Blessing_Sentinel_Damage", "UI/Icons/Distortions/Distortion_Guardians", "UI/Icons/Skills/icon_sentinel_", "Distortion_Sentinels_Disabled", "Traps/Ballista/UI/ICON_Trap_AutoBallista", "Potion_Sentinel-immunity", "Icon_SentinelShield_Filled"]
FILTERS_OLD = ["Content/Traps/Sentinel_Archer/", "Content/Traps/Archer_Guardian/",
           "Characters/Guardians/Sentinel_Archer/Abilities/", "Characters/Guardians/Sentinel_Archer/BP/",
           "Characters/Guardians/Sentinel_Archer/Data/", "Characters/Guardians/Sentinel_Archer/Projectile/",
           "Content/Traps/Ballista/BP/", "Content/Traps/Ballista/Abilities/", "Content/Traps/Ballista/UI/",
           "Content/Traps/Sentinel_Cannoneer/BP/", "Content/Traps/Sentinel_Cannoneer/Abilities/",
           "Content/Traps/FloorSpikes/BP/", "Content/Traps/FloorSpikes/Abilities/", "Content/Traps/FloorSpikes/UI/",
           "Content/Traps/Barricade/BP/DA_Barricade_Definition", "Content/Traps/Barricade/BP/DA_Barricade_InventoryItem",
           "Content/Traps/Barricade/BP/BP_RiftBarricade_ItemInstance", "Content/Game/DA_DefaultGameData",
           "CastlePlaza/BP/BP_CastlePlaza_Archer_Guardian_Ledge", "Content/Traps/Shared/"]
shutil.rmtree(OUT, ignore_errors=True); shutil.rmtree(FLAT, ignore_errors=True); os.makedirs(FLAT)
args = [RETOC, "to-legacy", "--no-shaders", "--version", "UE5_3"]
for f in FILTERS: args += ["--filter", f]
args += [PAKS, OUT]
with open(os.path.join(FLAT, "retoc.txt"), "w", encoding="utf-8", errors="replace") as f:
    p = subprocess.run(args, stdout=f, stderr=subprocess.STDOUT)
names = []
for root, _, files in os.walk(OUT):
    for fn in files:
        if fn.endswith(".bin"): continue           # skip mesh/texture payloads, keep the small package files
        rel = os.path.relpath(os.path.join(root, fn), OUT).replace(os.sep, "~")
        shutil.copyfile(os.path.join(root, fn), os.path.join(FLAT, rel)); names.append(rel)
open(os.path.join(FLAT, "done.txt"), "w").write("exit %d\n%s" % (p.returncode, "\n".join(sorted(names))))
