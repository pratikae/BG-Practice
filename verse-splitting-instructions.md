# Chapter Processing Instructions — Bhagavad Gita Practice App

Complete pipeline for adding a new chapter: PDF verse extraction → audio splitting → app wiring.

---

## Prerequisites (one-time setup)

```bash
brew install ffmpeg
pip3 install openai-whisper
```

---

## Part 1 — Extract Verses from the PDF

### PDF Layout

Each page has a **two-column layout** split by a vertical line:
- Read left column top-to-bottom, then right column top-to-bottom, page by page.
- The very top of page 1 (above the column split) is the **title block** — treat it as Verse 0.

### Verse 0 (Title Block)

Capture whatever is in the pre-column header at the top of page 1. For Chapter 1 it looks like:

```
|| Äm Çré Paramätman1 Namaù||
|| Atha Çrémad-Bhagavad-Gétä ||
|| Atha Prathamo'dhyäyaù ||
Arjuna-Viñäda-Yogaù
```

Output this as **Verse 0** at the top of the Markdown document.

### Closing Colophon (Exclude)

The very last line of each chapter is a closing colophon. Do not include it as a verse. It looks like:

```
||om tatsaditi çrémadbhagavadgétäsu upaniñatsu brahmavidyäyäà ...||
```

### How to Extract Verses

1. Use OCR or PDF text extraction on the chapter PDF.
2. Identify the column boundary on each page (left vs. right).
3. Extract text in left-column order first, then right-column order, for each page.
4. Split on verse markers — each verse ends with `||N||` (where N is the verse number).
5. Keep speaker labels (e.g. `dhåtaräñöra uväca -`, `saïjaya uväca -`, `arjuna uväca -`) with the verse block they introduce.

### Handling OCR Artifacts

The title block often leaks into nearby verses (especially the first verse in the right column). When this happens:
- Remove any title-block fragments from within verse text.
- Fragments look like: `iñäda-Yºgaù`, `hamº'dhyäyaù ||`, `d-Bhagavad-Gétä ||`
- Common OCR substitutions: `¹` / `º` stand in for vowel diacritics; `1` at end of word is a diacritic artifact.

### Output Format

Produce a file named `chapterN-verse-splits-columned.md`:

```markdown
# Bhagavad Gita Chapter N — Verse Split Review

- verses captured: X (+ verse 0 header)

## Verse 0

[title block text here]

> page 1 (header, above column split)

## Verse 1

[speaker label if present]
[verse lines]
||1||

> page P (left/right half)

## Verse 2
...
```

### Quality Checks

- [ ] Verse 0 is present and contains the title block
- [ ] Verse numbering is sequential with no gaps
- [ ] No title-block fragments appear inside verse text
- [ ] Closing colophon is excluded
- [ ] Each verse has its `||N||` marker at the end
- [ ] Speaker labels (`uväca`) are preserved with the correct verse
- [ ] Source page annotations (left/right half) are correct

---

## Part 2 — Split the Complete Audio into Verses

The audio must be split using **Whisper** for word-level timestamp alignment, not silence detection alone (Sanskrit verse pauses are too uniform to distinguish by duration).

### Step 1 — Transcribe with Whisper

```python
import ssl, whisper, json

ssl._create_default_https_context = ssl._create_unverified_context  # fix macOS cert issue

model = whisper.load_model("small")
result = model.transcribe(
    "N_Ch N Complete.mp3",
    language="sa",
    word_timestamps=True,
    verbose=False
)

with open("whisper_chN.json", "w") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
```

This produces a JSON file with word-level timestamps. Each word entry looks like:
```json
{ "word": "dhritarāśtra", "start": 14.78, "end": 16.96 }
```

### Step 2 — Identify Verse Boundaries

Flatten all words from the JSON:

```python
words = []
for seg in result["segments"]:
    for w in seg.get("words", []):
        words.append({"word": w["word"].strip(), "start": w["start"], "end": w["end"]})
```

**Key landmarks to find:**
- **Verse 0 ends / Verse 1 begins**: find the first occurrence of the chapter's opening speaker label (e.g. `dhritarāśtra` / `dhrtarastra`). That word's `start` time is where Verse 1 begins. Everything before it is Verse 0.
- **Speaker labels** (`sanjaya uvāca`, `arjuna uvāca`) mark the start of the verse they appear in — search the word list for `sanjaya` or `arjuna` followed within 2 words by `uvāca`/`uvāja`.
- **Closing colophon**: find `om tatsaditi` (or `tatsaditi`). Verse 47 ends at that word's `start` time.

**For all other verses**, read through the word list sequentially. Each verse has 4 lines of ~3–4 seconds each. Identify where each verse's first distinctive word appears and note its `start` timestamp.

Tips:
- Print all words with timestamps and read through them against the verse text from the PDF.
- Whisper renders Sanskrit in IAST/Devanagari; match loosely (e.g. `pashyaitāṁ` = `paçyaitäà`, `sanjaya` = `saïjaya`).
- The colophon `om tatsaditi` signals the absolute end — Verse N ends there.

