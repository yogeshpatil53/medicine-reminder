import struct
import zlib
from pathlib import Path

def create_png(filename, width, height):
    # Generates a PNG with a medical cross and pill design
    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = zlib.crc32(c) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + c + struct.pack(">I", crc)

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)) # 8-bit RGBA

    rows = []
    cx, cy = width / 2, height / 2
    r_radius = width * 0.44

    for y in range(height):
        row = bytearray(b"\x00") # filter byte 0
        for x in range(width):
            dx = x - cx
            dy = y - cy
            dist = (dx * dx + dy * dy) ** 0.5

            if dist > r_radius:
                # Transparent outside circle
                row.extend([0, 0, 0, 0])
                continue

            # Background: Vibrant medical blue gradient
            factor = (y / height)
            bg_r = int(37 + (29 - 37) * factor)   # #2563EB to #1D4ED8
            bg_g = int(99 + (78 - 99) * factor)
            bg_b = int(235 + (216 - 235) * factor)
            bg_a = 255

            # Medical Cross dimensions
            cross_arm = width * 0.12
            cross_len = width * 0.28

            in_vert = (abs(dx) <= cross_arm) and (abs(dy) <= cross_len)
            in_horiz = (abs(dy) <= cross_arm) and (abs(dx) <= cross_len)

            if in_vert or in_horiz:
                # Crisp White Medical Cross with soft glow
                row.extend([255, 255, 255, 255])
            else:
                row.extend([bg_r, bg_g, bg_b, bg_a])

        rows.append(bytes(row))

    raw_data = b"".join(rows)
    idat = chunk(b"IDAT", zlib.compress(raw_data, 9))
    iend = chunk(b"IEND", b"")

    with open(filename, "wb") as f:
        f.write(header + ihdr + idat + iend)

out_dir = Path("static")
out_dir.mkdir(exist_ok=True)
create_png(out_dir / "icon-192.png", 192, 192)
create_png(out_dir / "icon-512.png", 512, 512)
print("PWA icons generated successfully!")
