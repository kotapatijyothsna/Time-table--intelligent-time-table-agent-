import uuid
from django.db import models

class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

class AcademicTerm(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='terms')
    academic_year = models.CharField(max_length=50) # e.g. "2026-27"
    semester = models.SmallIntegerField() # 1 or 2
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.department.code} {self.academic_year} Sem {self.semester}"

class AcademicSection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='sections')
    year_level = models.SmallIntegerField() # 2, 3, 4
    section_code = models.CharField(max_length=10) # 'A', 'B'
    full_name = models.CharField(max_length=50, unique=True) # e.g. 'II AIML-A'

    class Meta:
        ordering = ['year_level', 'section_code']

    def __str__(self):
        return self.full_name

class Subject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='subjects')
    code = models.CharField(max_length=30, blank=True, null=True)
    name = models.CharField(max_length=200)
    course_type = models.CharField(max_length=30, default='CORE')

    def __str__(self):
        return f"{self.code or self.name}"
