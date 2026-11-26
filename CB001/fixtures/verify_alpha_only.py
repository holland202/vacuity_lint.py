import argparse, io, sys
from PIL import Image, __version__ as PILV

def build(ink):
    # 4x4 transparent icon with an opaque diagonal-ish pattern in `ink`
    img = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    for x, y in [(0, 0), (1, 1), (2, 2), (3, 3), (1, 2), (2, 1)]:
        img.putpixel((x, y), ink + (255,))
    return img

def reopen(im):
    b = io.BytesIO(); im.save(b, "PNG"); b.seek(0)
    return Image.open(b).convert("RGBA")

def two_ways(ink):
    src = build(ink)
    direct = reopen(src.resize((2, 2), Image.LANCZOS))
    alpha = src.getchannel("A").resize((2, 2), Image.LANCZOS)
    masked = Image.new("RGBA", (2, 2), (0, 0, 0, 0)); masked.putalpha(alpha)
    return list(direct.getdata()), list(reopen(masked).getdata())

ap = argparse.ArgumentParser(); ap.add_argument("--ink", default="0,0,0")
ink = tuple(int(v) for v in ap.parse_args().ink.split(","))
d, m = two_ways(ink)
print(f"python={sys.version.split()[0]} pillow={PILV} ink={ink}")
for i, (a, b) in enumerate(zip(d, m)):
    print(f"px{i} direct={a} masked={b}")
bad = [i for i, (a, b) in enumerate(zip(d, m)) if a[3] != b[3]]
print("alpha-only compare:", "MISMATCH at " + str(bad) if bad else "match")
sys.exit(1 if bad else 0)
