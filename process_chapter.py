#!/usr/bin/env python3
"""
process_chapter.py — fully automated BG chapter audio splitter

Usage:
    python3 process_chapter.py <chapter_number> <verse_count>

Examples:
    python3 process_chapter.py 3 43
    python3 process_chapter.py 4 42

Input files expected in raw_data/chapter<N>/:
    - Audio:  any .mp3 file
    - PDF:    any .pdf file

Outputs:
    - Chapter N/Ch N Shloka 0.mp3 … Ch N Shloka M.mp3
    - Chapter N/chapterN-verse-splits-columned.md  (draft — review recommended)
    - raw_data/chapter<N>/whisper_chN.json          (cached; reused on reruns)
    - raw_data/chapter<N>/whisper_chN_words.json
    - chapters/chapters.json                         (updated in place)

Boundary detection algorithm:
    1. Find verse 0 end via first speaker label (sanjaya/arjuna/bhagavan uvāca).
    2. Find colophon ("om tatsaditi") to mark content end.
    3. Compute average verse duration.
    4. Greedy forward search: from each found boundary, look for the largest
       inter-word pause within [current + avg - WINDOW, current + avg + WINDOW].
       If an "uvāca" speaker label lands in that window, use it as a hard anchor.
    5. Verses outside MIN_VERSE_DUR–MAX_VERSE_DUR are flagged for review.
       A hints file lists the top candidate gaps near each flagged verse.
"""

import sys, os, json, ssl, subprocess, re, unicodedata
from pathlib import Path

# ── config ────────────────────────────────────────────────────────────────────

WHISPER_MODEL   = "small"
MIN_VERSE_DUR   = 10.0   # flag if shorter
MAX_VERSE_DUR   = 30.0   # flag if longer
BOUNDARY_WINDOW = 8.0    # ±seconds around expected boundary to search for pause

# ── text normalisation ────────────────────────────────────────────────────────

def strip_diacritics(s: str) -> str:
    """Flatten IAST/Devanagari to plain ASCII for loose matching."""
    # Normalise FIRST (so ā → a + combining macron), then drop combining marks
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()


def normalise_word(w: str) -> str:
    """Strip diacritics, then drop everything that isn't a-z."""
    return re.sub(r"[^a-z]", "", strip_diacritics(w))


def word_contains(whisper_word: str, target: str) -> bool:
    """True if the normalised whisper word contains the normalised target."""
    return target in normalise_word(whisper_word)


# ── file helpers ──────────────────────────────────────────────────────────────

def find_file(directory: Path, patterns: list[str]) -> Path | None:
    for pat in patterns:
        matches = list(directory.glob(pat))
        if matches:
            return matches[0]
    return None

# ── transcription ─────────────────────────────────────────────────────────────

def run_whisper(audio_path: Path, out_json: Path, words_json: Path) -> list[dict]:
    if out_json.exists():
        print(f"  [whisper] cached → {out_json.name}")
    else:
        print(f"  [whisper] transcribing {audio_path.name} (takes a few minutes) …")
        ssl._create_default_https_context = ssl._create_unverified_context
        import whisper
        model = whisper.load_model(WHISPER_MODEL)
        result = model.transcribe(
            str(audio_path),
            language="sa",
            word_timestamps=True,
            verbose=False,
        )
        out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"  [whisper] saved → {out_json.name}")

    result = json.loads(out_json.read_text())
    words = []
    for seg in result["segments"]:
        for w in seg.get("words", []):
            words.append({"word": w["word"].strip(), "start": w["start"], "end": w["end"]})

    words_json.write_text(json.dumps(words, ensure_ascii=False, indent=2))
    print(f"  [whisper] {len(words)} words extracted")
    return words

# ── landmark detection ────────────────────────────────────────────────────────

_SPEAKER_ROOTS = ["sanjaya", "bhagavan", "arjuna", "krishna", "dhritarashtra",
                  "dhrtarashtra", "sanjayas", "shribhagavan"]

def _is_speaker(word: str) -> bool:
    nw = normalise_word(word)
    return any(root in nw for root in _SPEAKER_ROOTS)

def _is_uvaca(word: str) -> bool:
    nw = normalise_word(word)
    return "uvac" in nw or "uvaj" in nw

