# Builds "OMD Map Builder.exe" with PyInstaller from tools\exe_src + the map builder tools and base files.
# Run with Unreal's bundled Python (it has PyInstaller). The app also runs this itself when its sources change
# (OMD_NO_COPY=1: it then swaps in exe_build\dist\OMD Map Builder.exe and restarts).
import os, shutil, subprocess, sys

ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
SRC = os.path.join(ROOT, "tools", "exe_src")
STAGE = os.path.join(ROOT, "exe_build")
LOG = os.path.join(ROOT, "notes", "build_exe.txt")
log = open(LOG, "w", encoding="utf-8")
def p(m): log.write(m + "\n"); log.flush(); print(m)

sys.path.insert(0, SRC)
import srchash  # noqa: E402

shutil.rmtree(STAGE, ignore_errors=True); os.makedirs(STAGE)
for f in ("app.py", "builder.py", "srchash.py", "icon.ico", "mapmaker.html"):
    shutil.copyfile(os.path.join(SRC, f), os.path.join(STAGE, f))
open(os.path.join(STAGE, "version.txt"), "w").write(srchash.source_hash())
mb = os.path.join(STAGE, "mapbuild"); os.makedirs(mb)
for f in ["mapv2.py", "tilepng.py", "geowriter.py", "hideactors.py", "ue53pkg.py", "ue53rename.py", "arpatch.py", "cityhash64.py",
          "boxes2tris.py", "prune.py", "deathtrapify.py", "patch_plaza2.py", "castleplaza_actors.json", "colosseum_actors.json", "arboretum_actors.json", "bases.py", "findloc.py", "envdeco.py", "props.py",
          "dupactors.py", "onslaughtloop.py", "friendpack.py", "JWVersus_main.lua", "JWBarricades_main.lua", "send_icons.bgra.z", "navbuild.exe", "navtool.exe", "repak.exe"]:
    shutil.copyfile(os.path.join(ROOT, "tools", "mapbuild", f), os.path.join(mb, f))
shutil.copyfile(os.path.join(ROOT, "tools", "retoc.exe"), os.path.join(mb, "retoc.exe"))
bs = os.path.join(STAGE, "base"); os.makedirs(bs)
for f in ["AssetRegistry.bin", "Level_Castle_CastlePlaza.umap", "Level_Castle_CastlePlaza.uexp", "Level_Castle_CastlePlaza_Lighting.umap",
          "Level_Castle_CastlePlaza_Lighting.uexp", "MD_Castle_CastlePlaza.uasset", "MD_Castle_CastlePlaza.uexp",
          "geo_template.umap", "geo_template.uexp", "tile_template.uasset", "tile_template.uexp",
          "Level_Castle_Colosseum.umap", "Level_Castle_Colosseum.uexp",
          "Level_Gardens_Arboretum.umap", "Level_Gardens_Arboretum.uexp",
          "BP_Onslaught_Gardens_Arboretum.uasset", "BP_Onslaught_Gardens_Arboretum.uexp",
          "Level_Castle_CastlePlaza_MapData.uasset", "Level_Castle_CastlePlaza_MapData.uexp",
          "Level_Castle_Colosseum_MapData.uasset", "Level_Castle_Colosseum_MapData.uexp",
          "Level_Gardens_Arboretum_MapData.uasset", "Level_Gardens_Arboretum_MapData.uexp"]:
    shutil.copyfile(os.path.join(ROOT, "tools", "base", f), os.path.join(bs, f))

hidden = ["mapv2", "tilepng", "geowriter", "hideactors", "ue53pkg", "ue53rename", "arpatch", "cityhash64", "dupactors", "bases", "findloc", "envdeco", "props", "onslaughtloop", "friendpack", "runpy", "collections", "srchash"]
args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed", "--name", "OMD Map Builder",
        "--icon", "icon.ico", "--paths", "mapbuild", "--add-data", "mapbuild;mapbuild", "--add-data", "base;base",
        "--add-data", "icon.ico;.", "--add-data", "mapmaker.html;.", "--add-data", "version.txt;."]
for h in hidden: args += ["--hidden-import", h]
args += ["app.py"]
p("RUN " + " ".join(args))
r = subprocess.run(args, cwd=STAGE, capture_output=True, text=True)
p("rc %d" % r.returncode); p(r.stdout[-2000:]); p(r.stderr[-4000:])
exe = os.path.join(STAGE, "dist", "OMD Map Builder.exe")
if r.returncode != 0 or not os.path.exists(exe):
    p("NO EXE"); sys.exit(1)
p("EXE OK %d bytes, version %s" % (os.path.getsize(exe), srchash.source_hash()))
if not os.environ.get("OMD_NO_COPY"):
    def put(dst):
        try: shutil.copyfile(exe, dst); p("copied to " + dst)
        except PermissionError:                       # the app is open: leave a new copy next to it
            alt = dst[:-4] + " (new).exe"; shutil.copyfile(exe, alt); p("in use, wrote " + alt)
    put(os.path.join(ROOT, "OMD Map Builder.exe"))
    desk = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.path.isdir(desk): put(os.path.join(desk, "OMD Map Builder.exe"))
p("DONE")
