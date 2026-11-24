import os, subprocess
ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
PAK = r"C:\Program Files (x86)\Steam\steamapps\common\Orcs Must Die Deathtrap\OMDD\Content\Paks\pakchunk0-Windows.pak"
REPAK = os.path.join(ROOT, "tools", "mapbuild", "repak.exe")
OUT = os.path.join(ROOT, "notes", "game_config")
for f in ["OMDD/Config/DefaultGameplayTags.ini", "OMDD/Config/Tags/UITags.ini", "OMDD/Config/DefaultGame.ini", "OMDD/Config/DefaultEngine.ini"]:
    r = subprocess.run([REPAK, "get", PAK, f], capture_output=True)
    open(os.path.join(OUT, f.split("/")[-1] + ".txt"), "wb").write(r.stdout or r.stderr)
