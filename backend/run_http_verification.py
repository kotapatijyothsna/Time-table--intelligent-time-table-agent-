import sys
import os
import time
import threading
import urllib.request
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.core.wsgi import get_wsgi_application
from wsgiref.simple_server import make_server

app = get_wsgi_application()
server = make_server('127.0.0.1', 8000, app)
t = threading.Thread(target=server.serve_forever, daemon=True)
t.start()
time.sleep(1)

print('Server started on 127.0.0.1:8000. Probing endpoints...')

# 1. Probe Departments
r1 = urllib.request.urlopen('http://127.0.0.1:8000/api/v1/academics/departments/')
print('[PASS] 1. Departments status:', r1.status, 'Total:', len(json.loads(r1.read().decode())))

# 2. Probe Exceptions list
r2 = urllib.request.urlopen('http://127.0.0.1:8000/api/v1/timetables/exceptions/')
print('[PASS] 2. Exceptions status:', r2.status, 'Total active:', len(json.loads(r2.read().decode())))

# 3. Probe Entries Search
r3 = urllib.request.urlopen('http://127.0.0.1:8000/api/v1/timetables/entries/search/?date=2026-11-09')
entries = json.loads(r3.read().decode())
print('[PASS] 3. Entries search status:', r3.status, 'Found:', len(entries))

# 4. Probe Create Exception (POST)
payload = {
    'timetable_entry_id': entries[0]['id'],
    'exception_date': '2026-11-09',
    'exception_type': 'CANCEL',
    'reason': 'Guest Lecture by IIT Madras Professor',
    'user_id': 'Head of Department'
}
req4 = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/timetables/exceptions/',
    data=json.dumps(payload).encode(),
    headers={'Content-Type': 'application/json'}
)
r4 = urllib.request.urlopen(req4)
ex_created = json.loads(r4.read().decode())
print('[PASS] 4. Create Exception status:', r4.status, 'Created ID:', ex_created['id'])

# 5. Probe Campus AI Assistant with Groq LLM
req5 = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/assistant/query/',
    data=json.dumps({'query': 'Are there any cancellations or substitutions on Monday?'}).encode(),
    headers={'Content-Type': 'application/json'}
)
r5 = urllib.request.urlopen(req5)
ai_data = json.loads(r5.read().decode())
print('[PASS] 5. Campus AI status:', r5.status)
print('         Active Model/Mode:', ai_data.get('rag_metadata', {}).get('rag_mode'))
print('         AI Response:')
for line in ai_data['reply'].split('\n'):
    print('           ', line)

# 6. Clean up created exception (DELETE)
ex_id = ex_created['id']
req6 = urllib.request.Request(f'http://127.0.0.1:8000/api/v1/timetables/exceptions/{ex_id}/', method='DELETE')
r6 = urllib.request.urlopen(req6)
print('[PASS] 6. Revoke Exception status:', r6.status, json.loads(r6.read().decode()))

server.shutdown()
print('ALL LIVE HTTP ENDPOINTS TESTED AND VERIFIED OVER TCP SOCKETS!')
