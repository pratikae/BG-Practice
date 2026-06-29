import json

with open('/Users/pratikaeswaran/VSCode/bg_program/raw_data/chapter2/whisper_ch2_words.json') as f:
    words = json.load(f)

# Find gaps between consecutive word starts (potential verse boundaries)
gaps = []
for i in range(1, len(words)):
    gap = words[i]['start'] - words[i-1]['start']
    gaps.append((gap, i, words[i-1]['start'], words[i]['start'], words[i-1]['word'], words[i]['word']))

gaps.sort(reverse=True)
print("Top 100 gaps (largest pauses):")
for gap, idx, prev_start, next_start, prev_word, next_word in gaps[:100]:
    print(f"  gap={gap:5.2f}s  at {prev_start:7.2f}s -> {next_start:7.2f}s  word[{idx-1}]='{prev_word}' -> word[{idx}]='{next_word}'")