### Step 3 — Split the Audio

Once you have a list of `(verse_number, start_time)` pairs plus the colophon start time:

```python
import subprocess, os

verse_starts = [
    (0,  0.0),        # header always starts at 0
    (1,  14.78),      # replace with actual values
    (2,  35.18),
    # ... all verses ...
    (47, 785.68),
]
colophon_start = 804.0   # use the silence boundary BEFORE "om tatsaditi", not the Whisper word timestamp

src = "raw_data/N_Ch N Complete.mp3"
out_dir = "Chapter N"
os.makedirs(out_dir, exist_ok=True)

for i, (vnum, vstart) in enumerate(verse_starts):
    vend = verse_starts[i + 1][1] if i + 1 < len(verse_starts) else colophon_start
    out = f"{out_dir}/Ch N Shloka {vnum}.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-i", src,
        "-ss", str(vstart), "-to", str(vend),
        "-acodec", "libmp3lame", "-q:a", "2", out   # transcode — do NOT use -c copy (causes frame-end glitches)
    ], check=True)
    print(f"Verse {vnum}: {vstart:.2f}s–{vend:.2f}s → {out}")

# Colophon: from colophon_start to end of file
subprocess.run([
    "ffmpeg", "-y", "-i", src,
    "-ss", str(colophon_start),
    "-acodec", "libmp3lame", "-q:a", "2",
    f"{out_dir}/Ch N Colophon.mp3"
], check=True)
print(f"Colophon: {colophon_start:.2f}s–end → {out_dir}/Ch N Colophon.mp3")
```

Expected verse durations: 14–22 seconds each. Flag any verse shorter than 10s or longer than 30s for manual review.

**Finding the clean colophon cut point:**

The Whisper timestamp for "om tatsaditi" often lands inside the preceding silence. Use `ffmpeg silencedetect` to find the silence boundary instead:

```bash
ffmpeg -ss <whisper_tatsad_time - 5> -t 10 -i "raw_data/N_Ch N Complete.mp3" \
  -af "silencedetect=noise=-35dB:d=0.3" -f null - 2>&1 | grep silence
```

Pick the `silence_start` immediately before the "om" word as your `colophon_start`. This lands the cut cleanly inside the gap rather than mid-silence.

---

## Part 3 — Wire Up the App

### Update `chapters/chapters.json`

Add a new chapter object. Verse 0 must be **first** with `"type": "intro"`, and the colophon must be **last** with `"type": "colophon"`. Regular verses go in between.

```json
{
  "id": "chapter-N",
  "title": "Chapter N",
  "verses": [
    { "number": 0, "type": "intro", "file": "Chapter N/Ch N Shloka 0.mp3" },
    { "number": 1, "file": "Chapter N/Ch N Shloka 1.mp3" },
    { "number": 2, "file": "Chapter N/Ch N Shloka 2.mp3" },
    ...
    { "number": M, "file": "Chapter N/Ch N Shloka M.mp3" },
    { "number": M+1, "type": "colophon", "file": "Chapter N/Ch N Colophon.mp3" }
  ]
}
```

The colophon verse number must be exactly `M + 1` (one past the last regular verse). The app uses this numbering to determine gap durations:
- In odd mode, verse M (if M is odd) → colophon: `M+1 === M+1`, so no gap.
- In even mode, verse M-1 (if M-1 is even) → colophon: `(M-1)+1 = M ≠ M+1`, so a gap of verse M's duration plays.

The app (`app.js`) automatically handles both special verses for all chapters:
- Intro (`type: "intro"`) always plays first regardless of odd/even mode.
- Colophon (`type: "colophon"`) always plays last regardless of odd/even mode.
- Gaps before the colophon follow the same odd/even logic as regular verses.
- Status shows "intro" and "closing prayer" respectively.

### File and Directory Naming Convention

| Asset | Path |
|---|---|
| Complete audio | `raw_data/N_Ch N Complete.mp3` |
| Verse files | `Chapter N/Ch N Shloka 0.mp3` … `Ch N Shloka M.mp3` |
| Colophon file | `Chapter N/Ch N Colophon.mp3` |
| chapters.json | `chapters/chapters.json` (shared across all chapters) |
| PDF | `0N_Chapter_English.pdf` |
| Verse text | `Chapter N/chapterN-verse-splits-columned.md` |

### Quality Checks

- [ ] `chapters.json` has the new chapter with verse 0 (`type: "intro"`) first
- [ ] Colophon (`type: "colophon"`, number = M+1) is the last entry
- [ ] All verse files exist in `Chapter N/` and are playable
- [ ] Verse 0 plays the title block (ॐ śrī … chapter name … yoga name)
- [ ] Verse 1 starts cleanly with the first verse content (not the title block)
- [ ] Colophon plays "om tatsaditi…" and does not include any verse content
- [ ] Spot-check several verses mid-chapter by clicking them in the playlist
- [ ] Odd mode: plays intro → odd verses with even gaps → colophon
- [ ] Even mode: plays intro → even verses with odd gaps → colophon (gap for last odd verse before colophon if applicable)
