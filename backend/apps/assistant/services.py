import re
import datetime
import json
import difflib
from apps.availability.services import AvailabilityService, PERIODS, DAY_NAMES
from apps.scheduling.services import SchedulingService
from apps.faculty.models import Faculty
from apps.resources.models import Resource
from apps.academics.models import AcademicSection, Subject
from apps.timetables.models import TimetableVersion, TimetableEntry, ScheduleException, ClassSwap, TimetableClash

ORDINAL_PERIOD_MAP = {
    '1st': 1, 'first': 1, '1': 1,
    '2nd': 2, 'second': 2, '2': 2,
    '3rd': 3, 'third': 3, '3': 3,
    '4th': 4, 'fourth': 4, '4': 4,
    '5th': 5, 'fifth': 5, '5': 5,
    '6th': 6, 'sixth': 6, '6': 6,
    '7th': 7, 'seventh': 7, '7': 7,
    '8th': 8, 'eighth': 8, '8': 8,
}

def parse_time_slot_and_period(prompt_lower):
    """
    Comprehensive time extraction from natural language prompts, supporting:
    - Period & hour references: '5 th hour', '5th hour', 'period 5', 'hour 5', 'fifth hour', 'p5'
    - Official breaks: 'morning break', 'lunch break'
    - Real-time anchors: 'now', 'currently', 'right now'
    - Standard times: '10:10 am', '2 pm', '14:30', 'at 11', 'at 2'
    Returns: (start_time, end_time, period_num, slot_label)
    """
    # 1. Period / Hour patterns: e.g. '5 th hour', '5th period', 'hour 5', 'period 5', 'fifth hour', 'p 5'
    m_hour = re.search(
        r'\b(1st|2nd|3rd|4th|5th|6th|7th|8th|first|second|third|fourth|fifth|sixth|seventh|eighth|[1-8])\s*(?:th|st|nd|rd)?\s*(?:hour|period|slot)\b|\b(?:hour|period|slot|p)\s*([1-8])\b',
        prompt_lower
    )
    if m_hour:
        tok = (m_hour.group(1) or m_hour.group(2)).strip()
        p_num = ORDINAL_PERIOD_MAP.get(tok)
        if not p_num and tok.isdigit():
            p_num = int(tok)
        if p_num and p_num in PERIODS:
            return PERIODS[p_num]['start'], PERIODS[p_num]['end'], p_num, PERIODS[p_num]['label']

    # 2. Morning / Lunch Break
    if 'morning break' in prompt_lower:
        return datetime.time(9, 55), datetime.time(10, 10), None, 'Morning Break (09:55 - 10:10)'
    if 'lunch break' in prompt_lower or 'lunch timing' in prompt_lower:
        return datetime.time(12, 40), datetime.time(13, 40), None, 'Lunch Break (12:40 - 13:40)'

    # 3. 'now', 'currently', 'right now'
    if any(w in prompt_lower for w in ['now', 'currently', 'right now', 'at this moment']):
        now_t = datetime.datetime.now().time()
        for p_num, p_data in PERIODS.items():
            if p_data['start'] <= now_t <= p_data['end']:
                return p_data['start'], p_data['end'], p_num, p_data['label']
        time_str = now_t.strftime('%H:%M')
        return now_t, datetime.time(min(now_t.hour + 1, 23), now_t.minute), None, f'Current Time ({time_str})'

    # 4. 12-hour with minutes and AM/PM: e.g. "10:10 am", "02:30 pm"
    m = re.search(r'\b(1[0-2]|0?[1-9]):([0-5][0-9])\s*(am|pm)\b', prompt_lower)
    if m:
        hr = int(m.group(1))
        mn = int(m.group(2))
        ampm = m.group(3)
        if ampm == 'pm' and hr < 12:
            hr += 12
        elif ampm == 'am' and hr == 12:
            hr = 0
        s_t = datetime.time(hr, mn)
        end_min = hr * 60 + mn + 50
        e_t = datetime.time(min(end_min // 60, 23), end_min % 60)
        # Check if matches period
        p_match = None
        for p_n, p_d in PERIODS.items():
            if p_d['start'] == s_t:
                p_match = p_n
                break
        lbl = PERIODS[p_match]['label'] if p_match else f"{s_t.strftime('%I:%M %p')} - {e_t.strftime('%I:%M %p')}"
        return s_t, e_t, p_match, lbl

    # 5. 24-hour HH:MM: e.g. "14:30", "10:10", "8:15"
    m = re.search(r'\b([0-1]?[0-9]|2[0-3]):([0-5][0-9])\b', prompt_lower)
    if m:
        hr = int(m.group(1))
        mn = int(m.group(2))
        s_t = datetime.time(hr, mn)
        end_min = hr * 60 + mn + 50
        e_t = datetime.time(min(end_min // 60, 23), end_min % 60)
        p_match = None
        for p_n, p_d in PERIODS.items():
            if p_d['start'] == s_t:
                p_match = p_n
                break
        lbl = PERIODS[p_match]['label'] if p_match else f"{s_t.strftime('%I:%M %p')} - {e_t.strftime('%I:%M %p')}"
        return s_t, e_t, p_match, lbl

    # 6. Hour with AM/PM: e.g. "11 am", "2 pm", "11am", "2pm"
    m = re.search(r'\b(1[0-2]|0?[1-9])\s*(am|pm)\b', prompt_lower)
    if m:
        hr = int(m.group(1))
        ampm = m.group(2)
        if ampm == 'pm' and hr < 12:
            hr += 12
        elif ampm == 'am' and hr == 12:
            hr = 0
        s_t = datetime.time(hr, 0)
        e_t = datetime.time(min(hr + 1, 23), 0)
        return s_t, e_t, None, f"{s_t.strftime('%I:%M %p')} - {e_t.strftime('%I:%M %p')}"

    # 7. "at HH" format: e.g. "at 11", "at 2", "at 14"
    m = re.search(r'\bat\s+([0-1]?[0-9]|2[0-3])\b', prompt_lower)
    if m:
        hr = int(m.group(1))
        if hr in [1, 2, 3, 4, 5]:
            hr += 12
        s_t = datetime.time(hr, 0)
        e_t = datetime.time(min(hr + 1, 23), 0)
        return s_t, e_t, None, f"{s_t.strftime('%I:%M %p')} - {e_t.strftime('%I:%M %p')}"

    # Default: Period 3 (10:10 - 11:00)
    return datetime.time(10, 10), datetime.time(11, 0), 3, 'Period 3 (10:10 - 11:00)'

def parse_time_from_prompt(prompt_lower):
    s, e, p, lbl = parse_time_slot_and_period(prompt_lower)
    return s


def find_faculty_in_prompt(prompt_lower):
    """
    Intelligent fuzzy matching of faculty names from user prompt.
    Handles split names (e.g. 'bala krishna' -> 'Dr. Sivadi Balakrishna'),
    honorifics ('sir', 'madam', 'ma'am', 'dr', 'prof'), and phonetic/substring overlap.
    """
    clean_q = re.sub(r'\b(dr\.?|mr\.?|ms\.?|mrs\.?|prof\.?|sir|madam|ma\'am|teacher)\b', '', prompt_lower)
    condensed_q = re.sub(r'[^a-z0-9]', '', clean_q)
    
    stop_tokens = {
        'free', 'today', 'tomorrow', 'class', 'classes', 'schedule', 'hour', 'period',
        'available', 'busy', 'teaching', 'subject', 'time', 'slot', 'room', 'lab',
        'who', 'what', 'when', 'which', 'show', 'tell', 'check', 'any', 'find', 'section'
    }
    q_tokens = [w for w in re.findall(r'[a-zA-Z]{3,}', clean_q) if w not in stop_tokens]
    joined_q = ''.join(q_tokens)

    scored = []
    for f in Faculty.objects.filter(is_active=True):
        fname = f.full_name.lower()
        f_clean = re.sub(r'\b(dr\.?|mr\.?|ms\.?|mrs\.?|prof\.?)\b', '', fname)
        f_condensed = re.sub(r'[^a-z0-9]', '', f_clean)
        f_tokens = [w for w in re.findall(r'[a-zA-Z]{3,}', f_clean) if w not in ['assistant', 'associate', 'professor']]

        score = 0
        # 1. Direct condensed substring match (e.g. 'balakrishna' in 'isbalakrishnasirfree')
        if f_condensed and len(f_condensed) >= 5:
            if f_condensed in condensed_q:
                score += 150 + len(f_condensed)
            elif condensed_q in f_condensed and len(condensed_q) >= 6:
                score += 120 + len(condensed_q)
            elif joined_q and (joined_q in f_condensed or f_condensed in joined_q) and len(joined_q) >= 6:
                score += 100 + len(joined_q)

        # 2. Token overlap & fuzzy similarity
        for ft in f_tokens:
            if ft in q_tokens:
                score += 30 + len(ft)
            else:
                for qt in q_tokens:
                    if len(qt) >= 4 and len(ft) >= 4:
                        ratio = difflib.SequenceMatcher(None, ft, qt).ratio()
                        if ratio >= 0.75:
                            score += int(ratio * 30)

        # 3. Faculty code match
        if f.faculty_code and f.faculty_code.lower() in clean_q:
            score += 150

        if score > 0:
            scored.append((score, f))

    scored.sort(key=lambda x: x[0], reverse=True)
    if scored and scored[0][0] >= 20:
        return scored[0][1], scored[0][0]
    return None, 0


def find_section_in_prompt(prompt_lower):
    """
    Detects academic sections in user query (e.g. 'II AIML-A', 'III CS', 'IV DS', 'II CSBS', 'II IOT').
    """
    # 1. Specific AIML / ACSE section
    m = re.search(r'\b(ii|iii|iv)\s*(?:aiml|acse)[-\s]*([a-l])\b', prompt_lower)
    if m:
        sec_name = f"{m.group(1).upper()} AIML-{m.group(2).upper()}"
        sec = AcademicSection.objects.filter(full_name=sec_name).first()
        if sec:
            return sec

    # 2. Year + Department (e.g. 'IV CS', 'III DS', 'II CSBS', 'II IOT', 'IV DS(93)')
    m_dept = re.search(r'\b(ii|iii|iv)\s*(cs|ds|csbs|iot|mtech|bs|msc)\b', prompt_lower)
    if m_dept:
        yr = m_dept.group(1).upper()
        dept_code = m_dept.group(2).upper()
        sec = AcademicSection.objects.filter(full_name__istartswith=f"{yr} {dept_code}").first()
        if sec:
            return sec

    # 3. Substring match across all sections
    for sec in AcademicSection.objects.all():
        norm_s = sec.full_name.lower().replace('-', ' ')
        if norm_s in prompt_lower:
            return sec

    return None


def find_subject_in_prompt(prompt_lower):
    """
    Detects course / subject names in prompt (e.g. 'Deep Learning', 'Text Mining', 'DBMS').
    """
    # Exclude common query words
    stop = {'today', 'tomorrow', 'classes', 'schedule', 'faculty', 'room', 'class'}
    for sub in Subject.objects.all():
        s_norm = sub.name.lower()
        if len(s_norm) >= 4 and s_norm not in stop and s_norm in prompt_lower:
            return sub
        if sub.code and len(sub.code) >= 3 and sub.code.lower() in prompt_lower:
            return sub
    return None


class AIAssistantService:
    @classmethod
    def handle_query(cls, user_prompt, conversation_id="default"):
        """
        Interprets natural-language queries using fuzzy entity matching, academic
        relationship traversal, and deterministic tool invocations, returning
        grounded answers with comprehensive evidence.
        """
        prompt_lower = user_prompt.lower()
        today = datetime.date.today()
        target_date = today

        # 1. Day of Week Resolution
        day_names_list = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        matched_day_idx = None
        for idx, d_name in enumerate(day_names_list):
            if d_name in prompt_lower:
                days_ahead = (idx - today.weekday()) % 7
                target_date = today + datetime.timedelta(days=days_ahead)
                matched_day_idx = idx
                break

        tools_invoked = []
        evidence = []
        reply = ""

        # 2. Time & Period Resolution
        start_t, end_t, period_num, slot_label = parse_time_slot_and_period(prompt_lower)
        day_display = target_date.strftime('%A, %b %d')

        # -------------------------------------------------------------
        # Category A: Timetable Clash Detection Audit
        # -------------------------------------------------------------
        if any(w in prompt_lower for w in ["clash", "clashes", "conflict", "conflicts", "collision", "double booking", "overlap"]):
            tools_invoked.append({
                "tool_name": "list_timetable_clashes",
                "parameters": {"status": "UNRESOLVED"}
            })
            unresolved = TimetableClash.objects.filter(status='UNRESOLVED').select_related(
                'entry_1', 'entry_1__section', 'entry_1__subject', 'entry_1__faculty', 'entry_1__resource',
                'entry_2', 'entry_2__section', 'entry_2__subject', 'entry_2__faculty', 'entry_2__resource'
            ).order_by('clash_type', 'overlap_start')

            fac_clashes = unresolved.filter(clash_type='FACULTY_CLASH')
            room_clashes = unresolved.filter(clash_type='CLASSROOM_CLASH')
            lab_clashes = unresolved.filter(clash_type='LAB_CLASH')
            sec_clashes = unresolved.filter(clash_type='SECTION_CLASH')

            reply = f"### Timetable Clash Detection Audit\n\n"
            reply += f"The system scanned the active timetable using half-open interval overlap `[Start1 < End2 AND Start2 < End1]` and identified **{unresolved.count()} unresolved conflict(s)**:\n\n"
            reply += f"• **Faculty Clashes:** {fac_clashes.count()} (Faculty assigned to 2 classes simultaneously)\n"
            reply += f"• **Classroom Clashes:** {room_clashes.count()} (Multiple lectures scheduled in the same room)\n"
            reply += f"• **Laboratory Clashes:** {lab_clashes.count()} (Multiple practicals overlapping in the same lab)\n"
            reply += f"• **Section Clashes:** {sec_clashes.count()} (A student cohort assigned to multiple rooms)\n\n"

            sample_clashes = list(unresolved[:5])
            if sample_clashes:
                reply += "**Sample Detected Conflicts:**\n"
                days_abbr = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
                for c in sample_clashes:
                    d_name = days_abbr[c.day_of_week] if 0 <= c.day_of_week < len(days_abbr) else 'Day'
                    reply += f"• **[{c.clash_type.replace('_', ' ')}]** ({d_name} {c.overlap_start.strftime('%H:%M')}-{c.overlap_end.strftime('%H:%M')} | {c.overlap_duration_minutes}m overlap)\n  {c.explanation}\n"

            reply += "\nYou can view, filter, and resolve these in the **Admin Portal → Timetable Clash Detection** dashboard."
            evidence.append({
                "total_unresolved": unresolved.count(),
                "faculty_clashes": fac_clashes.count(),
                "classroom_clashes": room_clashes.count(),
                "lab_clashes": lab_clashes.count(),
                "section_clashes": sec_clashes.count()
            })
            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": tools_invoked,
                "evidence": evidence
            }

        # -------------------------------------------------------------
        # Category B: College Hours & Break Timings
        # -------------------------------------------------------------
        if any(w in prompt_lower for w in ["college hours", "working hours", "break timing", "period timing", "lunch timing", "morning break", "when is break", "college timing"]):
            reply = "### Campus College Working Hours & Break Schedule\n\n"
            reply += "• **College Working Hours:** **08:15 AM - 04:05 PM** (Monday to Saturday)\n"
            reply += "• **Morning Break:** **09:55 AM - 10:10 AM** (15 minutes)\n"
            reply += "• **Lunch Break:** **12:40 PM - 01:40 PM** (60 minutes)\n\n"
            reply += "**Academic Period Breakdown:**\n"
            reply += "- **Period 1:** 08:15 AM - 09:05 AM\n"
            reply += "- **Period 2:** 09:05 AM - 09:55 AM\n"
            reply += "- ☕ **Morning Break:** 09:55 AM - 10:10 AM *(All rooms and faculty available)*\n"
            reply += "- **Period 3:** 10:10 AM - 11:00 AM\n"
            reply += "- **Period 4:** 11:00 AM - 11:50 AM\n"
            reply += "- **Period 5:** 11:50 AM - 12:40 PM\n"
            reply += "- 🍱 **Lunch Break:** 12:40 PM - 01:40 PM *(All rooms and faculty available)*\n"
            reply += "- **Period 6:** 01:40 PM - 02:30 PM\n"
            reply += "- **Period 7:** 02:30 PM - 03:20 PM\n"
            reply += "- **Period 8:** 03:20 PM - 04:05 PM\n\n"
            reply += "*Note: Before 08:15 AM and after 04:05 PM, as well as during official breaks, no classrooms or labs are occupied by scheduled classes, and all faculty are available.*"
            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": [{"tool_name": "get_college_hours_and_breaks", "parameters": {}}],
                "evidence": evidence
            }

        # -------------------------------------------------------------
        # Category C: CRT-FSD or Villas Sir
        # -------------------------------------------------------------
        if any(w in prompt_lower for w in ["crt", "fsd", "villas", "outsourced"]):
            villas = Faculty.objects.filter(full_name__icontains="villas").first()
            if villas:
                eval_res = AvailabilityService.evaluate_faculty_status(villas, target_date, start_t, end_t)
                entries_count = TimetableEntry.objects.filter(faculty=villas, is_active=True).count()
                reply = f"### CRT-FSD Faculty Profile: **{villas.full_name}**\n\n"
                reply += f"• **Role:** External Technical Trainer / Outsourced Faculty (`{villas.faculty_type}`)\n"
                reply += f"• **Department:** {villas.department.code if villas.department else 'AIML'}\n"
                reply += f"• **Specialization:** **CRT-FSD** (Campus Recruitment Training — Full Stack Development)\n"
                reply += f"• **Teaching Load:** {entries_count} scheduled timetable sessions across third-year and fourth-year cohorts.\n"
                reply += f"• **Current Status ({slot_label} on {day_display}):** **{eval_res['status'].upper()}**\n"
                if eval_res['status'] == 'Occupied' and eval_res.get('evidence'):
                    ev = eval_res['evidence']
                    reply += f"  - Currently teaching: **{ev['subject']}** for **{ev['section']}** in **Room {ev['room']}** ({ev['start_time']}-{ev['end_time']})\n"
                else:
                    reply += f"  - Reason: *{eval_res['reason']}*\n"
                return {
                    "conversation_id": conversation_id,
                    "reply": reply,
                    "tools_invoked": [{"tool_name": "get_faculty_profile", "parameters": {"name": villas.full_name}}],
                    "evidence": [eval_res]
                }

        # -------------------------------------------------------------
        # Category D: Class Swaps
        # -------------------------------------------------------------
        if any(w in prompt_lower for w in ["class swap", "how to swap", "swap class", "swapped", "exchange class", "exchanged"]):
            swaps = ClassSwap.objects.filter(swap_date=target_date).select_related('faculty_1', 'faculty_2', 'entry_1', 'entry_2')
            if swaps.exists():
                swap_lines = []
                for s in swaps:
                    swap_lines.append(f"• **{s.faculty_1.full_name}** ⇄ **{s.faculty_2.full_name}** [{s.status}]\n  - {s.entry_1.section.full_name} ({s.entry_1.subject.name}) swapped with {s.entry_2.section.full_name} ({s.entry_2.subject.name})\n  - Reason: *{s.reason}*")
                reply = f"**{swaps.count()} Approved Class Swap(s) on {day_display}:**\n\n" + "\n\n".join(swap_lines)
            else:
                reply = f"### Class Swap Management\n\nThere are **0 class swaps** logged for **{day_display}**.\n\n"
                reply += "**How Class Swap Works:**\n"
                reply += "1. Navigate to **Admin Portal → Leave & Swap Manager → Class Swaps**.\n"
                reply += "2. Select Date, Faculty 1, and their period slot.\n"
                reply += "3. Select Faculty 2 and their period slot.\n"
                reply += "4. Click **Validate Swap** to check for timetable conflicts.\n"
                reply += "5. Upon confirmation, both faculty schedules and availability will update dynamically."
            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": [{"tool_name": "list_class_swaps", "parameters": {"date": str(target_date)}}],
                "evidence": evidence
            }

        # -------------------------------------------------------------
        # Category E: Schedule Exceptions, Cancellations, or Substitutions
        # -------------------------------------------------------------
        if any(w in prompt_lower for w in ["exception", "cancellation", "cancel", "substitut", "leave", "reallocat", "can 4th year"]):
            if "can 4th year" in prompt_lower or "4th year faculty" in prompt_lower or "fourth year" in prompt_lower:
                reply = "### Strict 4th-Year Faculty Exclusivity Policy\n\n"
                reply += "• **Policy:** Faculty members exclusively assigned to 4th-year cohorts (e.g. Abdul Rehman) are **RESTRICTED** from substituting for 2nd-year or 3rd-year classes.\n"
                reply += "• **Rationale:** Final-year curriculum requirements and specialized project supervision demand that dedicated 4th-year faculty cannot take lower-division substitutions.\n"
                reply += "• **Exception:** Faculty members who already teach across multiple academic years (e.g. Dr. Ramesh Kumar Mojjada) are permitted to substitute across their qualified subjects."
                return {
                    "conversation_id": conversation_id,
                    "reply": reply,
                    "tools_invoked": [{"tool_name": "get_substitution_policy", "parameters": {}}],
                    "evidence": []
                }

            tools_invoked.append({
                "tool_name": "list_schedule_exceptions",
                "parameters": {"date": str(target_date)}
            })
            exceptions = ScheduleException.objects.filter(
                exception_date=target_date
            ).select_related('timetable_entry', 'timetable_entry__section', 'timetable_entry__subject', 'replacement_faculty', 'replacement_resource')

            if not exceptions.exists():
                upcoming = ScheduleException.objects.filter(
                    exception_date__gte=today
                ).select_related('timetable_entry', 'timetable_entry__section', 'timetable_entry__subject', 'replacement_faculty', 'replacement_resource').order_by('exception_date')[:5]

                if upcoming.exists():
                    up_list = []
                    for ex in upcoming:
                        sec = ex.timetable_entry.section.full_name
                        sub = ex.timetable_entry.subject.name
                        extra = ""
                        if ex.exception_type == 'SUBSTITUTE' and ex.replacement_faculty:
                            extra = f" (Substitute: {ex.replacement_faculty.full_name})"
                        elif ex.exception_type == 'RESOURCE_CHANGE' and ex.replacement_resource:
                            extra = f" (New Room: {ex.replacement_resource.code})"
                        up_list.append(f"• **{ex.exception_date}** [{ex.exception_type}]: {sec} — {sub}{extra}. Reason: *{ex.reason}*")
                    reply = f"No schedule exceptions or cancellations logged for **{day_display}**.\n\n**Upcoming Logged Exceptions:**\n" + "\n".join(up_list)
                else:
                    reply = f"There are currently **0 schedule exceptions, cancellations, or substitutions** logged for {day_display} or upcoming dates in the system."
            else:
                ex_list = []
                for ex in exceptions:
                    sec = ex.timetable_entry.section.full_name
                    sub = ex.timetable_entry.subject.name
                    extra = ""
                    if ex.exception_type == 'SUBSTITUTE' and ex.replacement_faculty:
                        extra = f" (Substituted by: **{ex.replacement_faculty.full_name}**)"
                    elif ex.exception_type == 'RESOURCE_CHANGE' and ex.replacement_resource:
                        extra = f" (Reallocated to: **Room {ex.replacement_resource.code}**)"
                    ex_list.append(f"• **[{ex.exception_type}]** {sec} | {sub}{extra}\n  *Slot:* {ex.timetable_entry.start_time.strftime('%I:%M %p')}-{ex.timetable_entry.end_time.strftime('%I:%M %p')} | *Reason:* {ex.reason}")
                reply = f"**{exceptions.count()} Active Schedule Exception(s) on {day_display}:**\n\n" + "\n\n".join(ex_list)

            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": tools_invoked,
                "evidence": evidence
            }

        # -------------------------------------------------------------
        # Category F: Specific Room or Laboratory Query
        # -------------------------------------------------------------
        room_match = re.search(r'\b(?:room|lab)\s*([a-zA-Z0-9\-]+)\b', prompt_lower)
        if room_match:
            rcode = room_match.group(1).upper()
            res_obj = Resource.objects.filter(code__iexact=rcode).first()
            if res_obj:
                eval_res = AvailabilityService.evaluate_resource_status(res_obj, target_date, start_t, end_t)
                status_raw = eval_res["status"]
                status_norm = status_raw.upper()
                tools_invoked.append({
                    "tool_name": "get_resource_timetable",
                    "parameters": {"room": res_obj.code, "date": str(target_date), "start_time": str(start_t)}
                })

                if status_norm == "OCCUPIED" and eval_res.get("evidence"):
                    ev = eval_res["evidence"]
                    facs = ev.get("faculty", "Assigned Faculty")
                    reply = f"**Room {res_obj.code}** is **OCCUPIED** during **{slot_label}** on {day_display}.\n\n"
                    reply += f"• **Class Cohort:** {ev['section']}\n"
                    reply += f"• **Subject:** {ev['subject']}\n"
                    reply += f"• **Assigned Faculty:** {facs}\n"
                    reply += f"• **Scheduled Duration:** {ev['start_time']} - {ev['end_time']}\n"
                    reply += f"• **Room Capacity:** {res_obj.capacity} seats"
                    evidence.append(ev)
                elif status_norm in ["AVAILABLE", "UNOCCUPIED"]:
                    reply = f"**Room {res_obj.code}** ({res_obj.capacity} seats) is verified **AVAILABLE** during **{slot_label}** on {day_display}.\n\n*(Status Reason: {eval_res['reason']})*"
                    evidence.append({"room": res_obj.code, "status": "AVAILABLE"})
                else:
                    reply = f"**Room {res_obj.code}** is currently **{status_raw}**: {eval_res['reason']}."

                return {
                    "conversation_id": conversation_id,
                    "reply": reply,
                    "tools_invoked": tools_invoked,
                    "evidence": evidence
                }

        # -------------------------------------------------------------
        # Category G: Specific Faculty Query (Fuzzy / Intelligent Match)
        # -------------------------------------------------------------
        fac_found, match_score = find_faculty_in_prompt(prompt_lower)
        if fac_found and match_score >= 20:
            eval_res = AvailabilityService.evaluate_faculty_status(fac_found, target_date, start_t, end_t)
            status_norm = eval_res["status"].upper()
            version = AvailabilityService.get_active_version()

            # Fetch today's schedule for this faculty member
            day_idx = target_date.weekday()
            fac_today_entries = TimetableEntry.objects.filter(
                timetable_version=version,
                faculty=fac_found,
                day_of_week=day_idx,
                is_active=True
            ).select_related('section', 'subject', 'resource').order_by('start_time')

            schedule_bullets = []
            for e in fac_today_entries:
                r_code = e.resource.code if e.resource else 'Unassigned'
                schedule_bullets.append(f"• **{e.start_time.strftime('%H:%M')} - {e.end_time.strftime('%H:%M')}:** {e.subject.name} for {e.section.full_name} in Room {r_code}")

            tools_invoked.append({
                "tool_name": "search_faculty_availability",
                "parameters": {"faculty": fac_found.full_name, "date": str(target_date), "start_time": str(start_t)}
            })

            # Check if user asked whether faculty is free or busy
            is_asking_free = any(w in prompt_lower for w in ['free', 'available', 'busy', 'occupied', 'vacant'])
            
            if status_norm == "OCCUPIED" and eval_res.get("evidence"):
                ev = eval_res["evidence"]
                reply = f"**{fac_found.full_name}** ({fac_found.faculty_code or 'Faculty'}) is **OCCUPIED / BUSY** during **{slot_label}** on {day_display}.\n\n"
                reply += f"• **Current Class:** {ev['subject']} for **{ev['section']}**\n"
                reply += f"• **Classroom / Lab:** Room {ev['room']}\n"
                reply += f"• **Scheduled Duration:** {ev['start_time']} - {ev['end_time']}\n"
                evidence.append(ev)
            else:
                reply = f"Yes, **{fac_found.full_name}** ({fac_found.faculty_code or 'Faculty'}) is verified **AVAILABLE** during **{slot_label}** on {day_display}.\n\n"
                reply += f"*(Status Reason: {eval_res['reason']})*\n"
                evidence.append({"faculty": fac_found.full_name, "status": "AVAILABLE", "slot": slot_label})

            if schedule_bullets:
                reply += f"\n**Scheduled Classes for {fac_found.full_name} on {target_date.strftime('%A')}:**\n" + "\n".join(schedule_bullets)
            else:
                reply += f"\n*(No scheduled classes in the timetable for {fac_found.full_name} on {target_date.strftime('%A')}.)*"

            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": tools_invoked,
                "evidence": evidence
            }

        # -------------------------------------------------------------
        # Category H: Section Timetable Query (e.g. 'schedule for II AIML-A')
        # -------------------------------------------------------------
        sec_found = find_section_in_prompt(prompt_lower)
        if sec_found:
            version = AvailabilityService.get_active_version()
            day_idx = target_date.weekday()
            sec_entries = TimetableEntry.objects.filter(
                timetable_version=version,
                section=sec_found,
                day_of_week=day_idx,
                is_active=True
            ).select_related('subject', 'faculty', 'resource').order_by('start_time')

            tools_invoked.append({
                "tool_name": "get_section_timetable",
                "parameters": {"section": sec_found.full_name, "day": day_names_list[day_idx]}
            })

            reply = f"### Timetable for **{sec_found.full_name}** on **{day_display}**\n\n"
            if sec_entries.exists():
                for se in sec_entries:
                    fac_name = se.faculty.full_name if se.faculty else "Department Faculty"
                    rm = f"Room {se.resource.code}" if se.resource else "Unassigned"
                    reply += f"• **{se.start_time.strftime('%H:%M')} - {se.end_time.strftime('%H:%M')}:** {se.subject.name} | *Faculty:* {fac_name} | *Location:* {rm}\n"
                    evidence.append({
                        "time": f"{se.start_time.strftime('%H:%M')}-{se.end_time.strftime('%H:%M')}",
                        "subject": se.subject.name,
                        "faculty": fac_name,
                        "room": rm
                    })
            else:
                reply += f"No scheduled classes found for {sec_found.full_name} on {target_date.strftime('%A')}."

            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": tools_invoked,
                "evidence": evidence
            }

        # -------------------------------------------------------------
        # Category I: Subject / Teacher Query (e.g. 'who teaches Deep Learning?')
        # -------------------------------------------------------------
        sub_found = find_subject_in_prompt(prompt_lower)
        if sub_found:
            version = AvailabilityService.get_active_version()
            sub_entries = TimetableEntry.objects.filter(
                timetable_version=version,
                subject=sub_found,
                faculty__isnull=False,
                is_active=True
            ).select_related('faculty', 'section', 'resource').order_by('section__full_name')

            tools_invoked.append({
                "tool_name": "search_subject_allocations",
                "parameters": {"subject": sub_found.name}
            })

            reply = f"### Faculty Allocated to **{sub_found.name}** ({sub_found.code or 'Course'}):\n\n"
            fac_section_map = {}
            for se in sub_entries:
                fn = se.faculty.full_name
                sec_n = se.section.full_name
                if fn not in fac_section_map:
                    fac_section_map[fn] = set()
                fac_section_map[fn].add(sec_n)

            if fac_section_map:
                for fn, secs in sorted(fac_section_map.items()):
                    reply += f"• **{fn}:** Teaching {', '.join(sorted(secs))}\n"
                    evidence.append({"faculty": fn, "sections": list(secs)})
            else:
                reply += f"No dedicated faculty assignments found in active timetable for {sub_found.name}."

            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": tools_invoked,
                "evidence": evidence
            }

        # -------------------------------------------------------------
        # Category J: Free Faculty Directory Search
        # -------------------------------------------------------------
        if any(k in prompt_lower for k in ["faculty", "prof", "who is free", "free faculty", "available faculty", "free teacher", "teachers free"]):
            tools_invoked.append({
                "tool_name": "search_faculty_availability",
                "parameters": {"date": str(target_date), "start_time": str(start_t), "end_time": str(end_t)}
            })

            free_facs = []
            seen = set()
            for f in Faculty.objects.filter(is_active=True).select_related('department').order_by('full_name'):
                norm = " ".join(f.full_name.lower().split())
                if norm in seen:
                    continue
                eval_res = AvailabilityService.evaluate_faculty_status(f, target_date, start_t, end_t)
                if eval_res["status"].upper() in ["AVAILABLE", "UNOCCUPIED"]:
                    seen.add(norm)
                    dept_tag = f" [{f.department.code}]" if f.department else ""
                    id_tag = f" ({f.faculty_code})" if f.faculty_code else ""
                    free_facs.append(f"{f.full_name}{id_tag}{dept_tag}")

            if free_facs:
                sample_str = "\n- " + "\n- ".join(free_facs[:10])
                reply = f"Found **{len(free_facs)} verified available faculty members** during **{slot_label}** on {day_display}:\n{sample_str}"
                if len(free_facs) > 10:
                    reply += f"\n\n*(and {len(free_facs) - 10} more available faculty across departments)*"
            else:
                reply = f"All faculty members have scheduled classes during **{slot_label}** on {day_display}."

            evidence.append({"available_count": len(free_facs), "sample": free_facs[:10]})
            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": tools_invoked,
                "evidence": evidence
            }

        # -------------------------------------------------------------
        # Category K: Classroom / Laboratory Vacancy Search
        # -------------------------------------------------------------
        is_lab = bool(re.search(r'\b(?:labs?|laborator(?:y|ies))\b', prompt_lower))
        is_classroom = bool(re.search(r'\b(?:classrooms?|rooms?)\b', prompt_lower)) or "free room" in prompt_lower or "available room" in prompt_lower

        if is_lab or is_classroom:
            res_type = 'LABORATORY' if is_lab else 'CLASSROOM'
            type_label = "laboratories" if is_lab else "classrooms"

            cap_match = re.search(r'\b(?:for\s+)?(\d{2,3})\s*(?:students?|seats?|capacity)?\b', prompt_lower)
            min_cap = int(cap_match.group(1)) if cap_match and int(cap_match.group(1)) <= 150 else 30

            tools_invoked.append({
                "tool_name": "search_classroom_availability",
                "parameters": {"date": str(target_date), "start_time": str(start_t), "end_time": str(end_t), "type": res_type, "min_capacity": min_cap}
            })

            recs = SchedulingService.recommend_classrooms(target_date, start_t, end_t, min_capacity=min_cap, resource_type=res_type)
            if recs:
                rooms_str = "\n".join([f"• **Room {r['code']}** ({r['capacity']} seats) — Verified Available" for r in recs[:8]])
                reply = f"Verified available {type_label} (min {min_cap} seats) for **{slot_label}** on {day_display}:\n\n{rooms_str}"
                if len(recs) > 8:
                    reply += f"\n\n*(and {len(recs) - 8} more available {type_label})*"
                evidence.extend(recs[:8])
            else:
                reply = f"No {type_label} with at least {min_cap} seats are verified available for **{slot_label}** on {day_display}."

            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": tools_invoked,
                "evidence": evidence
            }

        # -------------------------------------------------------------
        # Category L: Website Navigation & Feature Overview
        # -------------------------------------------------------------
        if any(w in prompt_lower for w in ["how to", "features", "website", "dashboard", "ready to use", "portal", "help"]):
            reply = "### Smart Campus Timetable & Resource Management Guide\n\n"
            reply += "Here is how to use the key features on this portal:\n\n"
            reply += "1. **Live Dashboard:** Displays real-time classroom, lab, and faculty availability dynamically between **08:15 AM and 04:05 PM** based on actual system time. Highlights ongoing periods and break states.\n"
            reply += "2. **Ready-to-Use Classrooms:** Shows instant unoccupied rooms filtered by seating capacity for impromptu lectures or study sessions.\n"
            reply += "3. **Timetable Viewers:** View interactive weekly matrices for **44 Academic Sections**, **213 Faculty Members**, and **46 Classrooms & Labs**.\n"
            reply += "4. **Admin Portal:**\n"
            reply += "   - **Class Swap:** Mutual period exchange between two teachers with real-time overlap validation.\n"
            reply += "   - **Substitution Manager:** Categorizes eligible replacement faculty (Same Subject, Same Class, Other Eligible) and enforces 4th-Year Exclusivity Rules.\n"
            reply += "   - **Timetable Clash Detection:** Real-time audit of double bookings across faculty, rooms, and labs.\n"
            reply += "5. **Campus AI:** Ask any natural language question about schedules, teachers, rooms, or policies!"
            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": [{"tool_name": "get_portal_guide", "parameters": {}}],
                "evidence": []
            }

        # -------------------------------------------------------------
        # Category M: Intelligent Keyword Fallback
        # -------------------------------------------------------------
        # Extract meaningful terms to search across faculty, subjects, and rooms
        tokens = [t for t in re.findall(r'[a-zA-Z]{4,}', prompt_lower) if t not in stop_tokens]
        matched_facs = []
        matched_rooms = []
        matched_subs = []
        for t in tokens:
            f = Faculty.objects.filter(full_name__icontains=t).first()
            if f and f not in matched_facs:
                matched_facs.append(f)
            r = Resource.objects.filter(code__icontains=t).first()
            if r and r not in matched_rooms:
                matched_rooms.append(r)
            s = Subject.objects.filter(name__icontains=t).first()
            if s and s not in matched_subs:
                matched_subs.append(s)

        if matched_facs or matched_rooms or matched_subs:
            reply = f"Here is the verified academic data related to your question:\n\n"
            if matched_facs:
                reply += "**Matched Faculty:**\n"
                for f in matched_facs[:3]:
                    st = AvailabilityService.evaluate_faculty_status(f, target_date, start_t, end_t)
                    reply += f"• **{f.full_name}** ({f.department.code if f.department else 'AIML'}): Currently **{st['status'].upper()}** for {slot_label}\n"
            if matched_rooms:
                reply += "\n**Matched Rooms / Labs:**\n"
                for r in matched_rooms[:3]:
                    st = AvailabilityService.evaluate_resource_status(r, target_date, start_t, end_t)
                    reply += f"• **Room {r.code}** ({r.capacity} seats): **{st['status'].upper()}** for {slot_label}\n"
            if matched_subs:
                reply += "\n**Matched Courses / Subjects:**\n"
                for s in matched_subs[:3]:
                    reply += f"• **{s.name}** ({s.code or 'Course'})\n"
            reply += f"\n*(Query evaluated for {day_display} during {slot_label})*"
            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": [{"tool_name": "keyword_search", "parameters": {"tokens": tokens}}],
                "evidence": evidence
            }

        # General Guidance
        reply = (
            "I can assist you with real-time faculty availability, classroom & laboratory schedules, "
            "section timetables, schedule exceptions, class swaps, and substitutions.\n\n"
            "Try asking questions like:\n"
            "• *'Is Bala Krishna sir free on 5th hour today?'*\n"
            "• *'Which AIML faculty are free at 11 AM today?'*\n"
            "• *'Find an available classroom for 50 students at 10:10 AM'*\n"
            "• *'Is Dr. Sudha Rani teaching any class at 2 PM?'*\n"
            "• *'What is the timetable for II AIML-A on Monday?'*\n"
            "• *'Who teaches Deep Learning?'*\n"
            "• *'Are any computer labs free on Friday morning?'*\n"
            "• *'Are there any timetable clashes or conflicts?'*\n"
            "• *'How do I swap a class?'*"
        )
        return {
            "conversation_id": conversation_id,
            "reply": reply,
            "tools_invoked": tools_invoked,
            "evidence": evidence
        }
