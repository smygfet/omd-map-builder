# Installs the Trap Barricade for testing (v3: the item's trap-book entry is copied from the Tar Trap's, which is
# purchasable; the Rift Barricade's isn't. If an earlier install added entries, the index is first restored from its backup). Touches NO Map Maker file (tools\base, exe_src, mapbuild stay as they are):
#  1. zz_JWTrapBarricade_P (.pak/.utoc/.ucas: the trap's packages) + zz_JWTrapBarricadeTags_P.pak (its identifier tag)
#  2. the trap book entry: only in the INSTALLED zz_JWRegistry_P.pak (backup tools\trapbarricade\zz_JWRegistry_P.before_tb.pak).
#     A map build from the Map Builder rewrites that file, so the trap leaves the trap book until the Map Maker
#     chat adds the two entries to its base index (see the project note claude/trap-barricade.md).
#  3. the UE4SS mods JWTrapBarricade (behaviour) and JWTrapBarricadeGrant (one gold skull, once, to buy it)
# Waits while the game is running (it locks the mod files). Log: notes\trapbarricade_install3.txt
import os, shutil, struct, subprocess, sys, time
ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
MB = os.path.join(ROOT, "tools", "mapbuild"); sys.path.insert(0, MB)
import arpatch  # noqa: E402  (read-only use of the Map Maker's library)
HERE = os.path.join(ROOT, "tools", "trapbarricade")
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Orcs Must Die Deathtrap\OMDD"
MODS = os.path.join(GAME, "Content", "Paks", "Mods"); UE = os.path.join(GAME, "Binaries", "Win64", "Mods")
REPAK = os.path.join(MB, "repak.exe"); NOWIN = 0x08000000
DIR = "/Game/Traps/TrapBarricade"; SRC = "/Game/Traps/Barricade/BP/"
TAG = '(TagName="Item.Identifier.Trap.JWTrapBarricade")'
log = open(os.path.join(ROOT, "notes", "trapbarricade_install3.txt"), "w", encoding="utf-8")
def p(m): log.write(time.strftime("%H:%M:%S ") + m + "\n"); log.flush()
def game_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq OMDDSteam-Win64-Shipping.exe"], capture_output=True, text=True, creationflags=NOWIN).stdout
    return "OMDDSteam-Win64-Shipping.exe" in out

def add_trap(path):
    r = arpatch.Registry(path)
    try:
        if r.find_asset(DIR + "/DA_TrapBarricade_InventoryItem", "DA_TrapBarricade_InventoryItem"): return False
    except KeyError:
        pass
    for srcdir, src, new, cls in (("/Game/Traps/Barricade/BP/", "DA_Rift_Barricade_Definition", "DA_TrapBarricade_Definition", "RSTTrapDefinition"),
                                  ("/Game/Traps/TarTrap/BP/", "DA_TarTrap_InventoryItem", "DA_TrapBarricade_InventoryItem", "RSTInventoryItemDefinition")):
        a = r.find_asset(srcdir + src, src)
        # the source record's chunks and flags
        o = a["start"] + 28; assert struct.unpack_from("<I", r.b, o)[0] == 0, "bundles"; o += 4      # no bundles
        nc = struct.unpack_from("<I", r.b, o)[0]
        chunks = struct.unpack_from("<%di" % nc, r.b, o + 4); flags = struct.unpack_from("<I", r.b, o + 4 + 4 * nc)[0]
        pairs = []
        for k, v in r.pairs_of(a["handle"]):
            kn = r.names[k]
            if kn == "PrimaryAssetName": v = r.v_nlname(new)
            elif kn == "Identifier" and cls == "RSTInventoryItemDefinition": v = r.v_ansi(TAG)
            pairs.append((kn, v))
        r.add_asset(DIR, "/Script/OMD4", cls, DIR + "/" + new, new, r.add_pairs(pairs), tuple(chunks), flags)
        p("  index: %s added (from %s, chunks %s, flags 0x%x)" % (new, src, list(chunks), flags))
    r.save(path)
    return True

try:
    t0 = time.time()
    while game_running():
        if time.time() - t0 > 3 * 3600: p("game still running after 3 h, giving up"); sys.exit(1)
        if int(time.time() - t0) % 300 < 20: p("waiting for the game to close...")
        time.sleep(20)
    for f in os.listdir(os.path.join(HERE, "pak")):
        shutil.copyfile(os.path.join(HERE, "pak", f), os.path.join(MODS, f)); p("installed " + f)
    # old Trap Barricade files that are no longer part of the mod
    reg = os.path.join(MODS, "zz_JWRegistry_P.pak")
    bak = os.path.join(HERE, "zz_JWRegistry_P.before_tb.pak")
    if os.path.exists(bak) and os.path.getmtime(reg) <= os.path.getmtime(os.path.join(HERE, "zz_JWRegistry_P.pak")) + 5:
        shutil.copyfile(bak, reg); os.remove(bak); p("restored the installed index from its backup (it still had the old entries)")
    tmp = os.path.join(HERE, "regtmp"); shutil.rmtree(tmp, ignore_errors=True)
    subprocess.run([REPAK, "unpack", "-o", tmp, reg], check=True, creationflags=NOWIN)
    ar = os.path.join(tmp, "OMDD", "AssetRegistry.bin")
    if add_trap(ar):
        out = os.path.join(HERE, "zz_JWRegistry_P.pak")
        subprocess.run([REPAK, "pack", "-q", "--version", "V11", "-m", "../../../", "-p", str(0xF6052F54), tmp, out], check=True, creationflags=NOWIN)
        shutil.copyfile(reg, os.path.join(HERE, "zz_JWRegistry_P.before_tb.pak"))
        shutil.copyfile(out, reg); p("installed index: Trap Barricade added")
    else:
        p("installed index: Trap Barricade already there")
    shutil.rmtree(tmp, ignore_errors=True)
    for m in ("JWTrapBarricade", "JWTrapBarricadeGrant"):
        os.makedirs(os.path.join(UE, m, "Scripts"), exist_ok=True)
        shutil.copyfile(os.path.join(HERE, m, "Scripts", "main.lua"), os.path.join(UE, m, "Scripts", "main.lua"))
        if not os.path.exists(os.path.join(UE, m, "enabled.off")): open(os.path.join(UE, m, "enabled.txt"), "w").close()
        p("installed UE4SS mod " + m)
    p("DONE")
except Exception as e:
    import traceback; p("FAILED: %r\n%s" % (e, traceback.format_exc()))
