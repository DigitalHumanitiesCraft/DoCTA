"""Map Transkribus document titles to CSV signatures.

Transkribus: "Thaur_TLA Inventare A 49.1_1471" or "Thaur_tla_inventare_a_49_1"
CSV:         "AT-TLA/BBÄ MIB - Inventare A 049.1"

Key: extract the "A {number}" part and normalize it.
"""
import csv
import json
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = 'c:/Users/chstn/Desktop/data/DHCraft/Projekte/Git/DoCTA'

def extract_inv_number(text):
    """Extract normalized inventory number like '49.1', '125.3' from various formats."""
    text = text.replace('_', ' ').replace('  ', ' ')
    # Match patterns like "A 049.1", "A 125.3-4", "a 49 1", "A_6.1"
    m = re.search(r'[Aa]\s*(\d+)[.\s](\d+)', text)
    if m:
        main = str(int(m.group(1)))  # strip leading zeros
        sub = m.group(2)
        return f'{main}.{sub}'
    # Try just "A {number}" without sub
    m = re.search(r'[Aa]\s*(\d+)', text)
    if m:
        return str(int(m.group(1)))
    return None


def main():
    # Load Transkribus data
    with open(f'{BASE}/data/transkribus_status.json', encoding='utf-8') as f:
        tb_docs = json.load(f)

    # Load CSV
    csv_rows = []
    with open(f'{BASE}/sources/quellen-katalog.csv', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            csv_rows.append(row)

    # Build lookup: inv_number → CSV row(s)
    csv_by_number = {}
    for row in csv_rows:
        sig = row.get('Signatur', '').strip()
        if 'Inventare' not in sig:
            continue
        num = extract_inv_number(sig)
        if num:
            # Handle ranges like "125.3-4" → also register "125.4"
            m = re.search(r'(\d+)\.(\d+)-(\d+)', sig)
            if m:
                main = str(int(m.group(1)))
                for sub in range(int(m.group(2)), int(m.group(3)) + 1):
                    csv_by_number[f'{main}.{sub}'] = row
            # Handle "(und .X)" patterns
            m2 = re.search(r'und\s*\.?(\d+)', sig)
            if m2:
                main_m = re.search(r'[Aa]\s*(\d+)', sig)
                if main_m:
                    main = str(int(main_m.group(1)))
                    csv_by_number[f'{main}.{m2.group(1)}'] = row
            csv_by_number[num] = row

    # Build lookup: inv_number → Transkribus doc(s)
    tb_by_number = {}
    for doc in tb_docs:
        title = doc.get('title', '')
        if 'inventar' not in title.lower() and 'Inventare' not in title:
            # Try castle name matching for non-standard titles
            num = extract_inv_number(title)
            if num:
                tb_by_number.setdefault(num, []).append(doc)
            continue
        num = extract_inv_number(title)
        if num:
            tb_by_number.setdefault(num, []).append(doc)

    # Match
    matched = []
    unmatched_tb = []
    unmatched_csv = []

    for num, tb_list in sorted(tb_by_number.items(), key=lambda x: (int(x[0].split('.')[0]), int(x[0].split('.')[1]) if '.' in x[0] else 0)):
        csv_row = csv_by_number.get(num)
        for tb_doc in tb_list:
            if csv_row:
                matched.append({
                    'inv_number': num,
                    'transkribus_id': tb_doc['id'],
                    'transkribus_title': tb_doc['title'],
                    'csv_signatur': csv_row.get('Signatur', '').strip(),
                    'csv_titel': csv_row.get('Titel', '').strip()[:80],
                    'csv_kategorie': csv_row.get('Kategorie', '').strip(),
                    'csv_transkribiert': csv_row.get('Transkribiert', '').strip(),
                    'pages': tb_doc.get('pages', 0),
                    'lines': tb_doc.get('lines', 0),
                    'words': tb_doc.get('words', 0),
                    'has_text': tb_doc.get('has_text', False)
                })
            else:
                unmatched_tb.append(tb_doc)

    # Find CSV inventar entries without Transkribus match
    matched_nums = {m['inv_number'] for m in matched}
    for num, row in sorted(csv_by_number.items()):
        if num not in matched_nums and num not in tb_by_number:
            unmatched_csv.append({'inv_number': num, 'signatur': row.get('Signatur', '').strip(), 'transkribiert': row.get('Transkribiert', '').strip()})

    # Report
    print(f'=== MATCHED: {len(matched)} ===\n')
    for m in matched:
        text_marker = 'TEXT' if m['has_text'] else '----'
        print(f"  [{text_marker}] A {m['inv_number']:<8} | TB:{m['transkribus_id']:>8} ({m['pages']:>3}p, {m['lines']:>4}L) | CSV: {m['csv_signatur']}")

    if unmatched_tb:
        print(f'\n=== UNMATCHED Transkribus docs: {len(unmatched_tb)} ===\n')
        for d in unmatched_tb:
            print(f"  {d['id']:>8} | {d['title']}")

    if unmatched_csv:
        print(f'\n=== UNMATCHED CSV entries: {len(unmatched_csv)} ===\n')
        for c in unmatched_csv:
            transk = c['transkribiert']
            marker = ' [Inventaria]' if transk else ''
            print(f"  A {c['inv_number']:<8} | {c['signatur']}{marker}")

    # Also handle non-inventar documents (Raitbücher, Kopialbücher, etc.)
    print(f'\n=== Non-Inventar Transkribus docs ===\n')
    for doc in sorted(tb_docs, key=lambda x: x.get('title', '')):
        title = doc['title']
        if 'inventar' in title.lower() or 'Inventare' in title:
            continue
        # Try to find in CSV
        csv_match = None
        tl = title.lower()
        if 'raitbuch' in tl:
            # Extract number
            m = re.search(r'raitbuch\s*(\d+)', tl)
            if m:
                rb_num = m.group(1)
                for row in csv_rows:
                    if 'Raitbuch' in row.get('Titel', '') and f'Raitbuch {rb_num}' in row.get('Titel', ''):
                        csv_match = row.get('Signatur', '').strip()
                        break
        elif 'kopialbuch' in tl or 'koialbuch' in tl:
            pass  # Complex matching needed
        elif 'hs' in tl.replace('_', ' ').lower():
            # Try Hs number
            m = re.search(r'hs[_\s]*(\d+)', tl)
            if m:
                hs_num = m.group(1)
                for row in csv_rows:
                    sig = row.get('Signatur', '')
                    if f'Hs. {hs_num}' in sig or f'Hs {hs_num}' in sig:
                        csv_match = sig.strip()
                        break

        match_str = f' → CSV: {csv_match}' if csv_match else ''
        print(f"  {doc['id']:>8} | {doc.get('pages',0):>4}p | {title}{match_str}")

    # Save mapping
    with open(f'{BASE}/data/source_mapping.json', 'w', encoding='utf-8') as f:
        json.dump({
            'matched': matched,
            'unmatched_transkribus': [{'id': d['id'], 'title': d['title']} for d in unmatched_tb],
            'unmatched_csv': unmatched_csv
        }, f, ensure_ascii=False, indent=2)
    print(f'\nSaved mapping to data/source_mapping.json')

if __name__ == '__main__':
    main()
