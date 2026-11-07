"""Replace AIML references with ACSE across all frontend JSX files and backend Python files."""
import os
import re

REPLACEMENTS = [
    ('Artificial Intelligence & Machine Learning', 'Advanced Computer Science and Engineering'),
    ('Artificial Intelligence and Machine Learning', 'Advanced Computer Science and Engineering'),
    ('AIML Department', 'ACSE Department'),
    ('AIML AI Agent', 'ACSE AI Agent'),
    ('Ask AIML AI Agent', 'Ask ACSE AI Agent'),
    ('AIML Timetable', 'ACSE Timetable'),
    ('smart_campus_aiml', 'smart_campus_acse'),
    ('smart-campus-aiml', 'smart-campus-acse'),
    ('II AIML', 'II ACSE'),
    ('III AIML', 'III ACSE'),
    ('IV AIML', 'IV ACSE'),
]

DIRS = [
    r'c:\jyothsna\TimeTable\TimeTable\frontend\src',
    r'c:\jyothsna\TimeTable\TimeTable\backend\apps\assistant',
    r'c:\jyothsna\TimeTable\TimeTable\backend\templates',
]
EXTS = ('.jsx', '.js', '.py', '.html', '.md')

total_files = 0
for d in DIRS:
    for root, dirs, files in os.walk(d):
        for fname in files:
            if any(fname.endswith(e) for e in EXTS):
                fpath = os.path.join(root, fname)
                with open(fpath, encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                new_content = content
                for old, new in REPLACEMENTS:
                    new_content = new_content.replace(old, new)
                if new_content != content:
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f'Updated: {fpath}')
                    total_files += 1

# Also update footer in App.jsx specifically
app_jsx = r'c:\jyothsna\TimeTable\TimeTable\frontend\src\App.jsx'
with open(app_jsx, encoding='utf-8') as f:
    content = f.read()
content = content.replace('AIML Department', 'ACSE Department')
content = content.replace('VFSTR) • AIML Department', 'VFSTR) • ACSE Department')
with open(app_jsx, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\nTotal files updated: {total_files}')
print('Done!')
