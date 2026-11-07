import re
import datetime
import json
from apps.availability.services import AvailabilityService
from apps.scheduling.services import SchedulingService
from apps.faculty.models import Faculty
from apps.resources.models import Resource
from apps.timetables.models import TimetableVersion, TimetableEntry, ScheduleException, ClassSwap, TimetableClash

def parse_time_from_prompt(prompt_lower):
    """
    Robust time extraction from natural language prompts, prioritizing
    explicit HH:MM AM/PM over ambiguous single numbers.
    """
    # 1. 12-hour with minutes and AM/PM: e.g. "10:10 am", "02:30 pm"
    m = re.search(r'\b(1[0-2]|0?[1-9]):([0-5][0-9])\s*(am|pm)\b', prompt_lower)
    if m:
        hr = int(m.group(1))
        mn = int(m.group(2))
        ampm = m.group(3)
        if ampm == 'pm' and hr < 12:
            hr += 12
        elif ampm == 'am' and hr == 12:
            hr = 0
        return datetime.time(hr, mn)

    # 2. 24-hour HH:MM or general HH:MM: e.g. "14:30", "10:10", "8:15"
    m = re.search(r'\b([0-1]?[0-9]|2[0-3]):([0-5][0-9])\b', prompt_lower)
    if m:
        hr = int(m.group(1))
        mn = int(m.group(2))
        return datetime.time(hr, mn)

    # 3. Hour with AM/PM: e.g. "11 am", "2 pm", "11am", "2pm"
    m = re.search(r'\b(1[0-2]|0?[1-9])\s*(am|pm)\b', prompt_lower)
    if m:
        hr = int(m.group(1))
        ampm = m.group(2)
        if ampm == 'pm' and hr < 12:
            hr += 12
        elif ampm == 'am' and hr == 12:
            hr = 0
        return datetime.time(hr, 0)

    # 4. "at HH" format: e.g. "at 11", "at 2", "at 14"
    m = re.search(r'\bat\s+([0-1]?[0-9]|2[0-3])\b', prompt_lower)
    if m:
        hr = int(m.group(1))
        if hr in [1, 2, 3, 4, 5]:  # campus afternoon hours default
            hr += 12
        return datetime.time(hr, 0)

    return None


