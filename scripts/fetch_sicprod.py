"""Fetch all SiCProD entities and relations as static JSON for the prototype.

API: https://sicprod.acdh-dev.oeaw.ac.at/apis/api/
No auth needed (public API).
"""
import json
import sys
import io
import urllib.request
import urllib.parse
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_API = 'https://sicprod.acdh-dev.oeaw.ac.at/apis/api'
OUT_DIR = 'c:/Users/chstn/Desktop/data/DHCraft/Projekte/Git/DoCTA/data'

def fetch_paginated(endpoint, limit=500):
    """Fetch all results from a paginated API endpoint."""
    results = []
    offset = 0
    while True:
        url = f'{BASE_API}/{endpoint}/?format=json&limit={limit}&offset={offset}'
        print(f'  Fetching {endpoint} offset={offset}...', end=' ')
        try:
            req = urllib.request.Request(url, headers={'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            print(f'ERROR: {e}')
            # Retry once after short wait
            time.sleep(2)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
            except Exception as e2:
                print(f'FATAL: {e2}')
                break

        batch = data.get('results', [])
        results.extend(batch)
        count = data.get('count', 0)
        print(f'{len(batch)} items (total: {len(results)}/{count})')

        if not data.get('next'):
            break
        offset += limit
        time.sleep(0.3)  # Be nice to the server

    return results


def extract_persons(raw):
    """Extract relevant fields from person records."""
    persons = []
    for p in raw:
        persons.append({
            'id': p['id'],
            'name': p.get('name', ''),
            'first_name': p.get('first_name') or '',
            'gender': p.get('gender', ''),
            'start_date': p.get('start_date_written') or '',
            'end_date': p.get('end_date_written') or '',
            'alternative_label': p.get('alternative_label', []),
        })
    return persons


def extract_places(raw):
    """Extract relevant fields from place records."""
    places = []
    for p in raw:
        places.append({
            'id': p['id'],
            'label': p.get('label', ''),
            'type': p.get('type') or '',
            'lat': p.get('latitude'),
            'lng': p.get('longitude'),
            'start_date': p.get('start_date_written') or '',
            'end_date': p.get('end_date_written') or '',
            'alternative_label': p.get('alternative_label', []),
        })
    return places


def extract_institutions(raw):
    """Extract relevant fields from institution records."""
    institutions = []
    for inst in raw:
        institutions.append({
            'id': inst['id'],
            'name': inst.get('name', ''),
            'type': inst.get('type') or '',
            'start_date': inst.get('start_date_written') or '',
            'end_date': inst.get('end_date_written') or '',
            'alternative_label': inst.get('alternative_label', []),
        })
    return institutions


def extract_functions(raw):
    """Extract relevant fields from function records."""
    functions = []
    for f in raw:
        functions.append({
            'id': f['id'],
            'name': f.get('name', ''),
            'start_date': f.get('start_date_written') or '',
            'end_date': f.get('end_date_written') or '',
            'alternative_label': f.get('alternative_label', []),
        })
    return functions


def extract_relation_type(url):
    """Extract relation type from the relation URL.

    e.g. '.../apis_ontology.nimmtteilan/1/?format=json' -> 'nimmtteilan'
    """
    # URL looks like: .../apis_ontology.{type}/{id}/...
    import re
    m = re.search(r'apis_ontology\.(\w+)/\d+/', url)
    if m:
        return m.group(1)
    return 'unknown'


def extract_id_from_url(url):
    """Extract entity ID from API URL.

    e.g. '.../apis_ontology.person/18/?format=json' -> 18
    """
    import re
    m = re.search(r'/(\d+)/\?', url)
    if m:
        return int(m.group(1))
    return None


def extract_relations(raw):
    """Extract relevant fields from relation records."""
    relations = []
    for r in raw:
        rel_type = extract_relation_type(r.get('url', ''))
        subj = r.get('subj', {})
        obj = r.get('obj', {})
        relations.append({
            'relation_type': rel_type,
            'subj_id': extract_id_from_url(subj.get('url', '')),
            'subj_type': subj.get('content_type_name', ''),
            'subj_label': subj.get('label', ''),
            'obj_id': extract_id_from_url(obj.get('url', '')),
            'obj_type': obj.get('content_type_name', ''),
            'obj_label': obj.get('label', ''),
        })
    return relations


def save_json(data, filename):
    """Save data as JSON."""
    path = f'{OUT_DIR}/{filename}'
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    size_kb = len(json.dumps(data, ensure_ascii=False)) / 1024
    print(f'  Saved {path} ({len(data)} items, {size_kb:.0f} KB)')


def main():
    print('=== SiCProD Data Fetch ===\n')

    # Fetch all entities
    print('1. Persons...')
    raw_persons = fetch_paginated('apis_ontology.person')
    persons = extract_persons(raw_persons)
    save_json(persons, 'persons.json')

    print('\n2. Places...')
    raw_places = fetch_paginated('apis_ontology.place')
    places = extract_places(raw_places)
    save_json(places, 'places.json')

    print('\n3. Institutions...')
    raw_institutions = fetch_paginated('apis_ontology.institution')
    institutions = extract_institutions(raw_institutions)
    save_json(institutions, 'institutions.json')

    print('\n4. Functions...')
    raw_functions = fetch_paginated('apis_ontology.function')
    functions = extract_functions(raw_functions)
    save_json(functions, 'functions.json')

    print('\n5. Relations (this takes a while — 42.893 entries)...')
    raw_relations = fetch_paginated('relations.relation')
    relations = extract_relations(raw_relations)
    save_json(relations, 'relations.json')

    # Summary
    print(f'\n=== Done ===')
    print(f'  Persons:      {len(persons):>6}')
    print(f'  Places:       {len(places):>6}')
    print(f'  Institutions: {len(institutions):>6}')
    print(f'  Functions:    {len(functions):>6}')
    print(f'  Relations:    {len(relations):>6}')

    # Collect distinct relation types
    rel_types = {}
    for r in relations:
        rt = r['relation_type']
        rel_types[rt] = rel_types.get(rt, 0) + 1
    print(f'\n  Distinct relation types: {len(rel_types)}')
    for rt, count in sorted(rel_types.items(), key=lambda x: -x[1])[:20]:
        print(f'    {rt:<30} {count:>6}')


if __name__ == '__main__':
    main()
