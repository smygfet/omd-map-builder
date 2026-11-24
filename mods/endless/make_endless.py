# Endless mode for the game's own missions: every base-game wave script runs its wave 1 for waves 1-39, wave 40 ends.
# Same patch as the VS endless maps (builder/onslaughtloop.py), but written over the original package paths, so the
# missions themselves become endless while zz_JWEndless_P is installed.
import os, sys, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import ue53pkg, ue53rename as RN, onslaughtloop
SRC = sys.argv[1]; OUT = sys.argv[2]
ok, bad = [], []
shutil.rmtree(OUT, ignore_errors=True)
for fn in sorted(os.listdir(SRC)):
    if not fn.endswith(".uasset"): continue
    stem = fn[:-7]; parts = stem.split("~"); on = parts[-1]
    rel = "/".join(parts[:-1]); pkgname = "/Game/" + "/".join(parts[2:])          # OMDD~Content~Levels~... -> /Game/Levels/...
    sp = os.path.join(SRC, stem)
    print("==", on)
    try:
        pk = ue53pkg.Package(sp + ".uasset", sp + ".uexp")
        ub = [e for e in pk.exports if e["name"] == "ExecuteUbergraph_" + on][0]
        old_d = bytes(pk.data(ub)[1])
        new_d = onslaughtloop.loop_wave1(old_d, pk.names, pk.imports)
        hb, xb = RN.rewrite(open(sp + ".uasset", "rb").read(), open(sp + ".uexp", "rb").read(),
                            renames={"NotEqual_IntInt": "Greater_IntInt"}, package_name=pkgname,
                            export_edits={ub["index"]: [(old_d, new_d)]})
        d = os.path.join(OUT, rel); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, on + ".uasset"), "wb").write(hb); open(os.path.join(d, on + ".uexp"), "wb").write(xb)
        ok.append(on)
    except Exception as e:
        print("   SKIPPED:", repr(e)); bad.append((on, repr(e)))
print("\nendless: %d scripts, skipped %d" % (len(ok), len(bad)))
for b in bad: print("  skipped", b)
