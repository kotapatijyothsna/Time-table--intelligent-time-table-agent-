import uuid
from django.db import models
from apps.academics.models import Department

class Resource(models.Model):
    RESOURCE_TYPES = [
        ('CLASSROOM', 'Classroom'),
        ('LABORATORY', 'Laboratory'),
        ('SEMINAR_HALL', 'Seminar Hall'),
        ('LIBRARY_SLOT', 'Library Slot'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='resources')
    code = models.CharField(max_length=50, unique=True) # e.g. '619', '604', 'LAB-1'
    name = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=30, choices=RESOURCE_TYPES, default='CLASSROOM')
    capacity = models.IntegerField(default=60)
    is_shared = models.BooleanField(default=False)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

class ResourceBlock(models.Model):
    BLOCK_TYPES = [
        ('MAINTENANCE', 'Maintenance'),
        ('EXAMINATION', 'Examination'),
        ('EVENT', 'Event'),
        ('OFFLINE', 'Offline'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='blocks')
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    reason = models.CharField(max_length=255)
    block_type = models.CharField(max_length=30, choices=BLOCK_TYPES, default='MAINTENANCE')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Block on {self.resource.code}: {self.reason}"
