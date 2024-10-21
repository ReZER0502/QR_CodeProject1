from django.db import models
from django.core.files.base import ContentFile
import qrcode
from io import BytesIO
import re

class Attendee(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=100, default='General')
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)
    is_present = models.BooleanField(default=False)
    present_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        print(f"Attendee ID after saving: {self.id}")
        
        if self.id is not None:
            qr_data = f"http://10.0.0.52:8000/registration/mark_attendance/?attendee_id={self.id}"
            print(f"Generated QR Code URL: {qr_data}")
            
            qrcode_img = qrcode.make(qr_data)
            canvas = BytesIO()
            qrcode_img.save(canvas, format='PNG')

            safe_email = re.sub(r'[^\w.-]', '_', self.email)
            self.qr_code.save(f'qr_code_{safe_email}.png', ContentFile(canvas.getvalue()), save=False)
            super().save(update_fields=['qr_code'])
        else:
            print("Error: Attendee ID is None, QR code will not be generated.")