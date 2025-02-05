from django.contrib import admin
from .models import Attendee

admin.site.register(Attendee)

from django.contrib import admin
from .models import QRTemplate

@admin.register(QRTemplate)
class QRTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'image')
    search_fields = ('name',)
