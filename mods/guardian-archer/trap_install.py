# Installs the Guardian Archer trap (zz_JWArcherTrap_P) and adds its two entries to the game's asset index:
#  - tools\base\AssetRegistry.bin (backup: AssetRegistry.orig.bin), so every later map build keeps the trap
#  - the installed zz_JWRegistry_P.pak, so it works right away
# Waits while the game is running (it locks the mod files). Touches nothing else. Log: notes\trap_install.txt
import os, shutil, subprocess, sys, time

ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
MB = os.path.join(ROOT, "tools", "mapbuild"); sys.path.insert(0, MB)
import arpatch  # noqa: E402

MODS = r"C:\Program Files (x86)\Steam\steamapps\common\Orcs Must Die Deathtrap\OMDD\Content\Paks\Mods"
HERE = os.path.join(ROOT, "tools", "trap")
REPAK = os.path.join(MB, "repak.exe")
BASE = os.path.join(ROOT, "tools", "base", "AssetRegistry.bin")
NOWIN = 0x08000000
DIR = "/Game/Traps/GuardianArcher"
TAG = '(TagName="Item.Identifier.Trap.GravityPillar")'
log = open(os.path.join(ROOT, "notes", "trap_install.txt"), "w", encoding="utf-8")
def p(m): log.write(time.strftime("%H:%M:%S ") + m + "\n"); log.flush()

def game_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq OMDDSteam-Win64-Shipping.exe"], capture_output=True, text=True, creationflags=NOWIN).stdout
    return "OMDDSteam-Win64-Shipping.exe" in out

def add_trap(path_in, path_out):
    """Adds the trap's definition + inventory item (copied from the Tar Trap's entries). Returns False if already there."""
    r = arpatch.Registry(path_in)
    try:
        if r.find_asset(DIR + "/DA_GuardianArcher_InventoryItem", "DA_GuardianArcher_InventoryItem"): return False
    except KeyError:
        pass
    for src, new, cls, flags in (("DA_TarTrap_Definition", "DA_GuardianArcher_Definition", "RSTTrapDefinition", 0x80002200),
                                 ("DA_TarTrap_InventoryItem", "DA_GuardianArcher_InventoryItem", "RSTInventoryItemDefinition", 0x80042200)):
        a = r.find_asset("/Game/Traps/TarTrap/BP/" + src, src)
        pairs = []
        for k, v in r.pairs_of(a["handle"]):
            kn = r.names[k]
            if kn == "PrimaryAssetName": v = r.v_nlname(new)
            elif kn == "Identifier" and cls == "RSTInventoryItemDefinition": v = r.v_ansi(TAG)
            elif kn == "Identifier": v = r.v_ansi('(TagName="Gameplay.Property.Trap.Sentinel")')
            pairs.append((kn, v))
        h = r.add_pairs(pairs)
        r.add_asset(DIR, "/Script/OMD4", cls, DIR + "/" + new, new, h, (240,), flags)
    r.save(path_out)
    return True

try:
    t0 = time.time()
    while game_running():
        if time.time() - t0 > 3 * 3600: p("game still running after 3 h, giving up"); sys.exit(1)
        if int(time.time() - t0) % 300 < 20: p("waiting for the game to close...")
        time.sleep(20)
    # 1. the trap's own mod files
    for f in os.listdir(os.path.join(HERE, "pak")):
        shutil.copyfile(os.path.join(HERE, "pak", f), os.path.join(MODS, f)); p("installed " + f)
    # 2. base index (used by every map build from the PC sources)
    bak = os.path.join(os.path.dirname(BASE), "AssetRegistry.orig.bin")
    if not os.path.exists(bak): shutil.copyfile(BASE, bak); p("backed up base index")
    p("base index: " + ("trap added" if add_trap(BASE, BASE) else "trap already there"))
    # 3. installed index
    reg = os.path.join(MODS, "zz_JWRegistry_P.pak")
    if os.path.exists(reg):
        tmp = os.path.join(HERE, "regtmp"); shutil.rmtree(tmp, ignore_errors=True)
        subprocess.run([REPAK, "unpack", "-o", tmp, reg], check=True, creationflags=NOWIN)
        ar = os.path.join(tmp, "OMDD", "AssetRegistry.bin")
        if add_trap(ar, ar):
            out = os.path.join(HERE, "zz_JWRegistry_P.pak")
            subprocess.run([REPAK, "pack", "-q", "--version", "V11", "-m", "../../../", "-p", str(0xF6052F54), tmp, out], check=True, creationflags=NOWIN)
            shutil.copyfile(reg, os.path.join(HERE, "zz_JWRegistry_P.before_trap.pak"))
            shutil.copyfile(out, reg); p("installed index: trap added")
        else:
            p("installed index: trap already there")
    else:
        p("no zz_JWRegistry_P.pak installed (build the maps once; the base index already has the trap)")
    p("DONE")
except Exception as e:
    import traceback; p("FAILED: %r\n%s" % (e, traceback.format_exc()))
