import json
full_path = '/Users/faizan/.gemini/antigravity/brain/5048cda7-761c-4bb4-b7d7-88a56df02f96/.system_generated/logs/transcript_full.jsonl'
with open(full_path, 'r') as f:
    for idx, line in enumerate(f):
        if idx == 140:
            data = json.loads(line)
            # Find in all fields
            for k, v in data.items():
                if isinstance(v, str) and 'Campaign Name,Campaign Type,Commission' in v:
                    pos = v.find('Campaign Name,Campaign Type,Commission')
                    # Find end
                    end = v.find('</USER_REQUEST>', pos)
                    if end == -1:
                        end = v.find('```', pos)
                    if end == -1:
                        end = len(v)
                    cuelinks_csv = v[pos:end].strip()
                    with open('/Users/faizan/.gemini/antigravity/scratch/affiliate-etl-platform/backend/sample_data/cuelinks_real.csv', 'w') as out:
                        out.write(cuelinks_csv)
                    print(f"Key {k}, wrote {len(cuelinks_csv.splitlines())} lines to cuelinks_real.csv")
