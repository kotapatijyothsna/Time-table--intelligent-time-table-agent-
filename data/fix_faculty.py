"""
Fix faculty_master.json:
1. Assign correct designations based on faculty_segration.txt
2. Remove duplicates (fuzzy name matching)
3. Remove invalid entries (FSD, "Ms. P Mr. Sourabh Viswakarma", etc.)
"""

import json
import re
import uuid

# ── Designation lists from faculty_segration.txt ──────────────────────────────
FACULTY = [
    "DR. ANKAMMA RAO MALLELA", "DR. B. N. NAVEEN KUMAR", "DR. BANDI GURAVAIAH",
    "DR. G. YALAMANDA BABU", "DR. IMTIYAZ BHATT", "DR. MANIGANDAN A",
    "DR. N. BHARGAVI", "DR. P. KALPANA", "DR. RUSHI PRASAD SAHOO",
    "Dr Gurusamy Murugesan", "Dr Ramesh Kumar Mojjada", "Dr SK Satpathy",
    "Dr. A.V. Nageswara Rao", "Dr. Amar Jukuntla", "Dr. Arnab De",
    "Dr. B Sai Sambasiva Rao", "Dr. B. Jyostna Devi", "Dr. B. Sudha Rani",
    "Dr. Chennapradaga Amarendra", "Dr. D. Venkatesulu", "Dr. Eva Patel",
    "Dr. G. Kalaiarasi", "Dr. Guttikonda Prashanti", "Dr. Jawad Ahmad Dar",
    "Dr. M.Nirupama Bhat", "Dr. Mastan Sharif", "Dr. P. Giri Prasad",
    "Dr. P.M. Benson Mansingh", "Dr. S. Hanumantha Rao", "Dr. Fathimabi Shaik",
    "Dr. S.Srikantha Reddy", "Dr. Sivadi Balakrishna", "Dr. Sreenivas Peta",
    "Dr. Vinod Kumar", "Dr.Aswini", "Dr.K.Lova Raju",
    "Dr.M.Krishna Chennakesava Rao", "MR. M. Komal Krishna", "MS. D.SUPRIYA",
    "Mr Bhanu Prakash", "Mr D Vinod Kumar", "Mr K Jagadeeshwar",
    "Mr K Karthik", "Mr K Phanindra", "Mr N. Murali Krishna",
    "Mr Prajwal Santakke", "Mr Prasant Kumar Sahoo", "Mr Satyajeet Prakash",
    "Mr Siva Kumar", "Mr T Leela Uma Mahesh", "Mr Vivek Kumar Saini",
    "Mr. A Siva Ram", "Mr. A.Siva Naga Rama Gopal", "Mr. Bharadwaja Chepuri",
    "Mr. Brundavanam Satya Sai", "Mr. D. Karthik", "Mr. D. Pavan Kalyan",
    "Mr. K. Raja Dinesh", "Mr. K. Venkata Naga Vamsi", "Mr. K.Sambasivarao",
    "Mr. Mahendra Varma", "Mr. N. Murali Krishna", "Mr. Nagendra",
    "Mr. P Srinivasa Rao", "Mr. PLN Manoj Kumar",
    "Mr. PVV Satya Surya Teja Sri Manoj", "Mr. S. Uday Kiran",
    "Mr. Sattwik Barua", "Mr. Satwik Singh", "Mr. Sourabh Viswakarma",
    "Mr. Srinivas Rao Pallanti", "Mr. T. Krishna",
    "Mr. VSNS Yaswanth Kommuri", "Mr.K.Janaki Ram", "Mr.Sreekar",
    "Ms A.Ramya", "Ms Ch. Charana Sree", "Ms G Akhila", "Ms K .Supraja",
    "Ms Mohitha", "Ms Thambi Rani", "Ms Vasanthi", "Ms. A. Chandana",
    "Ms. Ambati Hemalatha", "Ms. Attuluri Ramya", "Ms. B. Bhavana Sreeja",
    "Ms. Beulah Bontha", "Ms. D. Begum Tamgellabi", "Ms. D. Urlamma",
    "Ms. G Prathyusha", "Ms. G. Mahalakshmi", "Ms. I.Leela Priya",
    "Ms. Jayamma Rodda", "Ms. K. Sabhamini", "Ms. K.Vyshnavi",
    "Ms. M. YAMINI", "Ms. N. Pooja", "Ms. Narra Bhagyalakshmi",
    "Ms. P Seetha Lakshmi", "Ms. S. RadhaRani", "Ms. Sravika Morampudi",
    "Ms. Syed Reshma", "Ms. Ugge Naga Nandini", "Ms. Vemuri Lakshmi Ravali",
    "Ms.G.Jyostna", "Ms.Jasmitha Parasa", "Prof P L N Varma", "Sk Chand Basha",
]

