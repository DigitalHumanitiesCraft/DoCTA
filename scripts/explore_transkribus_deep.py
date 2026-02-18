"""Deep exploration of Transkribus Collection 2197991.
Gets page-level details and transcription status for all documents."""
import urllib.request
import urllib.parse
import json
import sys
import io
import os
import time

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

    # 1. Get Raitbuch 2 fulldoc — all pages with keys and transcription status
    RB2_ID = 12514730
    print(f'=== Raitbuch 2 (ID {RB2_ID}) — All 123 pages ===\n')
    fulldoc = api_get(token, f'/collections/{COLLECTION_ID}/{RB2_ID}/fulldoc')
    pages = fulldoc.get('pageList', {}).get('pages', [])

    status_counts = {}
    rb2_pages = []
    for p in pages:
        transcripts = p.get('tsList', {}).get('transcripts', [])
        status = transcripts[0].get('status', '?') if transcripts else 'NONE'
        key = p.get('key', '?')
        page_nr = p.get('pageNr', '?')
        img_name = p.get('imgFileName', '?')

        status_counts[status] = status_counts.get(status, 0) + 1
        rb2_pages.append({
            'pageNr': page_nr,
            'key': key,
            'status': status,
            'imgFileName': img_name,
            'iiif_url': f'https://files.transkribus.eu/iiif/2/{key}/full/max/0/default.jpg',
            'iiif_thumb': f'https://files.transkribus.eu/iiif/2/{key}/full/200,/0/default.jpg'
        })

    print('Transcription status distribution:')
    for s, c in sorted(status_counts.items()):
        print(f'  {s}: {c}')

    print(f'\nFirst 10 pages:')
    for p in rb2_pages[:10]:
        print(f"  p{p['pageNr']:>3}: {p['status']:<15} {p['imgFileName']}")

    # Save Raitbuch 2 page data
    with open('data/raitbuch2_pages.json', 'w', encoding='utf-8') as f:
        json.dump(rb2_pages, f, ensure_ascii=False, indent=2)
    print(f'\nSaved {len(rb2_pages)} pages to data/raitbuch2_pages.json')

    # 2. Check transcription status across a sample of documents
    print('\n\n=== Transcription status across collection (sampling) ===\n')

    docs = api_get(token, f'/collections/{COLLECTION_ID}/list')

    # Sample: all inventare (first 10), first 3 raitbücher, first 3 other
    sample_ids = []
    inv_count = 0
    rb_count = 0
    other_count = 0

    for doc in docs:
        title = doc.get('title', '').lower()
        doc_id = doc.get('docId')
        if 'inventar' in title or 'thaur' in title or 'fragenstein' in title:
            if inv_count < 10:
                sample_ids.append((doc_id, doc.get('title')))
                inv_count += 1
        elif 'raitbuch' in title:
            if rb_count < 3:
                sample_ids.append((doc_id, doc.get('title')))
                rb_count += 1
        else:
            if other_count < 3:
                sample_ids.append((doc_id, doc.get('title')))
                other_count += 1

    for doc_id, title in sample_ids:
        try:
            fd = api_get(token, f'/collections/{COLLECTION_ID}/{doc_id}/fulldoc')
            pages = fd.get('pageList', {}).get('pages', [])
            statuses = {}
            for p in pages:
                ts = p.get('tsList', {}).get('transcripts', [])
                st = ts[0].get('status', '?') if ts else 'NONE'
                statuses[st] = statuses.get(st, 0) + 1
            status_str = ', '.join(f'{s}:{c}' for s, c in sorted(statuses.items()))
            print(f'  {doc_id:>8} | {title:<50} | {status_str}')
            time.sleep(0.3)  # Rate limit
        except Exception as e:
            print(f'  {doc_id:>8} | {title:<50} | ERROR: {e}')

    # 3. Get one inventar fulldoc to check if there's actual transcription text
    print('\n\n=== Sample transcription check: Thaur A 49.1 ===\n')
    THAUR_ID = 11328300  # Thaur_TLA Inventare A 49.1_1471, 4 pages
    fd = api_get(token, f'/collections/{COLLECTION_ID}/{THAUR_ID}/fulldoc')
    pages = fd.get('pageList', {}).get('pages', [])
    for p in pages[:2]:
        ts = p.get('tsList', {}).get('transcripts', [])
        if ts:
            t = ts[0]
            print(f"  Page {p['pageNr']}:")
            print(f"    Status: {t.get('status')}")
            print(f"    Tool: {t.get('toolName', '?')}")
            # Check if there's a PAGE XML URL
            page_xml_url = t.get('url', t.get('pageXmlUrl', ''))
            if page_xml_url:
                print(f"    PAGE XML URL: {page_xml_url[:80]}...")
            nr_of_regions = t.get('nrOfRegions', '?')
            nr_of_lines = t.get('nrOfTranscribedLines', '?')
            nr_of_words = t.get('nrOfWordsInLines', '?')
            print(f"    Regions: {nr_of_regions}, Lines: {nr_of_lines}, Words: {nr_of_words}")

if __name__ == '__main__':
    main()
