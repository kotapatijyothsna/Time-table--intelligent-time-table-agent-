"""
Debug: show entries with no faculty and what codes they have.
Also show what faculty assignments were parsed from the Excel.
"""
import os, sys, json, re
import openpyxl

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import django; django.setup()

from apps.timetables.models import TimetableEntry, TimetableVersion

version = TimetableVersion.objects.filter(is_active=True).first()
no_fac = TimetableEntry.objects.filter(timetable_version=version, faculty__isnull=True).select_related('section')

# Collect unique missing codes per section
missing = {}
for e in no_fac:
    meta = json.loads(e.original_text) if e.original_text else {}
    sec = e.section.full_name
    code = meta.get('subject_code', '?')
    stype = meta.get('type', '?')
    key = (sec, code, stype)
    missing[key] = missing.get(key, 0) + 1

print(f"\n=== Missing faculty: {len(no_fac)} entries, {len(missing)} unique sec/code combos ===")
for (sec, code, stype), cnt in sorted(missing.items())[:50]:
    print(f"  [{cnt}x] {sec} | code={code} | type={stype}")

# Now re-parse Excel to show what abbreviations were generated
XLSX = r'C:/Users/Jyothsna/.gemini/antigravity/brain/268b8c3a-7aaf-4ae9-84fb-87f996a74602/.user_uploaded/media_1793902572071_cd19a6af.xlsx'
wb = openpyxl.load_workbook(XLSX)
DAYS = {'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'}

print("\n=== Faculty assignments parsed from Excel (sample) ===")
sec_subj_fac = {}
for sname in wb.sheetnames:
    if sname == 'LIBRARY SLOTS': continue
    ws = wb[sname]
    rows = list(ws.iter_rows(values_only=True))
    current_section = None
    in_timetable = False
    for i, row in enumerate(rows):
        first = str(row[0]).strip() if row[0] else ''
        if re.match(r'^(I{1,4}V?|IV)\s+\w', first) and (len(row) < 2 or row[1] is None):
            current_section = first.strip()
            in_timetable = False
            continue
        if first == 'Period':
            in_timetable = True
            continue
        if in_timetable and not first:
            in_timetable = False
        if current_section and ':' in first:
            for col_offset in [0, 5]:
                seg = str(row[col_offset]).strip() if col_offset < len(row) and row[col_offset] else ''
                if not seg or ':' not in seg: continue
                m = re.match(r'^(.+?)\(([LPT&]+)\)\s*:\s*(.+)$', seg)
                if not m:
                    m = re.match(r'^(.+?):\s*(.+)$', seg)
                    if not m: continue
                    subj_name = m.group(1).strip()
                    stype = 'L'
                else:
                    subj_name = m.group(1).strip()
                    stype = m.group(2)
                if re.match(r'^(Agentic|Coding|CRT|Mentor|Library|Counselling|Minor|Honor|NPTEL)', subj_name):
                    continue
                words = re.sub(r'[^a-zA-Z0-9 ]', '', subj_name).split()
                abbr = ''.join(w[0].upper() for w in words if len(w) > 2)
                key = (current_section, abbr, stype)
                sec_subj_fac[key] = subj_name

for (sec, abbr, stype), name in sorted(sec_subj_fac.items())[:60]:
    print(f"  {sec} | abbr={abbr} | type={stype} | name={name}")
