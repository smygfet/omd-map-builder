# Unreal-free writers for a custom map's cooked assets (UE5.3 legacy cooked format, then retoc -> IoStore):
#   write_geo()  geometry sublevel: one StaticMeshActor + StaticMeshComponent per kit piece
#   write_tile() mission tile texture (1000 x 564 BGRA, no mips)
# Both start from a template that Unreal cooked once (tools\base\geo_template.* / tile_template.*), so every
# header field keeps exactly the layout the game expects; only counts, indices, transforms and pixels change.
import hashlib, struct

TAG = 0x9E2A83C1


def u_fstring(s):
    e = s.encode('ascii'); return struct.pack('<i', len(e) + 1) + e + b'\0'


# ---- UE name hashes stored next to each name (FCrc::Strihash_DEPRECATED / FCrc::StrCrc32, low 16 bits) ----
def _tables():
    norm, refl = [], []
    for i in range(256):
        c = i << 24
        for _ in range(8): c = ((c << 1) ^ 0x04C11DB7) & 0xffffffff if c & 0x80000000 else (c << 1) & 0xffffffff
        norm.append(c)
        c = i
        for _ in range(8): c = (c >> 1) ^ 0xEDB88320 if c & 1 else c >> 1
        refl.append(c)
    return norm, refl
_NORM, _REFL = _tables()


def name_hashes(s):
    h = 0
    for ch in s.upper(): h = ((h >> 8) & 0x00FFFFFF) ^ _NORM[(h ^ ord(ch)) & 0xFF]
    c = 0xffffffff
    for ch in s:
        v = ord(ch)
        for _ in range(4): c = (c >> 8) ^ _REFL[(c ^ v) & 0xff]; v >>= 8
    return struct.pack('<HH', h & 0xffff, (~c & 0xffffffff) & 0xffff)


class Summary:
    """FPackageFileSummary of an unversioned UE5.3 cooked package: field name -> (pos, fmt)."""
    def __init__(self, h):
        self.f = {}; o = 0
        def take(n, fmt):
            nonlocal o
            v = struct.unpack_from(fmt, h, o)[0]; self.f[n] = (o, fmt); o += struct.calcsize(fmt); return v
        def fstr(n):
            nonlocal o
            p = o; L = struct.unpack_from('<i', h, o)[0]; o += 4
            s = h[o:o + L - 1].decode('latin-1') if L > 0 else ''; o += max(L, 0)
            self.f[n] = (p, 'fstr'); return s
        assert take('tag', '<I') == TAG
        assert take('legacy', '<i') == -8
        take('ue3', '<i'); take('ue4', '<i'); take('ue5', '<i'); take('lic', '<i')
        assert take('ncv', '<i') == 0
        take('TotalHeaderSize', '<i')
        self.package_name = fstr('PackageName')
        flags = take('PackageFlags', '<I'); assert flags & 0x80000000
        take('NameCount', '<i'); take('NameOffset', '<i')
        take('SoftObjectPathsCount', '<i'); take('SoftObjectPathsOffset', '<i')
        take('GatherableTextDataCount', '<i'); take('GatherableTextDataOffset', '<i')
        take('ExportCount', '<i'); take('ExportOffset', '<i')
        take('ImportCount', '<i'); take('ImportOffset', '<i')
        take('DependsOffset', '<i')
        take('SoftPackageReferencesCount', '<i'); take('SoftPackageReferencesOffset', '<i')
        take('SearchableNamesOffset', '<i'); take('ThumbnailTableOffset', '<i')
        o += 16
        assert take('GenerationCount', '<i') == 1
        take('GenExportCount', '<i'); take('GenNameCount', '<i')
        for nm in ('Saved', 'Compat'): o += 10; fstr(nm + 'Branch')
        take('CompressionFlags', '<I'); take('CompressedChunks', '<i'); take('PackageSource', '<I')
        assert take('AdditionalPackagesToCook', '<i') == 0
        take('AssetRegistryDataOffset', '<i'); take('BulkDataStartOffset', '<q'); take('WorldTileInfoDataOffset', '<i')
        assert take('ChunkIDCount', '<i') == 0
        take('PreloadDependencyCount', '<i'); take('PreloadDependencyOffset', '<i')
        take('NamesReferencedFromExportDataCount', '<i'); take('PayloadTocOffset', '<q'); take('DataResourceOffset', '<i')
        self.end = o

    def get(self, h, n): p, fmt = self.f[n]; return struct.unpack_from(fmt, h, p)[0]
    def put(self, h, n, v): p, fmt = self.f[n]; struct.pack_into(fmt, h, p, v)


