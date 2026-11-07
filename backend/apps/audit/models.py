import uuid
from django.db import models

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=100, blank=True, null=True)
    action = models.CharField(max_length=50) # CREATE, UPDATE, DELETE, APPROVE, IMPORT
    entity_name = models.CharField(max_length=100) # TimetableVersion, ScheduleException, ResourceBlock
    entity_id = models.CharField(max_length=100)
    changes = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.created_at.strftime('%Y-%m-%d %H:%M:%S')} | {self.action} on {self.entity_name} ({self.entity_id})"
