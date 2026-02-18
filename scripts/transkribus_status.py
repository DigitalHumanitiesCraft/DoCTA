"""Check transcription status for ALL documents in Collection 2197991."""
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

    docs = api_get(token, f'/collections/{COLLECTION_ID}/list')
    print(f'Checking {len(docs)} documents...\n')

    results = []
    for i, doc in enumerate(docs):
        doc_id = doc['docId']
        title = doc.get('title', '?')
        nr_pages = doc.get('nrOfPages', 0)

        try:
            fd = api_get(token, f'/collections/{COLLECTION_ID}/{doc_id}/fulldoc')
            pages = fd.get('pageList', {}).get('pages', [])

            total_lines = 0
            total_words = 0
            statuses = {}

            for p in pages:
                ts = p.get('tsList', {}).get('transcripts', [])
                if ts:
                    t = ts[0]
                    st = t.get('status', '?')
                    statuses[st] = statuses.get(st, 0) + 1
                    total_lines += t.get('nrOfTranscribedLines', 0) or 0
                    total_words += t.get('nrOfWordsInLines', 0) or 0

            has_text = total_lines > 0
            primary_status = max(statuses, key=statuses.get) if statuses else '?'
            done_pages = statuses.get('DONE', 0)

            results.append({
                'id': doc_id,
                'title': title,
                'pages': nr_pages,
                'status': primary_status,
                'done_pages': done_pages,
                'lines': total_lines,
                'words': total_words,
                'has_text': has_text,
                'statuses': statuses
            })

            marker = 'TEXT' if has_text else '----'
            print(f"  [{marker}] {doc_id:>8} | {nr_pages:>4}p | {total_lines:>5} lines | {total_words:>6} words | {primary_status:<12} | {title}")

        except Exception as e:
            print(f"  [ERR ] {doc_id:>8} | {title}: {e}")
            results.append({'id': doc_id, 'title': title, 'pages': nr_pages, 'error': str(e)})

        time.sleep(0.2)

        # Re-auth every 50 docs (token expires after 300s)
        if i > 0 and i % 50 == 0:
            token = get_token()
            print(f'  [Re-authenticated at doc {i}]')

    # Summary
    with_text = [r for r in results if r.get('has_text')]
    without_text = [r for r in results if not r.get('has_text') and 'error' not in r]

    print(f'\n=== SUMMARY ===')
    print(f'Total documents: {len(results)}')
    print(f'With transcription text: {len(with_text)}')
    print(f'Without text (images only): {len(without_text)}')
    print(f'Errors: {len([r for r in results if "error" in r])}')

    if with_text:
        total_text_pages = sum(r['pages'] for r in with_text)
        total_text_lines = sum(r['lines'] for r in with_text)
        total_text_words = sum(r['words'] for r in with_text)
        print(f'\nDocuments WITH text:')
        print(f'  Pages: {total_text_pages}')
        print(f'  Lines: {total_text_lines}')
        print(f'  Words: {total_text_words}')
        print(f'\n  Documents:')
        for r in sorted(with_text, key=lambda x: x['title']):
            print(f"    {r['id']:>8} | {r['pages']:>4}p | {r['lines']:>5}L | {r['words']:>6}W | {r['title']}")

    # Save results
    with open('data/transkribus_status.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print('\nSaved to data/transkribus_status.json')

if __name__ == '__main__':
    main()
