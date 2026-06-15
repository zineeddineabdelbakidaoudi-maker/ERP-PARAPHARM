import json
import os

transcript_path = r"C:\Users\pc gamer\.gemini\antigravity\brain\f913916e-d1b7-4254-b7c3-b44686d3629d\.system_generated\logs\transcript.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        if "SECTION 6" in line or "SECTION 7" in line:
            try:
                data = json.loads(line)
                content = data.get("content", "")
                if content and "Reply to Antigravity:" in content:
                    print(f"Line {idx} matches criteria. Length: {len(content)}")
                    with open(f"untruncated_request_{idx}.txt", "w", encoding="utf-8") as out:
                        out.write(content)
            except Exception as e:
                print("Error on line", idx, e)