def find_uvaca_timestamps(words: list[dict]) -> list[float]:
    """
    Find all timestamps where a speaker label (N uvāca) begins.
    Returns sorted list of start times.
    """
    anchors = []
    for i, w in enumerate(words):
        if _is_uvaca(w["word"]):
            # look backward up to 3 words for a speaker name
            for j in range(max(0, i - 3), i + 1):
                if _is_speaker(words[j]["word"]):
                    anchors.append(words[j]["start"])
                    break
    return sorted(set(anchors))


def find_verse0_end(words: list[dict]) -> float | None:
    """Start time of the first speaker label = end of verse 0."""
    anchors = find_uvaca_timestamps(words)
    return anchors[0] if anchors else None


def find_colophon_start(words: list[dict]) -> float | None:
    """Start time of 'om tatsaditi' = end of last verse."""
    for w in words:
        if word_contains(w["word"], "tatsad"):
            return w["start"]
    return None

# ── boundary detection ────────────────────────────────────────────────────────

def best_gap_in_range(words: list[dict], lo: float, hi: float) -> float | None:
    """
    Among all inter-word gaps whose LATER word starts between lo and hi,
    return the start time of that later word (i.e. the split point).
    Returns None if no words fall in range.
    """
    best_gap  = -1.0
    best_time = None

    for i in range(1, len(words)):
        t = words[i]["start"]
        if lo <= t <= hi:
            gap = t - words[i - 1]["start"]
            if gap > best_gap:
                best_gap  = gap
                best_time = t

    return best_time


def detect_verse_starts(
    words: list[dict],
    num_verses: int,
) -> tuple[list[tuple[int, float]], float]:
    """
    Returns (verse_starts, colophon_t).
    verse_starts is a list of (verse_num, start_time) pairs, verse 0 through verse N.
    """
    verse0_end = find_verse0_end(words)
    if verse0_end is None:
        verse0_end = 15.0
        print(f"  [boundary] WARNING: no speaker label found; guessing verse 1 start = {verse0_end:.2f}s")
    else:
        print(f"  [boundary] verse 0 end / verse 1 start: {verse0_end:.2f}s")

    colophon_t = find_colophon_start(words)
    if colophon_t is None:
        colophon_t = words[-1]["start"] - 5.0
        print(f"  [boundary] WARNING: colophon not found; using {colophon_t:.2f}s")
    else:
        print(f"  [boundary] colophon: {colophon_t:.2f}s")

    # Collect all uvāca anchors as hard boundaries
    all_uvaca = find_uvaca_timestamps(words)
    # Filter to range (verse1..colophon) and exclude verse0 itself
    uvaca_set = set(t for t in all_uvaca if t > verse0_end + 1.0 and t < colophon_t - 1.0)
    if uvaca_set:
        print(f"  [boundary] {len(uvaca_set)} additional uvāca anchors found: "
              + ", ".join(f"{t:.1f}s" for t in sorted(uvaca_set)))

    avg_dur = (colophon_t - verse0_end) / num_verses
    print(f"  [boundary] {num_verses} verses, avg {avg_dur:.1f}s each")

    verse_starts = [(0, 0.0), (1, verse0_end)]
    current = verse0_end

    for v in range(2, num_verses + 1):
        expected = current + avg_dur
        lo, hi   = expected - BOUNDARY_WINDOW, expected + BOUNDARY_WINDOW
        hi       = min(hi, colophon_t - 0.5)  # never search past the colophon

        # If a known uvāca anchor falls in the window, prefer it
        anchors_in_window = [t for t in uvaca_set if lo <= t <= hi]
        if anchors_in_window:
            best = min(anchors_in_window, key=lambda t: abs(t - expected))
            verse_starts.append((v, best))
            current = best
        else:
            best = best_gap_in_range(words, lo, hi)
            if best is None:
                # fallback: use expected position
                best = expected
            verse_starts.append((v, best))
            current = best

    return verse_starts, colophon_t

# ── audio splitting ───────────────────────────────────────────────────────────

def split_audio(
    audio_path: Path,
    verse_starts: list[tuple[int, float]],
    colophon_t: float,
    out_dir: Path,
    chapter_num: int,
) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    entries  = []
    flagged  = []

    for i, (vnum, vstart) in enumerate(verse_starts):
        vend = verse_starts[i + 1][1] if i + 1 < len(verse_starts) else colophon_t
        dur  = vend - vstart
        out  = out_dir / f"Ch {chapter_num} Shloka {vnum}.mp3"

        subprocess.run(
            ["ffmpeg", "-y", "-i", str(audio_path),
             "-ss", str(vstart), "-to", str(vend), "-c", "copy", str(out)],
            check=True, capture_output=True,
        )

        flag = ""
        if dur < MIN_VERSE_DUR:
            flag = " *** SHORT"
            flagged.append(vnum)
        elif dur > MAX_VERSE_DUR:
            flag = " *** LONG"
            flagged.append(vnum)

        print(f"  verse {vnum:3d}: {vstart:7.2f}s – {vend:7.2f}s  ({dur:5.2f}s){flag}")
        entries.append({
            "number": vnum,
            "file":   str((out_dir / out.name).relative_to(out_dir.parent)),
        })

    return entries, flagged

