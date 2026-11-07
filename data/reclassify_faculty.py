"""
Reclassify remaining 'Assistant Professor' entries into Faculty / Teaching Assistant / Outsourcing Staff.
Also remove any junk/non-name entries (time strings, numbers, etc.)
"""

import json
import re

# Names that should be Faculty (from segregation list or Dr. prefix)
FACULTY_EXTRA = {
    "Dr Ramesh Kumar Mojjada",   # Dr. prefix → Faculty
    "Dr Gurusamy Murugesan",
    "Dr SK Satpathy",
    "Dr. Amar Jukuntla",
    "Dr. D. Venkatesulu",
    "Dr. M.Nirupama Bhat",
    "Dr. P.M. Benson Mansingh",
    "Dr. S. Hanumantha Rao",
    "Dr. Sreenivas Peta",
    "Dr. Vinod Kumar",
    "Dr.Aswini",
    "Dr.M.Krishna Chennakesava Rao",
    "Prof P L N Varma",
    "Sk Chand Basha",
}

# Names that are Teaching Assistants (plain/non-Dr names from TA list in segration)
TA_NAMES = {
    "M.DEV SAMPATH KUMAR",
    "Sk. Salwar",
    "Sk.Salwar",
    "Salwar",
    "M.Gopi",
    "Summaya Afrin",
    "K.JAHNAVI",
    "U.HARSHAD(P)",
    "U.HARSHAD",
    "D.Begum",
    "D.Begum Thangellabi",
    "PATHANGI GOPI KRISHNA",
    "SK.MOULALI(P)",
    "SK.MOULALI(T)",
    "SK.MOULALI",
    "R.SAI TRINAYA(T)",
    "R.SAI TRINAYA",
    "RAMA RAJU SAI THRINAYA",
    "M. Harya Vardhan",
    "M.Harya Vardhan",
    "Harya Vardhan",
    "SK.SameeraSultana.",
    "SK.Sameera Sultana",
    "Jangam Rohit",
    "Chandrika pamavathi",
    "prasanna",
}

def is_junk(name):
    """Return True if the name is a time string, number, or obviously not a person."""
    # Match patterns like "55 - 10:10", "40-1:30", "15-9:05", etc.
    if re.match(r'^\d+\s*[-:]\s*[\d:]+', name.strip()):
        return True
    if re.match(r'^\d+$', name.strip()):
        return True
    if len(name.strip()) < 3:
        return True
    return False

def normalize(name):
    n = name.lower()
    n = re.sub(r'[^a-z0-9 ]', ' ', n)
    n = re.sub(r'\(p\)|\(t\)|\(mon\)|\(wed\)|\(tuesday\)|\(thursday\)', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n

ta_norm = {normalize(n) for n in TA_NAMES}

with open('faculty_master.json', encoding='utf-8') as f:
    data = json.load(f)

print(f"Before: {len(data)} entries")

updated = []
removed_junk = []

for entry in data:
    name = entry['full_name']

    # Remove junk
    if is_junk(name):
        removed_junk.append(name)
        continue

    if entry['designation'] == 'Assistant Professor':
        n = normalize(name)
        # Dr. prefix → Faculty
        if re.match(r'^dr[\.\s]', name.strip().lower()):
            entry['designation'] = 'Faculty'
        # In TA list → Teaching Assistant
        elif n in ta_norm:
            entry['designation'] = 'Teaching Assistant'
        # Mr./Ms. prefix + not Dr → Faculty (they appear in faculty section of segration)
        elif re.match(r'^(mr|ms|prof|sk)\b', name.strip().lower()):
            entry['designation'] = 'Faculty'
        # Everything else → Teaching Assistant (plain names with no prefix)
        else:
            entry['designation'] = 'Teaching Assistant'

    updated.append(entry)

print(f"Removed {len(removed_junk)} junk entries: {removed_junk}")
print(f"After: {len(updated)} entries")

# Summary
counts = {}
for e in updated:
    counts[e['designation']] = counts.get(e['designation'], 0) + 1
print("\nDesignation breakdown:")
for k, v in sorted(counts.items()):
    print(f"  {k}: {v}")

with open('faculty_master.json', 'w', encoding='utf-8') as f:
    json.dump(updated, f, indent=2, ensure_ascii=False)

print("\nDone! faculty_master.json saved.")