class AIAssistantService:
    @classmethod
    def handle_query(cls, user_prompt, conversation_id="default"):
        """
        Interprets natural-language queries using regex entity matching and
        deterministic tool invocations, returning grounded answers with evidence.
        """
        prompt_lower = user_prompt.lower()
        today = datetime.date.today()
        target_date = today

        # Check if user mentioned a specific day of week
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for idx, d_name in enumerate(day_names):
            if d_name in prompt_lower:
                days_ahead = (idx - today.weekday()) % 7
                target_date = today + datetime.timedelta(days=days_ahead)
                break

        tools_invoked = []
        evidence = []
        reply = ""

        # Parse time slot
        parsed_time = parse_time_from_prompt(prompt_lower)
        if parsed_time:
            start_t = parsed_time
            end_min = start_t.hour * 60 + start_t.minute + 50
            end_t = datetime.time(min(end_min // 60, 23), end_min % 60)
        else:
            start_t = datetime.time(10, 10)
            end_t = datetime.time(11, 0)

        # 0A. Check for Timetable Clashes or Conflicts Query
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
                day_names_list = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
                for c in sample_clashes:
                    d_name = day_names_list[c.day_of_week] if 0 <= c.day_of_week < len(day_names_list) else 'Day'
                    reply += f"• **[{c.clash_type.replace('_', ' ')}]** ({d_name} {c.overlap_start.strftime('%H:%M')}–{c.overlap_end.strftime('%H:%M')} | {c.overlap_duration_minutes}m overlap)\n  {c.explanation}\n"

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

        # 0B. Check for College Hours, Break Timings, or Period Timings Query
        if any(w in prompt_lower for w in ["break", "breaks", "college hours", "working hours", "college start", "college end", "class timing", "period timing", "lunch timing", "morning break"]):
            reply = "### Campus College Working Hours & Break Schedule\n\n"
            reply += "• **College Working Hours:** **08:15 AM – 04:05 PM** (Monday to Saturday)\n"
            reply += "• **Morning Break:** **09:55 AM – 10:10 AM** (15 minutes)\n"
            reply += "• **Lunch Break:** **12:40 PM – 01:40 PM** (60 minutes)\n\n"
            reply += "**Academic Period Breakdown:**\n"
            reply += "- **Period 1:** 08:15 AM – 09:05 AM\n"
            reply += "- **Period 2:** 09:05 AM – 09:55 AM\n"
            reply += "- ☕ **Morning Break:** 09:55 AM – 10:10 AM *(All rooms and faculty available)*\n"
            reply += "- **Period 3:** 10:10 AM – 11:00 AM\n"
            reply += "- **Period 4:** 11:00 AM – 11:50 AM\n"
            reply += "- **Period 5:** 11:50 AM – 12:40 PM\n"
            reply += "- 🍱 **Lunch Break:** 12:40 PM – 01:40 PM *(All rooms and faculty available)*\n"
            reply += "- **Period 6:** 01:40 PM – 02:30 PM\n"
            reply += "- **Period 7:** 02:30 PM – 03:20 PM\n"
            reply += "- **Period 8:** 03:20 PM – 04:05 PM\n\n"
            reply += "*Note: Before 08:15 AM and after 04:05 PM, as well as during official breaks, no classrooms or labs are occupied by scheduled classes, and all faculty are available.*"
            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": [{"tool_name": "get_college_hours_and_breaks", "parameters": {}}],
                "evidence": evidence
            }

        # 0C. Check for CRT-FSD or Villas Sir Query
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
                reply += f"• **Current Status ({start_t.strftime('%I:%M %p')} on {target_date.strftime('%A, %b %d')}):** **{eval_res['status'].upper()}**\n"
                if eval_res['status'] == 'Occupied' and eval_res.get('evidence'):
                    ev = eval_res['evidence']
                    reply += f"  - Currently teaching: **{ev['subject']}** for **{ev['section']}** in **Room {ev['room']}** ({ev['start_time']}–{ev['end_time']})\n"
                else:
                    reply += f"  - Reason: *{eval_res['reason']}*\n"
                return {
                    "conversation_id": conversation_id,
                    "reply": reply,
                    "tools_invoked": [{"tool_name": "get_faculty_profile", "parameters": {"name": villas.full_name}}],
                    "evidence": [eval_res]
                }

        # 0D. Check for Class Swaps Query
        if any(w in prompt_lower for w in ["class swap", "swaps", "swapped", "exchange class", "exchanged class"]):
            swaps = ClassSwap.objects.filter(swap_date=target_date).select_related('faculty_1', 'faculty_2', 'entry_1', 'entry_2')
            if swaps.exists():
                swap_lines = []
                for s in swaps:
                    swap_lines.append(f"• **{s.faculty_1.full_name}** ⇄ **{s.faculty_2.full_name}** [{s.status}]\n  - {s.entry_1.section.full_name} ({s.entry_1.subject.name}) swapped with {s.entry_2.section.full_name} ({s.entry_2.subject.name})\n  - Reason: *{s.reason}*")
                reply = f"**{swaps.count()} Approved Class Swap(s) on {target_date.strftime('%A, %b %d')}:**\n\n" + "\n\n".join(swap_lines)
            else:
                reply = f"There are **0 class swaps** logged for **{target_date.strftime('%A, %b %d')}**.\n\nYou can configure and preview mutual teacher class swaps under **Admin Portal → Leave & Swap Manager → Class Swaps**."
            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": [{"tool_name": "list_class_swaps", "parameters": {"date": str(target_date)}}],
                "evidence": evidence
            }

        # 0E. Check for Schedule Exceptions, Cancellations, or Substitutions query
        if any(w in prompt_lower for w in ["exception", "cancellation", "cancel", "substitut", "leave", "reallocat"]):
            tools_invoked.append({
                "tool_name": "list_schedule_exceptions",
                "parameters": {"date": str(target_date)}
            })
            exceptions = ScheduleException.objects.filter(
                exception_date=target_date
            ).select_related('timetable_entry', 'timetable_entry__section', 'timetable_entry__subject', 'replacement_faculty', 'replacement_resource')

            if not exceptions.exists():
                # Also check upcoming exceptions
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
                    reply = f"No schedule exceptions or cancellations logged for **{target_date.strftime('%A, %b %d')}**.\n\n**Upcoming Logged Exceptions:**\n" + "\n".join(up_list)
                else:
                    reply = f"There are currently **0 schedule exceptions, cancellations, or substitutions** logged for {target_date.strftime('%A, %b %d')} or upcoming dates in the system."
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
                    ex_list.append(f"• **[{ex.exception_type}]** {sec} | {sub}{extra}\n  *Slot:* {ex.timetable_entry.start_time.strftime('%I:%M %p')}–{ex.timetable_entry.end_time.strftime('%I:%M %p')} | *Reason:* {ex.reason}")
                reply = f"**{exceptions.count()} Active Schedule Exception(s) on {target_date.strftime('%A, %b %d')}:**\n\n" + "\n\n".join(ex_list)

            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": tools_invoked,
                "evidence": evidence
            }

        # Detect Room query: e.g. "room 604", "room 619", "who is in 604"
        room_match = re.search(r'\b(?:room|lab)\s*([a-zA-Z0-9\-]+)\b', prompt_lower)
        target_room_code = None
        if room_match:
            target_room_code = room_match.group(1).upper()

        version = AvailabilityService.get_active_version()

        # 1. Room-specific query
        if target_room_code:
            res_obj = Resource.objects.filter(code__iexact=target_room_code).first()
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
                    reply = f"**Room {res_obj.code}** is currently **OCCUPIED** between {start_t.strftime('%I:%M %p')} and {end_t.strftime('%I:%M %p')} on {target_date.strftime('%A, %b %d')}.\n\n• **Class:** {ev['section']}\n• **Subject:** {ev['subject']}\n• **Assigned Faculty:** {facs}\n• **Time Slot:** {ev['start_time']} – {ev['end_time']}"
                    evidence.append(ev)
                elif status_norm in ["AVAILABLE", "UNOCCUPIED"]:
                    reply = f"**Room {res_obj.code}** is verified **AVAILABLE** between {start_t.strftime('%I:%M %p')} and {end_t.strftime('%I:%M %p')} on {target_date.strftime('%A, %b %d')}."
                    evidence.append({"room": res_obj.code, "status": "AVAILABLE"})
                elif status_norm == "UNSCHEDULED":
                    reply = f"**Room {res_obj.code}** is a **shared facility**. The timetable shows no scheduled departmental class for this slot, but external occupancy is **NOT VERIFIED**."
                    evidence.append({"room": res_obj.code, "status": "NOT_VERIFIED"})
                else:
                    reply = f"**Room {res_obj.code}** is currently **{status_raw}**: {eval_res['reason']}."

                return {
                    "conversation_id": conversation_id,
                    "reply": reply,
                    "tools_invoked": tools_invoked,
                    "evidence": evidence
                }

        # 2. Specific Faculty Query: best match by token overlap
        fac_found = None
        best_score = 0
        stop_words = {"prof", "assistant", "associate", "dr.", "mr.", "ms.", "teaching", "class", "today", "tomorrow", "free", "faculty", "slots", "time", "room", "with"}
        for f in Faculty.objects.filter(is_active=True):
            f_tokens = [tok.lower() for tok in re.findall(r'[a-zA-Z]{3,}', f.full_name) if tok.lower() not in stop_words]
            if not f_tokens:
                continue
            score = sum(1 for tok in f_tokens if tok in prompt_lower)
            # Require at least one distinctive multi-character token match
            if score > best_score and any(len(tok) >= 4 and tok in prompt_lower for tok in f_tokens):
                best_score = score
                fac_found = f

        if fac_found and best_score >= 1:
            eval_res = AvailabilityService.evaluate_faculty_status(fac_found, target_date, start_t, end_t)
            status_raw = eval_res["status"]
            status_norm = status_raw.upper()
            reason = eval_res["reason"]
            tools_invoked.append({
                "tool_name": "search_faculty_availability",
                "parameters": {"faculty": fac_found.full_name, "date": str(target_date), "start_time": str(start_t)}
            })

            if status_norm == "OCCUPIED" and eval_res.get("evidence"):
                ev = eval_res["evidence"]
                reply = f"**{fac_found.full_name}** ({fac_found.faculty_code or 'Faculty'}) is currently **OCCUPIED** between {start_t.strftime('%I:%M %p')} and {end_t.strftime('%I:%M %p')} on {target_date.strftime('%A, %b %d')}.\n\n• **Teaching:** {ev['subject']}\n• **Section:** {ev['section']}\n• **Classroom/Lab:** Room {ev['room']}\n• **Duration:** {ev['start_time']} – {ev['end_time']}"
                evidence.append(ev)
            else:
                reply = f"**{fac_found.full_name}** ({fac_found.faculty_code or 'Faculty'}) is currently **AVAILABLE** between {start_t.strftime('%I:%M %p')} and {end_t.strftime('%I:%M %p')} on {target_date.strftime('%A, %b %d')}.\n\n*(Status Reason: {reason})*"
                evidence.append({"faculty": fac_found.full_name, "status": "AVAILABLE"})

            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": tools_invoked,
                "evidence": evidence
            }

        # 3. General Faculty Availability Search
        if any(k in prompt_lower for k in ["faculty", "prof", "who is free", "free faculty", "available faculty", "free teacher"]):
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
                reply = f"Found **{len(free_facs)} verified available faculty members** between {start_t.strftime('%I:%M %p')} and {end_t.strftime('%I:%M %p')} on {target_date.strftime('%A, %b %d')}:\n{sample_str}"
                if len(free_facs) > 10:
                    reply += f"\n\n*(and {len(free_facs) - 10} more available faculty across departments)*"
            else:
                reply = f"All faculty members have scheduled classes between {start_t.strftime('%I:%M %p')} and {end_t.strftime('%I:%M %p')} on {target_date.strftime('%A, %b %d')}."

            evidence.append({"available_count": len(free_facs), "sample": free_facs[:10]})
            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": tools_invoked,
                "evidence": evidence
            }

        # 4. Classroom / Lab Availability Search
        is_lab = bool(re.search(r'\b(?:labs?|laborator(?:y|ies))\b', prompt_lower))
        is_classroom = bool(re.search(r'\b(?:classrooms?|rooms?)\b', prompt_lower))

        if is_lab or is_classroom:
            res_type = 'LABORATORY' if is_lab else 'CLASSROOM'
            type_label = "laboratories" if is_lab else "classrooms"
            type_label_single = "laboratory" if is_lab else "classroom"

            # Parse minimum capacity if requested e.g. "for 50 students"
            cap_match = re.search(r'\b(?:for\s+)?(\d{2,3})\s*(?:students?|seats?|capacity)?\b', prompt_lower)
            min_cap = int(cap_match.group(1)) if cap_match and int(cap_match.group(1)) <= 150 else 30

            tools_invoked.append({
                "tool_name": "search_classroom_availability",
                "parameters": {"date": str(target_date), "start_time": str(start_t), "end_time": str(end_t), "type": res_type, "min_capacity": min_cap}
            })

            recs = SchedulingService.recommend_classrooms(target_date, start_t, end_t, min_capacity=min_cap, resource_type=res_type)
            if recs:
                rooms_str = "\n".join([f"• **Room {r['code']}** ({r['capacity']} seats) — Verified Available" for r in recs[:8]])
                reply = f"Verified available {type_label} (min {min_cap} seats) for {start_t.strftime('%I:%M %p')}–{end_t.strftime('%I:%M %p')} on {target_date.strftime('%A, %b %d')}:\n\n{rooms_str}"
                if len(recs) > 8:
                    reply += f"\n\n*(and {len(recs) - 8} more available {type_label})*"
                evidence.extend(recs[:8])
            else:
                reply = f"No {type_label} with at least {min_cap} seats are verified available at {start_t.strftime('%I:%M %p')} on {target_date.strftime('%A, %b %d')}."

            return {
                "conversation_id": conversation_id,
                "reply": reply,
                "tools_invoked": tools_invoked,
                "evidence": evidence
            }

        # Fallback
        reply = "I can assist you with real-time faculty availability, classroom & laboratory schedules, schedule exceptions, and substitutions. Try asking:\n• *'Which AIML faculty are free at 11 AM today?'*\n• *'Find an available classroom for 50 students at 10:10 AM'*\n• *'Is Dr. Sudha Rani teaching any class at 2 PM?'*\n• *'Are any computer labs free on Friday morning?'*\n• *'Are there any cancellations or substitutions today?'*"
        return {
            "conversation_id": conversation_id,
            "reply": reply,
            "tools_invoked": tools_invoked,
            "evidence": evidence
        }
