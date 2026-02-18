"""Fetch remaining SiCProD data: functions and relations."""
import json
import sys
import io
import urllib.request
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_API = 'https://sicprod.acdh-dev.oeaw.ac.at/apis/api'
OUT_DIR = 'c:/Users/chstn/Desktop/data/DHCraft/Projekte/Git/DoCTA/data'

def fetch_paginated(endpoint, limit=500):
    results = []
    offset = 0
    while True:
        url = f'{BASE_API}/{endpoint}/?format=json&limit={limit}&offset={offset}'
        print(f'  {endpoint} offset={offset}...', end=' ', flush=True)
        retries = 3
        data = None
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, headers={'Accept': 'application/json'})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                break
            except Exception as e:
                print(f'retry {attempt+1}...', end=' ', flush=True)
                time.sleep(3)
        if data is None:
            print(f'FAILED after {retries} retries')
            break
        batch = data.get('results', [])
        results.extend(batch)
        count = data.get('count', 0)
        print(f'{len(batch)} ({len(results)}/{count})', flush=True)
        if not data.get('next'):
            break
        offset += limit
        time.sleep(0.5)
    return results

import re

def extract_relation_type(url):
    m = re.search(r'apis_ontology\.(\w+)/\d+/', url)
    return m.group(1) if m else 'unknown'

def extract_id_from_url(url):
    m = re.search(r'/(\d+)/\?', url)
    return int(m.group(1)) if m else None

# Fetch functions
print('=== Functions ===')
raw_functions = fetch_paginated('apis_ontology.function')
functions = []
for f in raw_functions:
    functions.append({
        'id': f['id'],
        'name': f.get('name', ''),
        'start_date': f.get('start_date_written') or '',
        'end_date': f.get('end_date_written') or '',
        'alternative_label': f.get('alternative_label', []),
    })
with open(f'{OUT_DIR}/functions.json', 'w', encoding='utf-8') as fout:
    json.dump(functions, fout, ensure_ascii=False, indent=1)
print(f'Saved {len(functions)} functions')

# Fetch relations
print('\n=== Relations (42.893 — this takes a while) ===')
raw_relations = fetch_paginated('relations.relation')
relations = []
for r in raw_relations:
    subj = r.get('subj', {})
    obj = r.get('obj', {})
    relations.append({
        'relation_type': extract_relation_type(r.get('url', '')),
        'subj_id': extract_id_from_url(subj.get('url', '')),
        'subj_type': subj.get('content_type_name', ''),
        'subj_label': subj.get('label', ''),
        'obj_id': extract_id_from_url(obj.get('url', '')),
        'obj_type': obj.get('content_type_name', ''),
        'obj_label': obj.get('label', ''),
    })
with open(f'{OUT_DIR}/relations.json', 'w', encoding='utf-8') as fout:
    json.dump(relations, fout, ensure_ascii=False, indent=1)
print(f'Saved {len(relations)} relations')

# Distinct relation types
rel_types = {}
for r in relations:
    rt = r['relation_type']
    rel_types[rt] = rel_types.get(rt, 0) + 1
print(f'\nDistinct relation types: {len(rel_types)}')
for rt, count in sorted(rel_types.items(), key=lambda x: -x[1])[:20]:
    print(f'  {rt:<30} {count:>6}')