TEACHING_ASSISTANTS = [
    "ALUMOLU JAGADEESH REDDY", "ARIGA PRASANTHI", "B. SANGEETHA", "B. VENKAT",
    "B.HIMAJA", "B.NAVYA", "B.Sujitha", "B.Venkat", "BATTULA LEELA KRISHNA",
    "BOMMU VIDYA SRI", "D.Begum Thangellabi", "DEVARAPALLI RAJA GOPAL",
    "G.Akhila", "G.KRISHNA PRAKASH", "G.Vasanthi", "GAMPALA KRISHNA SRI",
    "GORANTLA BHARGAVI", "Harya Vardhan", "Himaja", "IMRAN KHAN PATHAN",
    "J DURGA PRASAD", "J.Divya", "K. Lakshmi Likhitha", "K.Leela Tapaswi",
    "K.Nikhitha", "K.SUSMITHA", "K.Sateesh Kumar", "K.Sushmitha",
    "KALAVATURI RANI", "L.GANESH", "M SRI CHAKRAPANI", "M. GANESH",
    "M. Pramod Chandra", "M.V J NARENDRA", "M.VISHNU VARDHAN",
    "MAHENDRA VARMA", "MARRIPATI KIRANMAYE", "Mahendra Varma",
    "Mitikala Ramanjaneyulu", "Mohammad Ruksar Afsana", "Nune Naga Surekha",
    "P. Girija", "P.CHANDRIKA PADMAVATHI", "P.MOKSHAGNA", "P.Seetha Lakshmi",
    "PANTHANGI GOPI KRISHNA", "PENDEN RUDHRA KRISHNA", "Priya Sahithi",
    "R.NAGA SUMITHRA", "R.SAI TRINAYA", "S Triveni", "S. Venkata Bhavani",
    "S.RAMYA SRI", "SANAMPUDI VENKATA KAVYANJALI", "SK .SUMAYA AFFRIN",
    "SK.MOULALI", "SK.Sameera Sultana", "SUNKARA DEVENDRA KUMAR",
    "Salwar", "Sk.summaya Afrin", "U.HARSHAD", "V PRIYA SAHITHI",
    "V S N S Yaswanth Kommuri", "V. Priya Sahithi", "V.RISHITHA",
    "VEMURI AISWARYA", "Y NAGA VYSHNAVI", "Y NEHA", "YARAGALLA KUMAR SAI",
    "prasanna",
]

OUTSOURCING = [
    "Abdul Rehman", "Francis Xavier", "K. Jnaneswar",
]

# ── Helpers ────────────────────────────────────────────────────────────────────
def normalize(name):
    """Lowercase, strip punctuation & extra spaces for fuzzy comparison."""
    n = name.lower()
    n = re.sub(r'[^a-z0-9 ]', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip()
    # remove day suffixes like (mon) (tue) (thursday) (p) (t)
    n = re.sub(r'\b(mon|tue|wed|thu|fri|saturday|sunday|thursday|tuesday|wednesday|monday)\b', '', n)
    n = re.sub(r'\(p\)|\(t\)|\(mon\)|\(wed\)|\(tuesday\)|\(thursday\)', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n

# Build lookup sets from the segration file
faculty_norm    = {normalize(n): "Faculty" for n in FACULTY}
ta_norm         = {normalize(n): "Teaching Assistant" for n in TEACHING_ASSISTANTS}
outsource_norm  = {normalize(n): "Outsourcing Staff" for n in OUTSOURCING}

def get_designation(name):
    n = normalize(name)
    if n in faculty_norm:    return "Faculty"
    if n in ta_norm:         return "Teaching Assistant"
    if n in outsource_norm:  return "Outsourcing Staff"
    # Fallback: Dr. prefix → Faculty; Mr/Ms → Faculty (keep existing)
    if re.match(r'^dr[\.\s]', name.strip().lower()):
        return "Faculty"
    return None   # unknown → keep existing

# ── INVALID entries to remove completely ──────────────────────────────────────
INVALID = {
    "fsd",
    "ms p mr sourabh viswakarma",   # garbled entry
    "mr k phanindra m vishnu vardhan",  # garbled entry
}

# ── Load data ─────────────────────────────────────────────────────────────────
with open('faculty_master.json', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total entries before cleaning: {len(data)}")

# ── Pass 1: Remove invalid/garbage entries ────────────────────────────────────
cleaned = []
removed_invalid = []
for entry in data:
    n = normalize(entry['full_name'])
    if n in INVALID:
        removed_invalid.append(entry['full_name'])
    else:
        cleaned.append(entry)

print(f"Removed {len(removed_invalid)} invalid entries: {removed_invalid}")

# ── Pass 2: Assign/update designations ───────────────────────────────────────
for entry in cleaned:
    new_desig = get_designation(entry['full_name'])
    if new_desig:
        entry['designation'] = new_desig
    # If still no match, map existing "Professor" → "Faculty",
    # "Assistant Professor" → "Faculty" (conservative fallback)
    if entry['designation'] in ("Professor", "Assistant Professor"):
        # check if Dr. prefix
        if re.match(r'^dr[\.\s]', entry['full_name'].strip().lower()):
            entry['designation'] = "Faculty"
        # else keep mapped below

# ── Pass 3: Deduplicate by normalized name (keep first occurrence) ─────────────
seen = {}
deduped = []
removed_dupes = []
for entry in cleaned:
    n = normalize(entry['full_name'])
    if n not in seen:
        seen[n] = entry
        deduped.append(entry)
    else:
        # Prefer the entry whose name matches source list exactly (better casing)
        removed_dupes.append(entry['full_name'])

print(f"Removed {len(removed_dupes)} duplicates:")
for d in removed_dupes:
    print(f"  - {d}")

print(f"\nFinal count: {len(deduped)} unique faculty entries")

# ── Designation summary ───────────────────────────────────────────────────────
desig_counts = {}
for e in deduped:
    desig_counts[e['designation']] = desig_counts.get(e['designation'], 0) + 1
print("\nDesignation breakdown:")
for k, v in sorted(desig_counts.items()):
    print(f"  {k}: {v}")

# ── Save ──────────────────────────────────────────────────────────────────────
with open('faculty_master.json', 'w', encoding='utf-8') as f:
    json.dump(deduped, f, indent=2, ensure_ascii=False)

print("\n✅ faculty_master.json updated successfully!")
