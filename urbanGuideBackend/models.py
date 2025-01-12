import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils.timezone import now


class Item(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="userprofile")
    name = models.CharField(max_length=100)
    userPicture = models.ImageField(upload_to="userPictures", null=True, blank=True)
    test_field = models.CharField(max_length=50, default="test")  # Temporary field

    def __str__(self):
        return f"{self.user.username}'s Profile"

class UserSchedule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100, default="My Trip")
    schedule_id = models.UUIDField(default=uuid.uuid4, unique=True)  # Unique schedule ID
    schedule = models.JSONField()  # Stores the enriched schedule JSON
    visited_venues = models.JSONField(default=list)  # List of visited venues
    is_active = models.BooleanField(default=False)  # Marks if the schedule is active
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)