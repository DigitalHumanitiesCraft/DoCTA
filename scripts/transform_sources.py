"""Transform the CSV source catalog into clean JSON for the prototype.

Input: sources/quellen-katalog.csv (316 entries with ghost columns, inconsistent dates)
Output: data/sources.json (clean, with Transkribus links and availability tiers)
"""
import csv
import json
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = 'c:/Users/chstn/Desktop/data/DHCraft/Projekte/Git/DoCTA'


def normalize_date(raw):
    """Normalize date strings to consistent format.

    Handles: '1487-1594', '1495 (ca.)', '15. Jh.', '-1564', '1479',
             '1470-1479', '1490 (ca.)', etc.
    Returns: {'raw': original, 'start': int|None, 'end': int|None, 'circa': bool}
    """
    if not raw or not raw.strip():
        return {'raw': '', 'start': None, 'end': None, 'circa': False}

    raw = raw.strip()
    # Normalize dashes (en-dash → hyphen)
    raw_norm = raw.replace('\u2013', '-').replace('\u2014', '-')
    circa = 'ca.' in raw_norm or 'ca' in raw_norm

    # Try range: 1487-1594
    m = re.match(r'(-?\d{4})\s*-\s*(\d{4})', raw_norm)
    if m:
        return {'raw': raw, 'start': int(m.group(1)), 'end': int(m.group(2)), 'circa': circa}

    # Try single year with optional prefix/suffix: 1479, -1564, 1495 (ca.)
    m = re.search(r'(-?\d{4})', raw_norm)
    if m:
        year = int(m.group(1))
        return {'raw': raw, 'start': year, 'end': year, 'circa': circa}

    # Century: "15. Jh."
    m = re.search(r'(\d+)\.\s*Jh', raw_norm)
    if m:
        century = int(m.group(1))
        return {'raw': raw, 'start': (century - 1) * 100 + 1, 'end': century * 100, 'circa': True}

    return {'raw': raw, 'start': None, 'end': None, 'circa': False}


def parse_pages(digitalisiert):
    """Extract page count from Digitalisiert column.

    The column contains page counts (not boolean), e.g. '123', '45 S.', etc.
    """
    if not digitalisiert or not digitalisiert.strip():
        return None
    m = re.search(r'(\d+)', digitalisiert.strip())
    if m:
        return int(m.group(1))
    return None


def compute_availability_tier(row, tb_mapping):
    """Compute data availability tier 1-4.

    Tier 1: Transkription vorhanden (in Transkribus mit Text)
    Tier 2: Digitalisiert (in Transkribus, aber kein Text)
    Tier 3: Im Archiv bekannt, nicht digitalisiert
    Tier 4: Unsicher/fraglich
    """
    signatur = row.get('Signatur', '').strip()

    # Check if in Transkribus mapping (with text)
    for m in tb_mapping.get('matched', []):
        if m['csv_signatur'] == signatur:
            if m['has_text']:
                return 1
            else:
                return 2

    # Transkribiert column says "Inventaria"
    if row.get('Transkribiert', '').strip():
        return 1

    # Has page count in Digitalisiert column → likely digitized
    pages = parse_pages(row.get('Digitalisiert', ''))
    if pages and pages > 0:
        return 2

    return 3


def main():
    # Load CSV
    rows = []
    with open(f'{BASE}/sources/quellen-katalog.csv', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    print(f'Loaded {len(rows)} CSV rows')

    # Load Transkribus mapping
    with open(f'{BASE}/data/source_mapping.json', encoding='utf-8') as f:
        tb_mapping = json.load(f)

    # Build Transkribus lookup by CSV signatur
    tb_by_signatur = {}
    for m in tb_mapping.get('matched', []):
        tb_by_signatur[m['csv_signatur']] = m

    # Transform
    sources = []
    ghost_cols = [f'Spalte{i}' for i in range(3, 19)]  # Spalte3-Spalte18

    categories = {}
    for row in rows:
        signatur = row.get('Signatur', '').strip()
        kategorie = row.get('Kategorie', '').strip()
        titel = row.get('Titel', '').strip()
        datierung = row.get('Datierung', '').strip()
        art = row.get('Art', '').strip()
        projekt = row.get('Projekt', '').strip()
        digitalisiert = row.get('Digitalisiert', '').strip()
        transkribiert = row.get('Transkribiert', '').strip()

        # Skip rows with no signatur (empty rows)
        if not signatur:
            continue

        date = normalize_date(datierung)
        pages = parse_pages(digitalisiert)
        tier = compute_availability_tier(row, tb_mapping)

        # Transkribus info
        tb_info = tb_by_signatur.get(signatur)
        transkribus = None
        if tb_info:
            transkribus = {
                'doc_id': tb_info['transkribus_id'],
                'title': tb_info['transkribus_title'],
                'pages': tb_info['pages'],
                'lines': tb_info['lines'],
                'words': tb_info['words'],
                'has_text': tb_info['has_text'],
            }

        source = {
            'signatur': signatur,
            'kategorie': kategorie,
            'titel': titel,
            'datierung': date,
            'art': art,
            'projekt': projekt,
            'seiten': pages,
            'transkribiert': transkribiert,
            'tier': tier,
            'transkribus': transkribus,
        }
        sources.append(source)
        categories[kategorie] = categories.get(kategorie, 0) + 1

    # Save
    out_path = f'{BASE}/data/sources.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(sources, f, ensure_ascii=False, indent=1)

    print(f'\nSaved {len(sources)} sources to {out_path}')
    print(f'\nCategories:')
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f'  {cat:<30} {count:>4}')

    print(f'\nTiers:')
    tier_counts = {}
    for s in sources:
        tier_counts[s['tier']] = tier_counts.get(s['tier'], 0) + 1
    for tier in sorted(tier_counts):
        labels = {1: 'Transkription', 2: 'Digitalisiert', 3: 'Im Archiv', 4: 'Unsicher'}
        print(f'  Tier {tier} ({labels.get(tier, "?")}): {tier_counts[tier]}')

    print(f'\nWith Transkribus link: {sum(1 for s in sources if s["transkribus"])}')


if __name__ == '__main__':
    main()
