import ssl, whisper, json

ssl._create_default_https_context = ssl._create_unverified_context  # fix macOS cert issue

print("Loading Whisper model...")
model = whisper.load_model("small")

print("Transcribing Chapter 2 audio (this takes a few minutes)...")
result = model.transcribe(
    "1_Ch 2 Complete.mp3",
    language="sa",
    word_timestamps=True,
    verbose=False
)

with open("raw_data/chapter2/whisper_ch2.json", "w") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("Done. Saved to raw_data/chapter2/whisper_ch2.json")

# Print a flat word list for review
words = []
for seg in result["segments"]:
    for w in seg.get("words", []):
        words.append({"word": w["word"].strip(), "start": w["start"], "end": w["end"]})

with open("raw_data/chapter2/whisper_ch2_words.json", "w") as f:
    json.dump(words, f, ensure_ascii=False, indent=2)

print(f"Total words: {len(words)}")
print("Word list saved to raw_data/chapter2/whisper_ch2_words.json")

# Print first 50 words for quick review
print("\nFirst 50 words:")
for w in words[:50]:
    print(f"  {w['start']:7.2f}s  {w['word']}")
