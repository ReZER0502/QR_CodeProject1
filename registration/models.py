from django.db import models
import qrcode
from io import BytesIO
from django.core.files import File
from django.urls import reverse  # Import reverse to create URLs
import re

class Attendee(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=100, default='General')
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)
    is_present = models.BooleanField(default=False)  # Field to mark attendance
    present_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        qr_data = f"http://192.168.172.1:8000/mark_attendance/?attendee_id={self.id}"  
        
        qrcode_img = qrcode.make(qr_data)
        canvas = BytesIO()
        qrcode_img.save(canvas, format='PNG')

        safe_email = re.sub(r'[^\w.-]', '_', self.email)
        self.qr_code.save(f'qr_code_{safe_email}.png', File(canvas), save=False)
        super().save(*args, **kwargs)
