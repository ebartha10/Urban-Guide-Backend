from django.contrib import admin
from .models import *

admin.site.register(Item)
admin.site.register(UserProfile)
admin.site.register(UserSchedule)