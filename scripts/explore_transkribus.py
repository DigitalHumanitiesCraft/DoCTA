"""Explore Transkribus Collection 2197991 — list all documents and categorize them."""
import urllib.request
import urllib.parse
import json
import sys
import io
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Auth — set TRANSKRIBUS_USER and TRANSKRIBUS_PASS as environment variables
TOKEN_URL = 'https://account.readcoop.eu/auth/realms/readcoop/protocol/openid-connect/token'
API_BASE = 'https://transkribus.eu/TrpServer/rest'
COLLECTION_ID = '2197991'

def get_token():
    params = {
        'grant_type': 'password',
        'client_id': 'transkribus-api-client',
        'username': os.environ['TRANSKRIBUS_USER'],
        'password': os.environ['TRANSKRIBUS_PASS']
    }
    data = urllib.parse.urlencode(params).encode('utf-8')
    req = urllib.request.Request(TOKEN_URL, data=data, method='POST')
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))['access_token']

def api_get(token, path):
    url = f'{API_BASE}{path}'
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Accept', 'application/json')
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def main():
    token = get_token()
    print('Auth OK\n')

    docs = api_get(token, f'/collections/{COLLECTION_ID}/list')

    # Categorize
    inventare = []
    raitbuecher = []
    kopialbuecher = []
    andere = []

    castle_names = [
        'thaur', 'fragenstein', 'sigmunds', 'hasegg', 'tratzberg', 'runkelstein',
        'kronburg', 'heinfels', 'greifenstein', 'naudersberg', 'wiesberg',
        'lamprechtsburg', 'sigmundskron', 'turm_mals', 'lichtenberg', 'pergine',
        'telvana', 'ehrenberg', 'schlossberg', 'hoertenberg', 'hört',
        'finsterm', 'schön'
    ]

    for doc in docs:
        title = doc.get('title', '?')
        doc_id = doc.get('docId', '?')
        nr_pages = doc.get('nrOfPages', '?')
        entry = {'id': doc_id, 'title': title, 'pages': nr_pages}

        tl = title.lower()
        if 'raitbuch' in tl:
            raitbuecher.append(entry)
        elif 'kopialbuch' in tl or 'koialbuch' in tl:
            kopialbuecher.append(entry)
        elif 'inventar' in tl or any(name in tl for name in castle_names):
            inventare.append(entry)
        else:
            andere.append(entry)

    total_pages = sum(d.get('nrOfPages', 0) for d in docs)

    print(f'=== Collection {COLLECTION_ID}: {len(docs)} Dokumente, {total_pages} Seiten gesamt ===\n')

    print(f'--- Burgeninventare ({len(inventare)}) ---')
    for e in sorted(inventare, key=lambda x: x['title']):
        print(f"  {e['id']:>8} | {e['pages']:>4}p | {e['title']}")

    print(f"\n--- Raitbücher ({len(raitbuecher)}) ---")
    for e in sorted(raitbuecher, key=lambda x: x['title']):
        print(f"  {e['id']:>8} | {e['pages']:>4}p | {e['title']}")

    print(f"\n--- Kopialbücher ({len(kopialbuecher)}) ---")
    for e in sorted(kopialbuecher, key=lambda x: x['title']):
        print(f"  {e['id']:>8} | {e['pages']:>4}p | {e['title']}")

    print(f"\n--- Andere ({len(andere)}) ---")
    for e in sorted(andere, key=lambda x: x['title']):
        print(f"  {e['id']:>8} | {e['pages']:>4}p | {e['title']}")

    # Summary
    rb_pages = sum(e['pages'] for e in raitbuecher)
    inv_pages = sum(e['pages'] for e in inventare)
    kb_pages = sum(e['pages'] for e in kopialbuecher)
    other_pages = sum(e['pages'] for e in andere)
    print(f'\n=== Zusammenfassung ===')
    print(f'Inventare:    {len(inventare):>3} Dok, {inv_pages:>5} Seiten')
    print(f'Raitbücher:   {len(raitbuecher):>3} Dok, {rb_pages:>5} Seiten')
    print(f'Kopialbücher: {len(kopialbuecher):>3} Dok, {kb_pages:>5} Seiten')
    print(f'Andere:       {len(andere):>3} Dok, {other_pages:>5} Seiten')
    print(f'GESAMT:       {len(docs):>3} Dok, {total_pages:>5} Seiten')

    # Save full JSON for later
    with open('data/transkribus_collection.json', 'w', encoding='utf-8') as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)
    print('\nFull JSON saved to data/transkribus_collection.json')

    # Now get Raitbuch 2 details (fulldoc metadata)
    rb2_id = None
    for e in raitbuecher:
        if e['title'] == 'Raitbuch 2':
            rb2_id = e['id']
            break

    if rb2_id:
        print(f'\n=== Raitbuch 2 (ID {rb2_id}) — Fulldoc Metadata ===')
        fulldoc = api_get(token, f'/collections/{COLLECTION_ID}/{rb2_id}/fulldoc')
        md = fulldoc.get('md', {})
        print(f"Title: {md.get('title')}")
        print(f"Pages: {md.get('nrOfPages')}")
        print(f"Created: {md.get('createdFromTimestamp')}")
        print(f"Uploaded: {md.get('uploadTimestamp')}")

        pages = fulldoc.get('pageList', {}).get('pages', [])
        print(f"\nFirst 5 pages:")
        for p in pages[:5]:
            ts_status = p.get('tsList', {}).get('transcripts', [{}])[0].get('status', '?') if p.get('tsList', {}).get('transcripts') else '?'
            img_url = p.get('url', '?')
            key = p.get('key', '?')
            page_nr = p.get('pageNr', '?')
            print(f"  Page {page_nr}: status={ts_status}, key={key}")
            print(f"    Image: {img_url[:100]}...")

if __name__ == '__main__':
    main()