# ── review hints ──────────────────────────────────────────────────────────────

def write_review_hints(
    words: list[dict],
    verse_starts: list[tuple[int, float]],
    colophon_t: float,
    flagged: list[int],
    out_path: Path,
):
    """Write a text file with top gap candidates near each flagged verse boundary."""
    if not flagged:
        return

    lines = ["# Verse boundary review hints", "",
             "For each flagged verse, the top 5 inter-word gaps near its boundary are listed.",
             "Find the correct gap, then re-run with corrected timestamps if needed.", ""]

    v_map = dict(verse_starts)

    for vnum in flagged:
        vstart = v_map[vnum]
        vend   = v_map.get(vnum + 1, colophon_t)
        dur    = vend - vstart
        lines.append(f"## Verse {vnum}  ({vstart:.2f}s – {vend:.2f}s, dur={dur:.2f}s)")
        lines.append("")

        # Gather gaps in ±12s window around current boundary
        lo = vstart - 12.0
        hi = vstart + 12.0
        candidates = []
        for i in range(1, len(words)):
            t = words[i]["start"]
            if lo <= t <= hi:
                gap = t - words[i-1]["start"]
                candidates.append((gap, t, words[i-1]["word"], words[i]["word"]))
        candidates.sort(reverse=True)

        lines.append(f"  Top gaps near verse {vnum} boundary:")
        for gap, t, prev, nxt in candidates[:5]:
            lines.append(f"    gap={gap:.2f}s  at {t:.2f}s  '{prev}' → '{nxt}'")
        lines.append("")

    out_path.write_text("\n".join(lines))
    print(f"  [review] hints → {out_path.name}")

# ── PDF verse extraction ──────────────────────────────────────────────────────

def extract_pdf_text(pdf_path: Path, raw_txt: Path) -> str:
    if raw_txt.exists():
        print(f"  [pdf] cached → {raw_txt.name}")
        return raw_txt.read_text()

    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), str(raw_txt)],
        capture_output=True,
    )
    if result.returncode != 0:
        print("  [pdf] WARNING: pdftotext failed (brew install poppler)")
        return ""
    print(f"  [pdf] extracted → {raw_txt.name}")
    return raw_txt.read_text()


def pdf_to_verse_markdown(pdf_text: str, chapter_num: int, num_verses: int) -> str:
    """
    Best-effort: split raw PDF text on ||N|| verse markers and produce
    the columned-markdown template. Page annotations are left as placeholders.
    """
    page_header_re = re.compile(
        r"^\s*\d+\.\s+\S.*Yog|^\s*\d+/\d+\s*$|^\s*\d+\. Sāṅkhya", re.IGNORECASE
    )
    verse_marker_re = re.compile(r"\|\|(\d+)\|\|")

    def clean(text: str) -> str:
        out = []
        for ln in text.splitlines():
            if not page_header_re.match(ln):
                out.append(ln.rstrip())
        return "\n".join(out).strip()

    # Split on ||N|| markers
    chunks    = re.split(r"(\|\|\d+\|\|)", pdf_text)
    verse_map = {}
    header    = ""
    buf       = []
    cur_num   = None

    for chunk in chunks:
        m = verse_marker_re.fullmatch(chunk.strip())
        if m:
            vnum = int(m.group(1))
            text = "\n".join(buf).strip()
            if cur_num is None:
                header = text
            else:
                verse_map[cur_num] = text
            buf = []
            cur_num = vnum
        else:
            buf.append(chunk)

    if cur_num is not None:
        verse_map[cur_num] = "\n".join(buf).strip()

    md = [
        f"# Bhagavad Gita Chapter {chapter_num} — Verse Split Review",
        "",
        f"- verses captured: {num_verses} (+ verse 0 header)",
        "",
        "## Verse 0",
        "",
        clean(header),
        "",
        "> page 1 (header, above column split)",
        "",
    ]
    for v in range(1, num_verses + 1):
        text = clean(verse_map.get(v, f"[verse {v} not found in PDF]"))
        md += [
            f"## Verse {v}",
            "",
            text + f" ||{v}||",
            "",
            "> page ? (left/right half)  ← update",
            "",
        ]

    return "\n".join(md)