class Pkg:
    def __init__(self, h, x):
        self.h, self.x = h, x; S = self.S = Summary(h); g = lambda n: S.get(h, n)
        self.hdr = g('TotalHeaderSize')
        o = g('NameOffset'); self.names = []
        for _ in range(g('NameCount')):
            L = struct.unpack_from('<i', h, o)[0]; o += 4
            self.names.append(h[o:o + L - 1].decode('latin-1')); o += L + 4
        io, ic = g('ImportOffset'), g('ImportCount')
        self.imports = [bytearray(h[io + 32 * i: io + 32 * i + 32]) for i in range(ic)]
        eo, ec = g('ExportOffset'), g('ExportCount')
        self.exports = [bytearray(h[eo + 96 * i: eo + 96 * i + 96]) for i in range(ec)]
        po = g('PreloadDependencyOffset')
        self.data, self.deps = [], []
        for e in self.exports:
            size, off = struct.unpack_from('<qq', e, 28)
            self.data.append(x[off - self.hdr: off - self.hdr + size])
            f, a, b, c, d = struct.unpack_from('<5i', e, 76)
            self.deps.append(([struct.unpack_from('<i', h, po + 4 * (f + k))[0] for k in range(a + b + c + d)] if f >= 0 else [], (a, b, c, d)))
        self.ar = h[g('AssetRegistryDataOffset'):po]

    def name(self, b, o): i, n = struct.unpack_from('<ii', b, o); return self.names[i], n
    def cls(self, k):
        c = struct.unpack_from('<i', self.exports[k], 0)[0]
        return self.name(self.imports[-c - 1], 20)[0] if c < 0 else None


def build_package(tpl, names, imports, exports, data, deps, package_name):
    """Serialize a package that keeps tpl's summary layout. exports: 96-byte entries (size/offset/deps patched here)."""
    h0 = tpl.h; S = tpl.S
    pn_pos = S.f['PackageName'][0]; old = struct.unpack_from('<i', h0, pn_pos)[0]
    summ = bytearray(h0[:pn_pos] + u_fstring(package_name) + h0[pn_pos + 4 + old:S.end])
    S2 = Summary(bytes(summ) + b'\0' * 64)
    out = bytearray(summ)
    name_off = len(out)
    for s in names: out += u_fstring(s) + name_hashes(s)
    imp_off = len(out)
    for im in imports: out += im
    exp_off = len(out); out += b'\0' * (96 * len(exports))
    dep_off = len(out); out += b'\0' * (4 * len(exports))
    ar_off = len(out); out += tpl.ar
    pre_off = len(out); flat = []
    firsts = []
    for lst, cnt in deps:
        firsts.append(len(flat) if lst else -1); flat += lst
    out += struct.pack('<%di' % len(flat), *flat)
    dro = S.get(h0, 'DataResourceOffset'); new_dro = -1
    if dro > 0:                                   # bulk data resource table (texture pixels): offsets are export-relative
        new_dro = len(out); out += h0[dro:S.get(h0, 'TotalHeaderSize')]
    hdr = len(out)
    x = bytearray(); offs = []
    for d in data: offs.append(hdr + len(x)); x += d
    for k, e in enumerate(exports):
        e = bytearray(e)
        struct.pack_into('<qq', e, 28, len(data[k]), offs[k])
        struct.pack_into('<5i', e, 76, firsts[k], *deps[k][1])
        out[exp_off + 96 * k: exp_off + 96 * k + 96] = e
    for n, v in [('TotalHeaderSize', hdr), ('NameCount', len(names)), ('NameOffset', name_off),
                 ('SoftObjectPathsOffset', imp_off), ('ExportCount', len(exports)), ('ExportOffset', exp_off),
                 ('ImportCount', len(imports)), ('ImportOffset', imp_off), ('DependsOffset', dep_off),
                 ('GenExportCount', len(exports)), ('GenNameCount', len(names)), ('AssetRegistryDataOffset', ar_off),
                 ('BulkDataStartOffset', hdr + len(x)), ('PreloadDependencyCount', len(flat)), ('PreloadDependencyOffset', pre_off), ('DataResourceOffset', new_dro)]:
        S2.put(out, n, v)
    if package_name != S.package_name:            # per-package GUID and source hash, derived from the path
        dig = hashlib.md5(package_name.encode()).digest()
        g = S2.f['GenerationCount'][0] - 16; out[g:g + 16] = dig
        S2.put(out, 'PackageSource', struct.unpack('<I', dig[:4])[0])
    return bytes(out), bytes(x) + struct.pack('<I', TAG)


