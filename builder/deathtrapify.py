# Patch a NavKit-written NAVP (Knt layout) into Deathtrap's NavPower v46 conventions.
import math, struct, sys
src, dst = sys.argv[1], sys.argv[2]
d = bytearray(open(src, 'rb').read())
AGENTS = [dict(layer=0, radius=42.0, height=192.0, step=35.0), dict(layer=1, radius=80.0, height=360.0, step=35.0)]
struct.pack_into('<I', d, 20, 0x01000001)          # file header constantFlags
struct.pack_into('<I', d, 40, 46)                  # navset version
ngraphs = struct.unpack_from('<I', d, 44)[0]
o = 48
for gi in range(ngraphs):
    h = list(struct.unpack_from('<10I11fI', d, o))
    a = AGENTS[min(gi, len(AGENTS) - 1)]
    h[0] = 46; h[1] = a['layer']
    h[10], h[11], h[12], h[13], h[14] = 200.0, 10.0, a['radius'], a['step'], a['height']
    struct.pack_into('<10I11fI', d, o, *h)
    area_bytes, total = h[2], h[8]
    base = o; p = o + 340; end = p + area_bytes
    pos_by_off = {}
    q = p
    while q < end:                                   # first pass: area centres by graph offset
        pos_by_off[q - base] = struct.unpack_from('<3f', d, q + 32)
        q += 72 + (struct.unpack_from('<I', d, q + 56)[0] & 0x7f) * 32
    nareas = nedges = 0
    while p < end:
        struct.pack_into('<I', d, p + 52, 0)         # usage flags: Deathtrap uses 0
        f2 = struct.unpack_from('<I', d, p + 60)[0]
        struct.pack_into('<I', d, p + 60, (f2 & ~0xF800) | ((a['layer'] & 0x1F) << 11))  # layer index in area flags2
        here = struct.unpack_from('<3f', d, p + 32)
        n = struct.unpack_from('<I', d, p + 56)[0] & 0x7f
        for k in range(n):
            eo = p + 72 + k * 32
            adj = struct.unpack_from('<Q', d, eo)[0]
            struct.pack_into('<I', d, eo + 20, 0xFFFC0000)
            cost = math.ceil(math.dist(here, pos_by_off[adj]) * 5) if adj else 0
            struct.pack_into('<I', d, eo + 24, cost)
            nedges += 1
        nareas += 1
        p += 72 + n * 32
    print("graph %d: %d areas, %d edges" % (gi, nareas, nedges))
    o += total
data = bytes(d[24:]); s = 0
for (w,) in struct.iter_unpack('<I', data[:len(data) // 4 * 4]): s = (s + w) & 0xffffffff
struct.pack_into('<I', d, 12, s)
open(dst, 'wb').write(d)
print("checksum %08x, %d bytes" % (s, len(d)))
