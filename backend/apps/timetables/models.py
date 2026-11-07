import uuid
from django.db import models
from apps.academics.models import AcademicTerm, AcademicSection, Subject
from apps.faculty.models import Faculty
from apps.resources.models import Resource

class TimetableVersion(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING_APPROVAL', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('ARCHIVED', 'Archived'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, related_name='versions')
    version_number = models.SmallIntegerField(default=1)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='DRAFT')
    is_active = models.BooleanField(default=False)
    change_summary = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ('term', 'version_number')
        ordering = ['-version_number']

    def __str__(self):
        return f"{self.term} - v{self.version_number} ({self.status})"

class TimetableEntry(models.Model):
    SESSION_TYPES = [
        ('THEORY', 'Theory'),
        ('TUTORIAL', 'Tutorial'),
        ('PRACTICAL', 'Practical'),
        ('COUNSELLING', 'Counselling'),
        ('LIBRARY', 'Library'),
        ('SELF_LEARNING', 'Self Learning'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timetable_version = models.ForeignKey(TimetableVersion, on_delete=models.CASCADE, related_name='entries')
    section = models.ForeignKey(AcademicSection, on_delete=models.CASCADE, related_name='timetable_entries')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='timetable_entries')
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True, related_name='timetable_entries')
    resource = models.ForeignKey('resources.Resource', on_delete=models.SET_NULL, null=True, blank=True, related_name='timetable_entries')
    day_of_week = models.SmallIntegerField() # 0 = Monday ... 5 = Saturday
    start_time = models.TimeField()
    end_time = models.TimeField()
    session_type = models.CharField(max_length=30, choices=SESSION_TYPES, default='THEORY')
    source_sheet = models.CharField(max_length=50, blank=True, default='')
    source_cell = models.CharField(max_length=20, blank=True, default='')
    original_text = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['day_of_week', 'start_time']
        indexes = [
            models.Index(fields=['day_of_week', 'start_time', 'end_time']),
            models.Index(fields=['faculty', 'day_of_week']),
            models.Index(fields=['resource', 'day_of_week']),
        ]

    def __str__(self):
        return f"{self.section.full_name} | Day {self.day_of_week} {self.start_time}-{self.end_time} | {self.subject.name}"

class ScheduleException(models.Model):
    EXCEPTION_TYPES = [
        ('CANCEL', 'Cancel'),
        ('RESCHEDULE', 'Reschedule'),
        ('SUBSTITUTE', 'Substitute'),
        ('RESOURCE_CHANGE', 'Resource Change'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timetable_entry = models.ForeignKey(TimetableEntry, on_delete=models.CASCADE, related_name='exceptions')
    exception_date = models.DateField()
    exception_type = models.CharField(max_length=30, choices=EXCEPTION_TYPES)
    replacement_faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True, related_name='replacement_exceptions')
    replacement_resource = models.ForeignKey('resources.Resource', on_delete=models.SET_NULL, null=True, blank=True, related_name='replacement_exceptions')
    new_start_time = models.TimeField(null=True, blank=True)
    new_end_time = models.TimeField(null=True, blank=True)
    reason = models.CharField(max_length=255)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='APPROVED')
    approved_by = models.CharField(max_length=100, default='Academic Admin')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-exception_date', '-created_at']

    def __str__(self):
        return f"Exception on {self.exception_date} ({self.exception_type}) for entry {self.timetable_entry_id}"

class ClassSwap(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    swap_date = models.DateField()
    faculty_1 = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='swaps_as_first')
    entry_1 = models.ForeignKey(TimetableEntry, on_delete=models.CASCADE, related_name='swaps_as_first')
    faculty_2 = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='swaps_as_second')
    entry_2 = models.ForeignKey(TimetableEntry, on_delete=models.CASCADE, related_name='swaps_as_second')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='APPROVED')
    reason = models.CharField(max_length=255)
    approved_by = models.CharField(max_length=100, default='Academic Admin')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-swap_date', '-created_at']

    def __str__(self):
        return f"Swap on {self.swap_date}: {self.faculty_1.full_name} <-> {self.faculty_2.full_name}"

class TimetableClash(models.Model):
    CLASH_TYPES = [
        ('FACULTY_CLASH', 'Faculty Allocation Clash'),
        ('CLASSROOM_CLASH', 'Classroom Allocation Clash'),
        ('LAB_CLASH', 'Laboratory Allocation Clash'),
        ('SECTION_CLASH', 'Class/Section Timetable Clash'),
    ]
    STATUS_CHOICES = [
        ('UNRESOLVED', 'Unresolved'),
        ('RESOLVED', 'Resolved'),
        ('IGNORED', 'Ignored'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clash_type = models.CharField(max_length=30, choices=CLASH_TYPES)
    day_of_week = models.SmallIntegerField() # 0 = Monday ... 5 = Saturday
    date = models.DateField(null=True, blank=True)
    entry_1 = models.ForeignKey(TimetableEntry, on_delete=models.CASCADE, related_name='clashes_as_first')
    entry_2 = models.ForeignKey(TimetableEntry, on_delete=models.CASCADE, related_name='clashes_as_second')
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, null=True, blank=True, related_name='clashes')
    resource = models.ForeignKey('resources.Resource', on_delete=models.CASCADE, null=True, blank=True, related_name='clashes')
    section = models.ForeignKey(AcademicSection, on_delete=models.CASCADE, null=True, blank=True, related_name='clashes')
    overlap_start = models.TimeField()
    overlap_end = models.TimeField()
    overlap_duration_minutes = models.IntegerField(default=0)
    explanation = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UNRESOLVED')
    resolution_notes = models.TextField(blank=True, default='')
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['day_of_week', 'overlap_start']

    def __str__(self):
        return f"{self.clash_type} on Day {self.day_of_week} ({self.overlap_start}-{self.overlap_end})"

class ImportBatch(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PARSED', 'Parsed'),
        ('VALIDATING', 'Validating'),
        ('CONFLICTS_FOUND', 'Conflicts Found'),
        ('APPROVED', 'Approved'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_filename = models.CharField(max_length=255)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')
    total_records = models.IntegerField(default=0)
    valid_records = models.IntegerField(default=0)
    critical_errors = models.IntegerField(default=0)
    warnings = models.IntegerField(default=0)
    error_summary = models.JSONField(null=True, blank=True)
    imported_version = models.ForeignKey(TimetableVersion, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
