import subprocess, os

verse_starts = [
    (0,   0.00),
    (1,  13.08),
    (2,  31.14),
    (3,  48.76),
    (4,  69.12),
    (5,  83.36),
    (6,  97.94),
    (7, 114.92),
    (8, 129.36),
    (9, 145.16),
    (10, 162.58),
    (11, 179.06),
    (12, 195.82),
    (13, 214.62),
    (14, 232.24),
    (15, 248.02),
    (16, 265.40),
    (17, 281.92),
    (18, 299.08),
    (19, 314.48),
    (20, 329.04),
    (21, 344.06),
    (22, 360.62),
    (23, 374.76),
    (24, 390.54),
    (25, 406.80),
    (26, 424.68),
    (27, 441.06),
    (28, 454.58),
    (29, 469.28),
    (30, 486.14),
    (31, 501.04),
    (32, 519.56),
    (33, 533.42),
    (34, 547.58),
    (35, 563.72),
    (36, 578.80),
    (37, 595.80),
    (38, 614.48),
    (39, 633.14),
    (40, 648.80),
    (41, 664.66),
    (42, 680.58),
    (43, 697.56),
]
colophon_start = 714.36

src = "raw_data/1_Ch 3 Complete.mp3"
out_dir = "Chapter 3"
os.makedirs(out_dir, exist_ok=True)

for i, (vnum, vstart) in enumerate(verse_starts):
    vend = verse_starts[i + 1][1] if i + 1 < len(verse_starts) else colophon_start
    out = f"{out_dir}/Ch 3 Shloka {vnum}.mp3"
    duration = vend - vstart
    subprocess.run([
        "ffmpeg", "-y", "-i", src,
        "-ss", str(vstart), "-to", str(vend),
        "-c", "copy", out
    ], check=True, capture_output=True)
    flag = " *** CHECK (short)" if duration < 10 else (" *** CHECK (long)" if duration > 35 else "")
    print(f"Verse {vnum:2d}: {vstart:7.2f}s – {vend:7.2f}s  ({duration:5.2f}s){flag}  → {out}")

print("\nDone!")
