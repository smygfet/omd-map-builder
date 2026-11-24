# Installs the Giant Flip Trap for testing. Touches NO Map Maker file (tools\base, exe_src, mapbuild stay as they are):
#  v2: the item entry is copied from the Tar Trap's (purchasable), plus an entry for our own definition; v1's entry is removed
#  1. zz_JWGiantFlip_P (.pak/.utoc/.ucas: the new item, its definition, the Giant Flip's price) + zz_JWGiantFlipTags_P.pak (its tag)
#  2. its trap-book entry: only in the INSTALLED zz_JWRegistry_P.pak (backup tools\giantflip\zz_JWRegistry_P.before_gf.pak).
#     A map build from the Map Builder rewrites that file; then re-run this job until the Map Maker chat adds the entry.
#  3. the UE4SS mod JWGiantFlipGrant (one gold skull, once, to buy it)
# Waits while the game is running. Log: notes\giantflip_install.txt
import os, shutil, struct, subprocess, sys, time
ROOT = os.path.join(os.path.expanduser("~"), "Documents", "Claud OMD")
MB = os.path.join(ROOT, "tools", "mapbuild"); sys.path.insert(0, MB)
import arpatch  # noqa: E402  (read-only use of the Map Maker's library)
HERE = os.path.join(ROOT, "tools", "giantflip")
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Orcs Must Die Deathtrap\OMDD"
MODS = os.path.join(GAME, "Content", "Paks", "Mods"); UE = os.path.join(GAME, "Binaries", "Win64", "Mods")
REPAK = os.path.join(MB, "repak.exe"); NOWIN = 0x08000000
DIR = "/Game/Traps/GiantFlip"
ITEM, DEF = "DA_GiantFlip_InventoryItem", "DA_GiantFlip_Definition"
TAG = '(TagName="Item.Identifier.Trap.JWGiantFlip")'; DEFTAG = "Gameplay.Property.Trap.JWGiantFlip"
log = open(os.path.join(ROOT, "notes", "giantflip_install.txt"), "w", encoding="utf-8")
def p(m): log.write(time.strftime("%H:%M:%S ") + m + "\n"); log.flush()
def game_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq OMDDSteam-Win64-Shipping.exe"], capture_output=True, text=True, creationflags=NOWIN).stdout
    return "OMDDSteam-Win64-Shipping.exe" in out

def drop_ours(r):
    """removes every earlier Giant Flip entry (v1's item was copied from the Flip Trap's, which is NOT purchasable)"""
    keep, n = [], 0
    pk = r.index.get(DIR + "/" + ITEM), r.index.get(DIR + "/" + DEF)
    for s_, e_ in r.asset_records:
        v = struct.unpack_from("<5I", r.b, s_)
        if v[3] in pk and v[3] is not None: n += 1; continue
        keep.append(r.b[s_:e_])
    if n:
        r.assets_blob = b"".join(keep); r.num_assets = len(keep)
    return n

def copy_entry(r, srcpath, src, new, cls, ident):
    a = r.find_asset(srcpath + src, src)
    o = a["start"] + 28; assert struct.unpack_from("<I", r.b, o)[0] == 0, "bundles"; o += 4
    nc = struct.unpack_from("<I", r.b, o)[0]
    chunks = struct.unpack_from("<%di" % nc, r.b, o + 4); flags = struct.unpack_from("<I", r.b, o + 4 + 4 * nc)[0]
    pairs = []
    for k, v in r.pairs_of(a["handle"]):
        kn = r.names[k]
        if kn == "PrimaryAssetName": v = r.v_nlname(ident if cls == "RSTTrapDefinition" else new)
        elif kn == "Identifier": v = r.v_ansi('(TagName="%s")' % ident if cls == "RSTTrapDefinition" else TAG)
        pairs.append((kn, v))
    r.add_asset(DIR, "/Script/OMD4", cls, DIR + "/" + new, new, r.add_pairs(pairs), tuple(chunks), flags)
    p("  index: %s added (from %s, chunks %s, flags 0x%x)" % (new, src, list(chunks), flags))

def add_trap(path):
    r = arpatch.Registry(path)
    n = drop_ours(r)
    if n: p("  index: removed %d earlier Giant Flip entr%s" % (n, "y" if n == 1 else "ies"))
    copy_entry(r, "/Game/Traps/FlipTrap/BP/", "DA_FlipTrap_Big_Definition", DEF, "RSTTrapDefinition", DEFTAG)
    copy_entry(r, "/Game/Traps/TarTrap/BP/", "DA_TarTrap_InventoryItem", ITEM, "RSTInventoryItemDefinition", None)
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
    reg = os.path.join(MODS, "zz_JWRegistry_P.pak")
    tmp = os.path.join(HERE, "regtmp"); shutil.rmtree(tmp, ignore_errors=True)
    subprocess.run([REPAK, "unpack", "-o", tmp, reg], check=True, creationflags=NOWIN)
    ar = os.path.join(tmp, "OMDD", "AssetRegistry.bin")
    if add_trap(ar):
        out = os.path.join(HERE, "zz_JWRegistry_P.pak")
        subprocess.run([REPAK, "pack", "-q", "--version", "V11", "-m", "../../../", "-p", str(0xF6052F54), tmp, out], check=True, creationflags=NOWIN)
        shutil.copyfile(reg, os.path.join(HERE, "zz_JWRegistry_P.before_gf.pak"))
        shutil.copyfile(out, reg); p("installed index: Giant Flip Trap added")
    else:
        p("installed index: Giant Flip Trap already there")
    shutil.rmtree(tmp, ignore_errors=True)
    m = "JWGiantFlipGrant"
    os.makedirs(os.path.join(UE, m, "Scripts"), exist_ok=True)
    shutil.copyfile(os.path.join(HERE, m, "Scripts", "main.lua"), os.path.join(UE, m, "Scripts", "main.lua"))
    if not os.path.exists(os.path.join(UE, m, "enabled.off")): open(os.path.join(UE, m, "enabled.txt"), "w").close()
    p("installed UE4SS mod " + m)
    p("DONE")
except Exception as e:
    import traceback; p("FAILED: %r\n%s" % (e, traceback.format_exc()))
