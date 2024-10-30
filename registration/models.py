from django.db import models
import qrcode
from io import BytesIO

#import 2 input boxes for first name and last name instead of 1 only.
#email is ok for duplicates. 
#use other alternatives rather than IP Address for whitelisting etg: email address.
#Approximately 5-10 admin scanners are only the ones allowed to scan.
#integrate security measure when trying to log in to website to prevent public registering.
#Plan for domain
class Attendee(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=100)
    is_present = models.BooleanField(default=False)
    present_time = models.DateTimeField(null=True, blank=True)
    sub_department = models.CharField(max_length=100, blank = True, null = True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)

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

            self.qr_code_image_data = canvas.getvalue()  
        else:
            print("Error: Attendee ID is None, QR code will not be generated.")
