import ssl, whisper, json, sys
sys.path.insert(0, '/Users/pratikaeswaran/VSCode/bg_program')

ssl._create_default_https_context = ssl._create_unverified_context

print("Loading model...")
model = whisper.load_model("small")
print("Transcribing...")
result = model.transcribe(
    "/Users/pratikaeswaran/VSCode/bg_program/raw_data/1_Ch 3 Complete.mp3",
    language="sa", word_timestamps=True, verbose=False,
)

with open("/Users/pratikaeswaran/VSCode/bg_program/raw_data/chapter3/whisper_ch3.json", "w") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

words = []
for seg in result["segments"]:
    for w in seg.get("words", []):
        words.append({"word": w["word"].strip(), "start": w["start"], "end": w["end"]})

with open("/Users/pratikaeswaran/VSCode/bg_program/raw_data/chapter3/whisper_ch3_words.json", "w") as f:
    json.dump(words, f, ensure_ascii=False, indent=2)

print(f"Done — {len(words)} words")
for w in words[:30]:
    print(f"  {w['start']:7.2f}s  {w['word']}")
