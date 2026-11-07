"""
Smart Campus - Conflict Detection & Data Quality Audit Engine
Audits the normalized timetable entries for overlapping sessions, missing rooms, and shared resource occupancy.
"""

import json
from collections import defaultdict

def time_to_mins(t_str):
    parts = t_str.split(':')
    return int(parts[0]) * 60 + int(parts[1])

def audit_dataset():
    with open("data/normalized_timetable_entries.json", "r", encoding="utf-8") as f:
        entries = json.load(f)

    with open("data/resource_master.json", "r", encoding="utf-8") as f:
        resources = {r["id"]: r for r in json.load(f)}

    conflicts = []
    missing_rooms = []
    shared_resource_alerts = []

    # Group entries by day and resource
    room_day_schedule = defaultdict(lambda: defaultdict(list))
    # Group entries by day and section
    section_day_schedule = defaultdict(lambda: defaultdict(list))

    for entry in entries:
        day = entry["day_of_week"]
        sec_id = entry["section_id"]
        res_id = entry["resource_id"]
        t_start = time_to_mins(entry["start_time"])
        t_end = time_to_mins(entry["end_time"])

        # Check missing room
        if not res_id:
            missing_rooms.append({
                "entry_id": entry["id"],
                "section": entry["section_name"],
                "day": entry["day_name"],
                "time": f"{entry['start_time']}-{entry['end_time']}",
                "subject": entry["raw_subject"],
                "message": "Session has no physical room assigned (e.g. self-learning, counseling, or library)"
            })
        else:
            room_day_schedule[res_id][day].append((t_start, t_end, entry))

        section_day_schedule[sec_id][day].append((t_start, t_end, entry))

    # Check for Room Overlaps: A_start < B_end and A_end > B_start
    for res_id, day_data in room_day_schedule.items():
        res_obj = resources.get(res_id, {})
        res_code = res_obj.get("code", res_id)
        is_shared = res_obj.get("is_shared", False)

        for day, slot_list in day_data.items():
            n = len(slot_list)
            for i in range(n):
                for j in range(i + 1, n):
                    s1, e1, ent1 = slot_list[i]
                    s2, e2, ent2 = slot_list[j]
                    if s1 < e2 and e1 > s2:
                        conflicts.append({
                            "type": "ROOM_OVERLAP",
                            "severity": "CRITICAL",
                            "resource": res_code,
                            "day": ent1["day_name"],
                            "time_a": f"{ent1['start_time']}-{ent1['end_time']}",
                            "section_a": ent1["section_name"],
                            "subject_a": ent1["raw_subject"],
                            "time_b": f"{ent2['start_time']}-{ent2['end_time']}",
                            "section_b": ent2["section_name"],
                            "subject_b": ent2["raw_subject"],
                            "message": f"Room {res_code} double-booked between {ent1['section_name']} and {ent2['section_name']}"
                        })

    # Check for Section Overlaps: A single section scheduled in two places simultaneously
    for sec_id, day_data in section_day_schedule.items():
        for day, slot_list in day_data.items():
            n = len(slot_list)
            for i in range(n):
                for j in range(i + 1, n):
                    s1, e1, ent1 = slot_list[i]
                    s2, e2, ent2 = slot_list[j]
                    if s1 < e2 and e1 > s2:
                        conflicts.append({
                            "type": "SECTION_OVERLAP",
                            "severity": "CRITICAL",
                            "section": ent1["section_name"],
                            "day": ent1["day_name"],
                            "time_a": f"{ent1['start_time']}-{ent1['end_time']}",
                            "subject_a": ent1["raw_subject"],
                            "time_b": f"{ent2['start_time']}-{ent2['end_time']}",
                            "subject_b": ent2["raw_subject"],
                            "message": f"Section {ent1['section_name']} has overlapping scheduled subjects"
                        })

    # Summary report
    audit_report = {
        "total_entries_scanned": len(entries),
        "total_conflicts": len(conflicts),
        "total_missing_rooms": len(missing_rooms),
        "conflicts": conflicts,
        "missing_rooms_sample": missing_rooms[:15]
    }

    with open("data/conflict_audit_report.json", "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2)

    print("=== TIMETABLE CONFLICT & DATA QUALITY REPORT ===")
    print(f"Total Entries Scanned: {len(entries)}")
    print(f"Critical Conflicts Detected: {len(conflicts)}")
    print(f"Missing Room Warnings: {len(missing_rooms)}")
    if conflicts:
        print("Sample Conflicts:")
        for c in conflicts[:5]:
            print(f"- [{c['type']}] {c['message']} ({c['day']} {c['time_a']})")

if __name__ == "__main__":
    audit_dataset()
