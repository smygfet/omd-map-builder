# Find the RelativeLocation (3 doubles) of actors' root components in a UE5.3 legacy cooked level.
# Unversioned property header: fragments (u16: skip 7 bits, has-zeroes bit 7, is-last bit 8, value count bits 9-15),
# then a zero mask if any fragment has zeroes, then the values. The location is the first value when the first
# fragment skips straight to it; otherwise we search the values for the first plausible 3-double vector.
import struct, ue53pkg

def header(d):
    o = 0; vals = 0; zeros = False; frags = []
    while True:
        f = struct.unpack_from('<H', d, o)[0]; o += 2
        skip = f & 0x7f; hz = (f >> 7) & 1; last = (f >> 8) & 1; vn = f >> 9
        frags.append((skip, vn, hz)); vals += vn; zeros |= bool(hz)
        if last: break
    if zeros:
        o += 1 if vals <= 8 else (2 if vals <= 16 else 4 * ((vals + 31) // 32))
    return o, frags

def plausible(v): return all(abs(c) < 2e6 for c in v) and any(abs(c) > 1.0 for c in v) and all(c == c for c in v)

ROOT_NAMES = ('Root', 'DefaultSceneRoot', 'RootComponent', 'SceneComp', 'CollisionCapsule', 'SpawnVolume', 'Scene',
              'RiftEnterArea', 'SceneRoot')

def loc_offset(d, L):
    """Offset of the RelativeLocation in component data d whose RelativeLocation has schema index L, or None."""
    he, fr = header(d)
    idx = 0; first = True; seen = 0
    for skip, vn, hz in fr:
        idx += skip
        if idx <= L < idx + vn:
            if first and L == idx: return he
            if fr[-1] is (skip, vn, hz) or fr.index((skip, vn, hz)) == len(fr) - 1:
                after = idx + vn - L                     # values from L to the end (loc, rot, ...): 24 bytes each
                return len(d) - 8 - 24 * after
            return None
        idx += vn; first = False
    return None

def find_actors(p, classes):
    """{actor name: {'comp', 'cls', 'off', 'xyz'}} for actors of the given classes (uexp offsets)."""
    T = p.total_header
    lvl = [e for e in p.exports if e['name'] == 'PersistentLevel'][0]
    out = {}
    for a in p.exports:
        if a['outer'] != lvl['index'] or p.class_name(a) not in classes: continue
        comps = [e for e in p.exports if e['outer'] == a['index']]
        comps.sort(key=lambda e: ROOT_NAMES.index(e['name']) if e['name'] in ROOT_NAMES else 99)
        for c in comps:
            cn = p.class_name(c)
            L = 5 if cn == 'SceneComponent' else 120
            s = c['off'] - T; d = p.x[s:s + c['size']]
            try: o = loc_offset(d, L)
            except Exception: o = None
            if o is None or o < 0 or o + 24 > len(d): continue
            v = struct.unpack_from('<3d', d, o)
            if plausible(v):
                out[a['name']] = {'comp': c['name'], 'cls': cn, 'off': s + o, 'xyz': list(v)}
                break
    return out
