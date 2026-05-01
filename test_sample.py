import json
from pathlib import Path

path = Path('docs/idiom-dictionary-network/data/idioms_phonetic.json')
if not path.exists():
    path = Path('output/idioms_phonetic.json')
    
data = json.loads(path.read_text('utf-8'))

samples = []
for item in data:
    idiom = item['idiom']
    if 'someone or something' in idiom and not any('someone or something' in s['idiom'] for s in samples):
        samples.append(item)
    elif 'doing something' in idiom and not any('doing something' in s['idiom'] for s in samples):
        samples.append(item)
    elif 'oneself' in idiom and not any('oneself' in s['idiom'] for s in samples):
        samples.append(item)
    elif 'someone\'s' in idiom and not any('someone\'s' in s['idiom'] for s in samples):
        samples.append(item)
    elif '(something)' in idiom and not any('(something)' in s['idiom'] for s in samples):
        samples.append(item)
    if len(samples) >= 5: break

print('SAMPLES:')
for s in samples:
    print(f"{s['idiom']} | current tokens: {s['tokens']} | rhyme: {s['rhyme_key']}")
