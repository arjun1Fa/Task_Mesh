import requests
import json
import time

# 1. Login to Orchestrator
auth_res = requests.post('http://127.0.0.1:8000/v1/auth/login', json={'username': 'admin', 'password': 'admin123'})
token = auth_res.json()['token']
headers = {'Authorization': f'Bearer {token}'}

# 2. Drain Worker Alpha to ensure Worker Beta receives the workload
print("Draining worker-alpha:", requests.post('http://127.0.0.1:8000/v1/nodes/worker-alpha/drain', headers=headers).json())
print("Resuming worker-beta:", requests.post('http://127.0.0.1:8000/v1/nodes/worker-beta/resume', headers=headers).json())

# 3. Submit real binary task via /v1/tasks/binary
with open('input_image.jpg', 'rb') as f:
    files = {'file': ('bus.jpg', f, 'image/jpeg')}
    data = {
        'model': 'yolov8n',
        'confidence_threshold': 0.25,
        'palette_size': 8,
        'priority': 10,
        'offload_policy': 'wireless_allowed',
        'requires_gpu': 'false'
    }
    submit_res = requests.post('http://127.0.0.1:8000/v1/tasks/binary', headers=headers, data=data, files=files)
    print("Submit response status:", submit_res.status_code)
    task = submit_res.json()
    task_id = task['id']
    print(f"Submitted binary task {task_id}")

# 4. Poll until completed
final_task = None
for i in range(30):
    time.sleep(2)
    poll_res = requests.get(f'http://127.0.0.1:8000/v1/tasks/{task_id}', headers=headers).json()
    st = poll_res.get('status')
    node = poll_res.get('assigned_node_id')
    print(f"[{i*2}s] Status: {st}, Assigned: {node}")
    if st in ('completed', 'failed'):
        final_task = poll_res
        break

# 5. Restore Worker Alpha
print("Restoring worker-alpha:", requests.post('http://127.0.0.1:8000/v1/nodes/worker-alpha/resume', headers=headers).json())

with open('beta_real_task_result.json', 'w') as out:
    json.dump(final_task, out, indent=2)

print("Saved result to beta_real_task_result.json")