def write_geo(tpl_umap, tpl_uexp, package_path, pieces, label='', exact=False):
    """pieces: [{'m': mesh path, 'l': [x,y,z], 'r': [pitch,yaw,roll], 's': [sx,sy,sz], 't': tag}, ...]"""
    T = Pkg(open(tpl_umap, 'rb').read(), open(tpl_uexp, 'rb').read())
    old_pkg = T.S.package_name; old_world = old_pkg.rsplit('/', 1)[1]; new_world = package_path.rsplit('/', 1)[1]
    names = [package_path if s == old_pkg else new_world if s == old_world else s for s in T.names]
    nidx = {s: i for i, s in enumerate(names)}
    def nm(s):
        if s not in nidx: nidx[s] = len(names); names.append(s)
        return nidx[s]
    imports = [bytearray(b) for b in T.imports]
    def find_import(cls, name, outer):
        for i, b in enumerate(imports):
            if T_name(b, 8) == cls and T_name(b, 20) == name and struct.unpack_from('<i', b, 16)[0] == outer: return -(i + 1)
        return None
    def T_name(b, o): i, n = struct.unpack_from('<ii', b, o); return names[i] if n == 0 else None
    pkg_tmpl = next(b for b in imports if T_name(b, 8) == 'Package')        # any Package import: same class/flags
    mesh_tmpl = next(b for b in imports if T_name(b, 8) == 'StaticMesh')
    mesh_imp = {}
    def mesh(path):
        if path in mesh_imp: return mesh_imp[path]
        pkg, obj = path.split('.')[0], path.split('.')[0].rsplit('/', 1)[1]
        p = find_import('Package', pkg, 0)
        if p is None:
            b = bytearray(pkg_tmpl); struct.pack_into('<ii', b, 20, nm(pkg), 0); imports.append(b); p = -len(imports)
        m = find_import('StaticMesh', obj, p)
        if m is None:
            b = bytearray(mesh_tmpl); struct.pack_into('<i', b, 16, p); struct.pack_into('<ii', b, 20, nm(obj), 0)
            imports.append(b); m = -len(imports)
        mesh_imp[path] = m; return m
    kind = {}
    for k in range(len(T.exports)): kind.setdefault(T.cls(k), []).append(k)
    L, M, NV, W, WS = (kind[c][0] for c in ('Level', 'Model', 'NavigationSystemModuleConfig', 'World', 'WorldSettings'))
    A0, C0 = kind['StaticMeshActor'][0], kind['StaticMeshComponent'][0]
    assert (L, M, NV) == (0, 1, 2)
    N = len(pieces); nA, nC = 3, 3 + N; nW, nWS = 3 + 2 * N, 4 + 2 * N
    remap = {L + 1: 1, M + 1: 2, NV + 1: 3, W + 1: nW + 1, WS + 1: nWS + 1}
    def rm(v): return remap.get(v, v) if v > 0 else v
    def entry(k, outer=None):
        e = bytearray(T.exports[k]); struct.pack_into('<i', e, 12, rm(struct.unpack_from('<i', e, 12)[0]) if outer is None else outer); return e
    exports, data, deps = [None] * (5 + 2 * N), [None] * (5 + 2 * N), [None] * (5 + 2 * N)
    # fixed exports
    for k, new in ((M, 1), (NV, 2), (W, nW), (WS, nWS)):
        exports[new] = entry(k); data[new] = T.data[k]
        lst, cnt = T.deps[k]; deps[new] = ([rm(v) for v in lst], cnt)
    # Level: actor array = [WorldSettings, None, actors...]
    d = T.data[L]; n = struct.unpack_from('<i', d, 34)[0]
    head = bytearray(d[:34]); struct.pack_into('<i', head, 26, nWS + 1)
    exports[0] = entry(L)
    lst, (a, b, c, e_) = T.deps[L]
    # actors + components
    ad = T.data[A0]; lab = ad.index(b'OMDB_') - 4; a_mid = ad[12:lab]
    ea0, ec0 = T.exports[A0], T.exports[C0]
    aname = struct.unpack_from('<i', ea0, 16)[0]
    alst, acnt = T.deps[A0]; clst, ccnt = T.deps[C0]
    order = sorted(range(N), key=lambda i: 'StaticMeshActor_%d' % i) if exact else list(range(N))
    slot = {i: k for k, i in enumerate(order)}
    actors = [nA + slot[i] + 1 for i in range(N)]
    data[0] = bytes(head) + struct.pack('<i', N + 2) + struct.pack('<%di' % (N + 2), nWS + 1, 0, *actors) + d[38 + 4 * n:]
    deps[0] = ([2, nWS + 1] + actors + [rm(v) for v in lst[a + b:]], (a, 2 + N, c, e_))
    for i, p in enumerate(pieces):
        k = slot[i]; ai, ci = nA + k + 1, nC + k + 1
        e = bytearray(ea0); struct.pack_into('<i', e, 12, 1); struct.pack_into('<ii', e, 16, aname, i + 1); exports[nA + k] = e
        data[nA + k] = b'\x00\x02\x3d\x03' + struct.pack('<ii', ci, ci) + a_mid + u_fstring('OMDB_%s%s_%d' % (label, p.get('t', 'Piece'), i))
        deps[nA + k] = ([ci] + [v for v in alst[acnt[0] + acnt[1]:acnt[0] + acnt[1] + acnt[2]]] + [1], acnt)
        m = mesh(p['m'])
        e = bytearray(ec0); struct.pack_into('<i', e, 12, ai); exports[nC + k] = e
        l, r, s = [float(v) for v in p['l']], [float(v) for v in p['r']], [float(v) for v in p.get('s', [1, 1, 1])]
        if not exact: body = b'\x10\x07' + struct.pack('<9d', *l, *r, *s)
        elif any(r) and s != [1.0, 1.0, 1.0]: body = b'\x10\x07' + struct.pack('<9d', *l, *r, *s)
        elif any(r): body = b'\x10\x05' + struct.pack('<6d', *l, *r)
        elif s != [1.0, 1.0, 1.0]: body = b'\x10\x02\x01\x03' + struct.pack('<6d', *l, *s)
        else: body = b'\x10\x03' + struct.pack('<3d', *l)
        data[nC + k] = b'\x04\x02\x7f\x00' + body[:2 if body[1] != 2 else 4] + struct.pack('<i', m) + body[2 if body[1] != 2 else 4:] + b'\0' * 12
        cdep = list(clst); cdep[1] = m; cdep[-1] = ai
        deps[nC + k] = (cdep, ccnt)
    assert acnt == (0, 1, 3, 1) and ccnt == (0, 2, 2, 1), (acnt, ccnt)
    return build_package(T, names, imports, exports, data, deps, package_path)


def write_tile(tpl_uasset, tpl_uexp, package_path, bgra):
    """Mission tile texture from the cooked template; bgra = 1000*564*4 bytes."""
    T = Pkg(open(tpl_uasset, 'rb').read(), open(tpl_uexp, 'rb').read())
    old_pkg = T.S.package_name; old_obj = old_pkg.rsplit('/', 1)[1]; new_obj = package_path.rsplit('/', 1)[1]
    names = [package_path if s == old_pkg else new_obj if s == old_obj else s for s in T.names]
    d = bytearray(T.data[0]); w, h_ = 1000, 564
    i = d.index(b'PF_B8G8R8A8\0') + 24                     # 12-byte format name, then 12 bytes, then the pixels
    assert len(bgra) == w * h_ * 4 and len(d) - i - len(bgra) == 24, (len(bgra), len(d) - i)
    assert struct.unpack_from('<ii', d, i + len(bgra)) == (w, h_)
    d[i:i + len(bgra)] = bgra
    d[16:32] = hashlib.md5((package_path + ':light').encode()).digest()        # texture's own GUID
    return build_package(T, names, T.imports, T.exports, [bytes(d)], T.deps, package_path)
