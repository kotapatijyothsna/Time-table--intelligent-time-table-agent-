import urllib.request
import json

def test_url(url, label):
    req = urllib.request.urlopen(url)
    data = json.loads(req.read().decode('utf-8'))
    print(f"\n=== {label} ===")
    if isinstance(data, list):
        print(f"Total Count: {len(data)}")
        if data:
            print(f"Sample: {data[0]}")
    elif isinstance(data, dict):
        for k in ['day', 'period', 'slot', 'resource_type', 'total_resources', 'total_faculty']:
            if k in data:
                print(f"  {k}: {data[k]}")
        if 'resources' in data:
            occ = sum(1 for r in data['resources'] if r['status'] == 'Occupied')
            unocc = sum(1 for r in data['resources'] if r['status'] == 'Unoccupied')
            other = len(data['resources']) - occ - unocc
            print(f"  Resource Statuses -> Occupied: {occ}, Unoccupied: {unocc}, Other: {other}")
            occupied_items = [r for r in data['resources'] if r['status'] == 'Occupied']
            if occupied_items:
                print(f"  Sample Occupied: {occupied_items[0]['code']} - {occupied_items[0]['reason']} ({occupied_items[0]['details']['section'] if occupied_items[0]['details'] else ''})")
            unocc_items = [r for r in data['resources'] if r['status'] == 'Unoccupied']
            if unocc_items:
                print(f"  Sample Unoccupied: {unocc_items[0]['code']} - {unocc_items[0]['reason']}")
        if 'faculty' in data:
            occ = sum(1 for f in data['faculty'] if f['status'] == 'Occupied')
            avail = sum(1 for f in data['faculty'] if f['status'] == 'Available')
            other = len(data['faculty']) - occ - avail
            print(f"  Faculty Statuses -> Occupied: {occ}, Available: {avail}, Other: {other}")
            occupied_items = [f for f in data['faculty'] if f['status'] == 'Occupied']
            if occupied_items:
                print(f"  Sample Occupied: {occupied_items[0]['name']} - {occupied_items[0]['reason']}")
            avail_items = [f for f in data['faculty'] if f['status'] == 'Available']
            if avail_items:
                print(f"  Sample Available: {avail_items[0]['name']} - {avail_items[0]['reason']}")

test_url('http://127.0.0.1:8000/api/v1/academics/departments/', 'Departments')
test_url('http://127.0.0.1:8000/api/v1/timetables/periods/', 'Periods')
test_url('http://127.0.0.1:8000/api/v1/availability/resources/?day=Monday&period=1&type=CLASSROOM', 'Classrooms Monday Period 1')
test_url('http://127.0.0.1:8000/api/v1/availability/resources/?day=Monday&period=2&type=LABORATORY', 'Labs Monday Period 2')
test_url('http://127.0.0.1:8000/api/v1/availability/faculty/?day=Monday&period=1', 'Faculty Monday Period 1')
