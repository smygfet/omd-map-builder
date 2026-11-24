# Draw a Map Maker v2 map as a 1000x564 PNG mission tile (pure Python, no libraries).
import struct, zlib

FLOOR = {'museum': '#b8a27f', 'drydocks': '#8b7356', 'cobblestone': '#8a8780', 'plaza': '#a99273', 'wood': '#9b7042',
         'stoneblock': '#9a958b', 'darkstone': '#5f5d5a', 'squaretile': '#a39d92', 'brick': '#a5654a', 'brickborder': '#9c6a52',
         'terracotta': '#b86f4c', 'pavement': '#8f8a7e', 'resort': '#c9b48e', 'parquet': '#8a5a34', 'mud': '#6b5640',
         'dirt': '#7a6648', 'ceramic': '#b9b4a8',
         'museumB': '#b3a07e', 'museumD': '#a8966f', 'cobblefan': '#8d8a82', 'scattered': '#8e8676', 'scattereddk': '#6e6a62', 'plazacross': '#a99779', 'plazablue': '#8f98a3', 'plazasquare': '#a8957a', 'plazaB': '#a48f70', 'plazaC': '#9f8c70', 'plazaE': '#ad9a7b', 'stonefloor': '#8f8c86', 'woodfloor': '#8f6a44', 'resortB': '#c4ae88', 'dirtB': '#75603f', 'terracottaB': '#b5704e',
         'grass': '#5f7d38', 'water': '#3d6f8a'}
WALL = {'stonewall': '#77746e', 'stonehouse': '#8a8174', 'plaster': '#cdbf9f', 'stucco': '#d9cfbb', 'adobe': '#b98d61', 'manor': '#6a4a30', 'castle': '#8f8b83'}
CEIL = {'planks': '#8a6239', 'library': '#5b3e27', 'manor': '#6d4b2f'}


def rgb(h): return [int(h[i:i + 2], 16) for i in (1, 3, 5)]
def shade(c, f):
    f = max(-1.0, min(1.0, f))                     # heights now go to 9 m (and decks higher): never past white or black
    return [max(0, min(255, int(v + ((255 if f > 0 else 0) - v) * abs(f)))) for v in c]


def pixels(d, W=1000, H=564):
    px = [[22, 26, 32] for _ in range(W * H)]
    cols, rows, g, st = d['cols'], d['rows'], d['grid'], d['styles']
    fc, wc, cc = rgb(FLOOR.get(st.get('floor'), '#8b7356')), rgb(WALL.get(st.get('wall'), '#77746e')), rgb(CEIL.get(st.get('ceiling'), '#6d4b2f'))   # unknown style: a neutral colour, never a crash
    s = int(min((W - 60) / cols, (H - 60) / rows)); ox = (W - s * cols) // 2; oy = (H - s * rows) // 2

    def rect(x0, y0, x1, y1, col):
        for y in range(max(0, y0), min(H, y1)):
            row = y * W
            for x in range(max(0, x0), min(W, x1)): px[row + x] = col
    for y in range(rows):
        for x in range(cols):
            c = g[y * cols + x]; X, Y = ox + x * s, oy + y * s
            if c['t'] == 'v': col = [12, 15, 19]
            elif c['t'] == 'w':
                rect(X, Y, X + s, Y + s, shade(wc, -0.2)); i = max(1, s // 7)
                rect(X + i, Y + i, X + s - i, Y + s - i, wc); continue
            else:
                col = shade(rgb(FLOOR[c['fs']]) if c.get('fs') in FLOOR else fc, -0.12 + c['h'] * 0.06 + (0.03 if c['t'] == 'r' else 0))
                if c.get('c'): col = [(a * 2 + b * 3) // 5 for a, b in zip(col, cc)]
            rect(X, Y, X + s - 1, Y + s - 1, col)
            if c.get('b') and c['t'] != 'w':              # upper deck: a lighter slab with a dark edge
                dk = shade(rgb(FLOOR[c['fs']]) if c.get('fs') in FLOOR else fc, -0.12 + c['b'] * 0.06)
                rect(X, Y, X + s - 1, Y + s - 1, shade(dk, -0.5)); i = max(1, s // 8); rect(X + i, Y + i, X + s - 1 - i, Y + s - 1 - i, dk)
            if c.get('p') and c['t'] == 'f':
                i = max(1, s // 4); rect(X + i, Y + i, X + s - 1 - i, Y + s - 1 - i, shade(col, -0.45))
    for m in d['markers']:
        cx, cy, r = ox + int((m['x'] + .5) * s), oy + int((m['y'] + .5) * s), max(3, int(s * 0.45))
        col = [82, 198, 230] if m['k'] == 'rift' else [229, 89, 77] if m['k'] == 'spawn' else None
        if not col: continue
        for y in range(cy - r - 2, cy + r + 3):
            for x in range(cx - r - 2, cx + r + 3):
                dx, dy = abs(x - cx), abs(y - cy)
                inside = (dx + dy <= r * 1.3) if m['k'] == 'rift' else (dx * dx + dy * dy <= r * r)
                if inside and 0 <= x < W and 0 <= y < H: px[y * W + x] = col
    return px


def bgra(d, W=1000, H=564):
    """Raw B8G8R8A8 pixels, top row first (what the cooked texture stores)."""
    return b''.join(bytes((p[2], p[1], p[0], 255)) for p in pixels(d, W, H))


def render(d, path, W=1000, H=564):
    px = pixels(d, W, H)
    raw = b''.join(b'\0' + bytes(v for p in px[y * W:(y + 1) * W] for v in p) for y in range(H))
    def chunk(t, data): return struct.pack('>I', len(data)) + t + data + struct.pack('>I', zlib.crc32(t + data) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b'')
    open(path, 'wb').write(png)
