import io
import time
import requests

base = 'http://localhost:3000'

print('--- Starting End-to-End Live Verification ---')

# 1. Health check via frontend rewrite
r = requests.get(f'{base}/api/health')
print('1. Health check:', r.status_code, r.json())
assert r.status_code == 200

# 2. Sample CSV download
r = requests.get(f'{base}/api/sample.csv')
print('2. Sample CSV:', r.status_code, f'{len(r.content)} bytes')
assert r.status_code == 200
csv_content = r.content

# 3. Dry-run validate
files = {'file': ('sample.csv', io.BytesIO(csv_content), 'text/csv')}
r = requests.post(f'{base}/api/validate', files=files)
print('3. Validate dry-run:', r.status_code, f"{r.json()['row_count']} rows, roles: {list(r.json()['detected_roles'].keys())}")
assert r.status_code == 200

# 4. Create Run
files = {'file': ('sample.csv', io.BytesIO(csv_content), 'text/csv')}
r = requests.post(f'{base}/api/runs', files=files)
print('4. Create run:', r.status_code, r.json()['run_id'])
assert r.status_code in (200, 201)
run_id = r.json()['run_id']

# 5. Fetch review envelope
r = requests.get(f'{base}/api/runs/{run_id}')
review_data = r.json()
print('5. Review envelope status:', review_data['status'], 'candidates:', review_data['review']['detected_protected_candidates'])
assert review_data['status'] == 'awaiting_approval'

# 6. Approve run
approval_payload = {
    'protected_attributes': review_data['review']['detected_protected_candidates'],
    'significance_level': 0.05,
    'min_group_size': 30,
    'permutations': 500
}
r = requests.post(
    f'{base}/api/runs/{run_id}/approve',
    json=approval_payload,
    headers={'X-User-Name': 'Om Lead Auditor', 'X-User-Email': 'om@audit.internal'}
)
print('6. Approve response:', r.status_code, r.json())
assert r.status_code == 202

# 7. Poll until completed
status = 'running'
for i in range(30):
    time.sleep(1)
    r = requests.get(f'{base}/api/runs/{run_id}')
    status = r.json()['status']
    stage = r.json().get('stage', 'unknown')
    print(f'   Poll {i+1}: stage={stage}, status={status}')
    if status == 'completed':
        break
assert status == 'completed'
summary = r.json()['summary']
print('7. Completed successfully! Summary:', summary)

# 8. Test Ask VERITAS Q&A
qa_payload = {'question': 'Which NIST controls have findings in this run?'}
r = requests.post(f'{base}/api/runs/{run_id}/ask', json=qa_payload)
qa_res = r.json()
print('8. Q&A Ask response:', r.status_code, f"Answer: {qa_res['answer'][:100]}... Citations: {qa_res['citations']}")
assert r.status_code == 200

# 9. Test Report HTML and PDF endpoints
r_html = requests.get(f'{base}/api/runs/{run_id}/report.html')
r_pdf = requests.get(f'{base}/api/runs/{run_id}/report.pdf')
print('9. Report HTML:', r_html.status_code, f'{len(r_html.content)} bytes | Report PDF:', r_pdf.status_code, f'{len(r_pdf.content)} bytes')
assert r_html.status_code == 200
assert r_pdf.status_code == 200

# 10. Test Frontend SSR pages
for path in ['/', '/runs', f'/runs/{run_id}/summary', f'/runs/{run_id}/fairness', f'/method']:
    r_page = requests.get(f'{base}{path}')
    print(f'10. Frontend page {path}:', r_page.status_code)
    assert r_page.status_code == 200

print('\n>>> ALL 10 END-TO-END CHECKS PASSED OPERATIONAL VERIFICATION! <<<')