# ── chapters.json ─────────────────────────────────────────────────────────────

def update_chapters_json(json_path: Path, chapter_num: int, entries: list[dict]):
    data    = json.loads(json_path.read_text())
    chapter = {
        "id":     f"chapter-{chapter_num}",
        "title":  f"Chapter {chapter_num}",
        "verses": entries,
    }
    chapters = data["chapters"]
    for i, ch in enumerate(chapters):
        if ch["id"] == f"chapter-{chapter_num}":
            chapters[i] = chapter
            print(f"  [json] replaced chapter-{chapter_num}")
            break
    else:
        chapters.append(chapter)
        print(f"  [json] appended chapter-{chapter_num}")

    json_path.write_text(json.dumps(data, indent=2) + "\n")

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    chapter_num = int(sys.argv[1])
    num_verses  = int(sys.argv[2])

    root      = Path(__file__).parent
    raw_dir   = root / "raw_data" / f"chapter{chapter_num}"
    out_dir   = root / f"Chapter {chapter_num}"
    json_path = root / "chapters" / "chapters.json"
    raw_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Chapter {chapter_num}  ({num_verses} verses)")
    print(f"{'='*60}")

    # 1. locate sources
    audio = find_file(raw_dir, ["*.mp3", "*.m4a", "*.wav"])
    pdf   = find_file(raw_dir, ["*.pdf"])
    if audio is None:
        print(f"\nERROR: no audio file in {raw_dir}")
        sys.exit(1)
    print(f"\n[1/5] audio: {audio.relative_to(root)}")
    print(f"[1/5] pdf:   {pdf.relative_to(root) if pdf else 'not found'}")

    # 2. whisper
    print(f"\n[2/5] Whisper transcription")
    w_json  = raw_dir / f"whisper_ch{chapter_num}.json"
    w_words = raw_dir / f"whisper_ch{chapter_num}_words.json"
    words = run_whisper(audio, w_json, w_words)

    # 3. boundaries
    print(f"\n[3/5] Verse boundary detection")
    verse_starts, colophon_t = detect_verse_starts(words, num_verses)

    # 4. split
    print(f"\n[4/5] Splitting audio → Chapter {chapter_num}/")
    entries, flagged = split_audio(audio, verse_starts, colophon_t, out_dir, chapter_num)

    # 4b. review hints for flagged verses
    if flagged:
        hints_path = raw_dir / f"ch{chapter_num}_review_hints.txt"
        write_review_hints(words, verse_starts, colophon_t, flagged, hints_path)

    # 5. PDF verse text
    print(f"\n[5/5] Verse text extraction")
    if pdf:
        raw_txt  = raw_dir / f"ch{chapter_num}_raw.txt"
        pdf_text = extract_pdf_text(pdf, raw_txt)
        if pdf_text:
            md      = pdf_to_verse_markdown(pdf_text, chapter_num, num_verses)
            md_path = out_dir / f"chapter{chapter_num}-verse-splits-columned.md"
            md_path.write_text(md)
            print(f"  [pdf] draft → {md_path.relative_to(root)}")
            print(f"  [pdf] NOTE: page annotations marked '← update' need review")
    else:
        print("  [pdf] skipped")

    # 6. chapters.json
    print(f"\n[6/6] chapters/chapters.json")
    update_chapters_json(json_path, chapter_num, entries)

    # summary
    durations = []
    for i, (vnum, vs) in enumerate(verse_starts):
        ve = verse_starts[i+1][1] if i+1 < len(verse_starts) else colophon_t
        durations.append(ve - vs)

    print(f"\n{'='*60}")
    print(f"  Done — {len(verse_starts)} files in Chapter {chapter_num}/")
    print(f"  Duration range: {min(durations):.1f}s – {max(durations):.1f}s")
    if flagged:
        print(f"  ⚠  Review flagged verses: {flagged}")
        print(f"     Hints → raw_data/chapter{chapter_num}/ch{chapter_num}_review_hints.txt")
        print(f"     Words → raw_data/chapter{chapter_num}/whisper_ch{chapter_num}_words.json")
    else:
        print(f"  All durations within {MIN_VERSE_DUR}–{MAX_VERSE_DUR}s ✓")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
