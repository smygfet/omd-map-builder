# Endless VS: makes a mission's wave script (BP_Onslaught_<map>, a Blueprint) run its wave-1 actions for many waves.
#
# How the script works: at the start the game calls the BP event Onslaught_Start(WaveNumber, SpawnerIndex) for wave
# 1, 2, 3, ... (per spawner) until the script calls OnslaughtEnd(); each call queues that wave's actions. The script
# is a switch on SpawnerIndex, then a switch on WaveNumber, compiled as
#   Let CmpSuccess = NotEqual_IntInt(K2Node_Event_WaveNumber, k); JumpIfNot(CmpSuccess) -> case k     (k rising)
# (A script that never calls OnslaughtEnd makes the game loop forever while loading: tried, it froze.)
#
# The patch: the import NotEqual_IntInt becomes Greater_IntInt (the caller renames it). With rising k, "jump when
# NOT (x > k)" still picks case k for x = k, so every switch keeps working for its own numbers. Then, per WaveNumber
# switch: its case 1 slot gets k = WAVES - 1 (waves 1 .. WAVES-1 all run wave 1), its highest case (the one that ends
# the mission, wave 7 in Arboretum) gets k = WAVES, the cases in between get WAVES - 1 (never reached). A switch
# without a case 1 (a spawner that is idle in wave 1) gets k = 0 everywhere: it never jumps, as in wave 1.
import struct

WAVES = 40


def loop_wave1(data, names, imports, log=print, waves=WAVES):
    """data: bytes of the ExecuteUbergraph function export. Returns the patched bytes (same length).
    The caller must also rename the name 'NotEqual_IntInt' to 'Greater_IntInt'."""
    ne = [i for i, im in enumerate(imports) if im["name"] == "NotEqual_IntInt"]
    assert ne, "no NotEqual_IntInt import"
    imp = struct.pack("<i", -(ne[0] + 1))
    wave = names.index("K2Node_Event_WaveNumber")
    d = bytearray(data)
    cmps = []
    pos = d.find(b"\x68" + imp + b"\x00")
    while pos >= 0:
        var = struct.unpack_from("<i", d, pos + 10)[0]
        if d[pos + 22] == 0x1D and d[pos + 27] == 0x16 and d[pos + 28] == 0x07:
            k = struct.unpack_from("<i", d, pos + 23)[0]
            cmps.append(dict(pos=pos, var=var, k=k))
        pos = d.find(b"\x68" + imp + b"\x00", pos + 1)
    # every compare must be part of a rising switch, or Greater would change what it does
    groups, cur = [], []
    for c in cmps:
        if cur and (c["var"] != cur[-1]["var"] or c["k"] <= cur[-1]["k"] or c["pos"] - cur[-1]["pos"] > 90):
            groups.append(cur); cur = []
        cur.append(c)
    if cur: groups.append(cur)
    for g in groups:
        ks = [c["k"] for c in g]
        assert ks == sorted(ks) and min(ks) >= 1, "switch cases not rising from 1+: %s" % ks
    wg = [g for g in groups if g[0]["var"] == wave]
    assert wg, "no WaveNumber switch found"
    top = max(c["k"] for g in wg for c in g)
    for g in wg:
        ks = [c["k"] for c in g]
        if g[0]["k"] == 1:
            for c in g:
                nk = waves if (c["k"] == top and top > 1) else waves - 1
                struct.pack_into("<i", d, c["pos"] + 23, nk)
            log("   wave switch %s: waves 1-%d run wave 1%s" % (ks, waves - 1, ", wave %d ends" % waves if top in ks else ""))
        else:
            for c in g: struct.pack_into("<i", d, c["pos"] + 23, 0)
            log("   wave switch %s (idle in wave 1): off" % ks)
    return bytes(d)
