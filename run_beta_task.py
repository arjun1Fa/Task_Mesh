import urllib.request
import json
import base64
import time

def api_call(url, data=None, token=None, method=None):
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    if data is not None:
        headers['Content-Type'] = 'application/json'
        body = json.dumps(data).encode('utf-8')
    else:
        body = None
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request) as resp:
        return json.loads(resp.read().decode('utf-8'))

# Login
auth = api_call('http://127.0.0.1:8000/v1/auth/login', {'username': 'admin', 'password': 'admin123'})
token = auth['token']
print("Authenticated successfully.")

# Drain worker-alpha so beta is targeted
print("Draining worker-alpha:", api_call('http://127.0.0.1:8000/v1/nodes/worker-alpha/drain', {}, token, 'POST'))
print("Resuming worker-beta:", api_call('http://127.0.0.1:8000/v1/nodes/worker-beta/resume', {}, token, 'POST'))

# Read image
with open('input_image.jpg', 'rb') as f:
    img_b64 = base64.b64encode(f.read()).decode('ascii')

task_payload = {
    'task_type': 'image_inference',
    'priority': 10,
    'timeout_seconds': 120,
    'payload': {
        'model': 'yolov8n',
        'confidence_threshold': 0.25,
        'extract_colors': True,
        'palette_size': 8,
        'annotate_image': True,
        'image_data': img_b64
    }
}

task_resp = api_call('http://127.0.0.1:8000/v1/tasks', task_payload, token, 'POST')
task_id = task_resp['id']
print(f"Task submitted: {task_id}")

final_task = None
for i in range(25):
    time.sleep(2)
    t = api_call(f'http://127.0.0.1:8000/v1/tasks/{task_id}', token=token)
    status = t.get('status')
    node = t.get('assigned_node')
    print(f"[{i*2}s] Status: {status}, Node: {node}")
    if status in ('completed', 'failed'):
        final_task = t
        break

# Restore worker-alpha
print("Restoring worker-alpha:", api_call('http://127.0.0.1:8000/v1/nodes/worker-alpha/resume', {}, token, 'POST'))

with open('beta_task_result.json', 'w') as out:
    json.dump(final_task, out, indent=2)

print("Saved final task result to beta_task_result.json")
