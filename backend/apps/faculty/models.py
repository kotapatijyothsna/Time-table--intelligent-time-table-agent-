import uuid
from django.db import models
from apps.academics.models import Department

class Faculty(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='faculty_members')
    faculty_code = models.CharField(max_length=50, blank=True, null=True, unique=True)
    full_name = models.CharField(max_length=150, db_index=True)
    designation = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True, unique=True)
    is_active = models.BooleanField(default=True)
    is_outsourced = models.BooleanField(default=False)
    faculty_type = models.CharField(max_length=50, default='INTERNAL') # INTERNAL, OUTSOURCED, VISITING

    class Meta:
        verbose_name_plural = "Faculty"
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.designation or 'Faculty'})"
