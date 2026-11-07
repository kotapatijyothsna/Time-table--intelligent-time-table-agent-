import urllib.request, json

req = urllib.request.urlopen("http://127.0.0.1:8000/api/v1/timetables/sections/")
sections = json.loads(req.read().decode("utf-8"))
print(f"Total sections available: {len(sections)}")

# Test a few different sections (e.g., II AIML-A, III AIML-A, CS, BS(DS))
sample_indices = [0, 12, 24, 35]
for idx in sample_indices:
    if idx < len(sections):
        s = sections[idx]
        req2 = urllib.request.urlopen(f"http://127.0.0.1:8000/api/v1/timetables/sections/{s['id']}/")
        data = json.loads(req2.read().decode("utf-8"))
        print(f"\n================ Section: {data['section']} (Version: {data['version']}) ================")
        print(f"Total entries: {len(data['entries'])}")
        for e in data['entries'][:6]:
            print(f"  Day {e['day_of_week']} | {e['start_time'][:5]}-{e['end_time'][:5]} | {e['subject'][:30]:30} | Fac: {e['faculty'][:25]:25} | Room: {e['room']}")
