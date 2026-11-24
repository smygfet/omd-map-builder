# Add new assets to a UE5.3 cooked AssetRegistry.bin (version 17, TextFirst tag store).
# Rebuilds: name batch, fixed tag store (appends texts, names, ansi strings, pairs), asset list.
import struct
try:
    import cityhash
except ImportError:
    import cityhash64 as cityhash


def u32(b, o): return struct.unpack_from('<I', b, o)[0]


class Registry:
    def __init__(self, path):
        b = self.b = open(path, 'rb').read()
        self.head = b[:24]                                   # guid, version, filter-editor-only
        o = 24
        n, nbytes = struct.unpack_from('<II', b, o); o += 8
        self.hash_version = b[o:o + 8]; o += 8
        self.hashes = list(struct.unpack_from('<%dQ' % n, b, o)); o += 8 * n
        hdr = b[o:o + 2 * n]; o += 2 * n
        self.names = []; self.wide = []
        for i in range(n):
            h = (hdr[2 * i] << 8) | hdr[2 * i + 1]; L = h & 0x7fff
            if h & 0x8000: s = b[o:o + 2 * L].decode('utf-16-le'); o += 2 * L
            else: s = b[o:o + L].decode('latin-1'); o += L
            self.names.append(s); self.wide.append(bool(h & 0x8000))
        self.index = {s: i for i, s in enumerate(self.names)}
        # store
        st = o
        assert u32(b, o) == 0x12345679; o += 4
        self.C = list(struct.unpack_from('<11I', b, o)); o += 44
        tb = u32(b, o); o += 4
        self.text_blob = b[o:o + tb]; o += tb
        nnn, nn, nnep, nep, nt, nao, nwo, nas, nws, nnp, np = self.C
        self.arr = {}
        for name, cnt, sz in [('nlnames', nnn, 4), ('names', nn, 8), ('nlexp', nnep, 16), ('exp', nep, 20), ('aoff', nao, 4),
                              ('woff', nwo, 4), ('astr', nas, 1), ('wstr', nws, 2), ('nlpairs', nnp, 8), ('pairs', np, 12)]:
            self.arr[name] = bytearray(b[o:o + cnt * sz]); o += cnt * sz
        assert u32(b, o) == 0x87654321; o += 4
        self.num_assets = struct.unpack_from('<i', b, o)[0]; o += 4
        self.assets_blob_start = o
        # skip to the end of the asset list using a small parser
        self.asset_records = []
        for i in range(self.num_assets):
            s = o; o = self._skip_asset(o); self.asset_records.append((s, o))
        self.assets_blob = b[self.assets_blob_start:o]
        self.tail = b[o:]

    def _skip_asset(self, o):
        b = self.b
        def nm(o):
            v = u32(b, o); return o + (8 if v & 0x80000000 else 4)
        for _ in range(5): o = nm(o)
        o += 8
        nb = u32(b, o); o += 4
        for _ in range(nb):
            o = nm(o); np_ = u32(b, o); o += 4
            for _ in range(np_):
                o = nm(o); o = nm(o); L = struct.unpack_from('<i', b, o)[0]; o += 4 + (L if L > 0 else -2 * L)
        cc = u32(b, o); o += 4 + 4 * cc
        return o + 4

    # ---- helpers to add data ----
    def name(self, s):
        if s in self.index: return self.index[s]
        self.names.append(s); self.wide.append(False)
        self.hashes.append(cityhash.CityHash64(s.lower().encode('latin-1')))
        self.index[s] = len(self.names) - 1
        return self.index[s]

    def v_ansi(self, s):
        i = self.C[5]
        self.arr['aoff'] += struct.pack('<I', self.C[7])
        e = s.encode('latin-1') + b'\0'
        self.arr['astr'] += e; self.C[7] += len(e); self.C[5] += 1
        return (i << 3) | 0

    def v_nlname(self, s):
        i = self.C[0]; self.arr['nlnames'] += struct.pack('<I', self.name(s)); self.C[0] += 1
        return (i << 3) | 2

    def v_text(self, s):
        i = self.C[4]
        e = s.encode('latin-1') + b'\0'
        self.text_blob += struct.pack('<i', len(e)) + e; self.C[4] += 1
        return (i << 3) | 6

    def pairs_of(self, handle):
        begin = handle & 0xffffffff; num = (handle >> 32) & 0xffff
        a = self.arr['nlpairs']
        return [struct.unpack_from('<II', a, 8 * (begin + k)) for k in range(num)]

    def add_pairs(self, pairs):
        """pairs: list of (key_string, value_id) - sorted the same way the engine stores them."""
        begin = self.C[9]
        for k, v in pairs: self.arr['nlpairs'] += struct.pack('<II', self.name(k), v)
        self.C[9] += len(pairs)
        return (1 << 63) | (len(pairs) << 32) | begin

    def add_asset(self, package_path, class_pkg, class_name, package_name, asset_name, handle, chunks, flags):
        rec = b''
        for s in (package_path, class_pkg, class_name, package_name, asset_name):
            i = self.name(s); assert i < 0x80000000; rec += struct.pack('<I', i)
        rec += struct.pack('<Q', handle) + struct.pack('<I', 0)
        rec += struct.pack('<I', len(chunks)) + b''.join(struct.pack('<i', c) for c in chunks) + struct.pack('<I', flags)
        self.assets_blob += rec; self.num_assets += 1

    def find_asset(self, package_name, asset_name):
        pk = self.index[package_name]; an = self.index[asset_name]
        for s, e in self.asset_records:
            v = struct.unpack_from('<5I', self.b, s)
            if v[3] == pk and v[4] == an:
                h = struct.unpack_from('<Q', self.b, s + 20)[0]
                o = s + 28; nb = u32(self.b, o)
                return dict(handle=h, start=s, end=e)
        return None

    def save(self, path):
        n = len(self.names)
        strs = b''; hdr = b''
        for s, w in zip(self.names, self.wide):
            if w: e = s.encode('utf-16-le'); L = len(e) // 2; hdr += struct.pack('>H', 0x8000 | L)
            else: e = s.encode('latin-1'); L = len(e); hdr += struct.pack('>H', L)
            strs += e
        out = bytearray(self.head)
        out += struct.pack('<II', n, len(strs)) + self.hash_version + struct.pack('<%dQ' % n, *self.hashes) + hdr + strs
        out += struct.pack('<I', 0x12345679) + struct.pack('<11I', *self.C) + struct.pack('<I', len(self.text_blob)) + self.text_blob
        for k in ('nlnames', 'names', 'nlexp', 'exp', 'aoff', 'woff', 'astr', 'wstr', 'nlpairs', 'pairs'):
            out += self.arr[k]
        out += struct.pack('<I', 0x87654321)
        out += struct.pack('<i', self.num_assets) + self.assets_blob + self.tail
        open(path, 'wb').write(out)
        return len(out)
