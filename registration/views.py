from django.shortcuts import render, redirect
from django.utils import timezone
import qrcode
from .models import Attendee
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from io import BytesIO
from datetime import timedelta
from django.core.files.base import ContentFile
from django.http import HttpResponse
from PIL import Image, ImageDraw, ImageFont
import os

def register(request):
    if request.method == 'POST':
        attendee = Attendee.objects.create(
            name=request.POST['name'],
            email=request.POST['email'],
            department=request.POST['department'],
            sub_department=request.POST['sub_department'],
        )
        attendee.save()
        qr_data = f"http://10.0.0.52:8000/registration/mark_attendance/?attendee_id={attendee.id}"
        qrcode_img = qrcode.make(qr_data)
        canvas = BytesIO()
        qrcode_img.save(canvas, format='PNG')
        canvas.seek(0)
        qr_code_file = ContentFile(canvas.getvalue(), name=f'qr_code_{attendee.id}.png')
        attendee.qr_code.save(f'qr_code_{attendee.id}.png', qr_code_file)  
        attendee.save() 
        return redirect('success', attendee_id=attendee.id)

    return render(request, 'registration/register.html')

def success(request, attendee_id):
    attendee = get_object_or_404(Attendee, id=attendee_id)
    return render(request, 'registration/success.html', {'attendee': attendee})

def mark_attendance(request):
    allowed_ips = ['10.0.0.10', '192.168.1.101']  # Example of whitelisted IPs
    ip = request.META.get('REMOTE_ADDR')
    if ip not in allowed_ips:
        return render(request, 'res.html', {
            'success': False,
            'message': 'WALA KANG JOWA!! DI KA NYA CRUSH. MASAKPLAY PA, MAY IBA NA YUN.'
        })

    attendee_id = request.GET.get('attendee_id')
    if attendee_id:
        try:
            attendee = Attendee.objects.get(id=attendee_id)
            if attendee.is_present:
                return render(request, 'res.html', {
                    'success': False,
                    'message': 'You already scanned this.'
                })

            attendee.is_present = True  
            utc_now = timezone.now()
            manila_cubao_time = utc_now + timedelta(hours=8)
            attendee.present_time = manila_cubao_time 
            attendee.save()
            return render(request, 'res.html', {
                'success': True,
                'message': 'Attendance marked successfully!',
                'attendee_name': attendee.name  
            })
        except Attendee.DoesNotExist:
            return render(request, 'res.html', {
                'success': False,
                'message': 'Attendee not found.'
            })

    return render(request, 'res.html', {
        'success': False,
        'message': 'Invalid request.'
    })

#'C:\Windows\Fonts\ArialNova-Bold.ttf'

def download_attendee_info(request, attendee_id):
    try:
        attendee = Attendee.objects.get(id=attendee_id)
        font_path = os.path.join('C:\Windows\Fonts\ArialNova-Bold.ttf', 'ArialNova-Bold.ttf')  
        font = ImageFont.truetype(font_path, 36)
        small_font = ImageFont.truetype(font_path, 24)

        image_width = 500
        image_height = 600
        image = Image.new('RGB', (image_width, image_height), color='white')
        draw = ImageDraw.Draw(image)
        name_text = f"Name: {attendee.name}"
        email_text = f"Email: {attendee.email}"
        name_position = (50, 50)
        email_position = (50, 150)
        qr_code_position = (50, 250)  #space before the QR code

        draw.text(name_position, name_text, font=font, fill='black')
        draw.text(email_position, email_text, font=small_font, fill='black')
        qr_code_image = Image.open(attendee.qr_code.path) 
        qr_code_image = qr_code_image.resize((300, 300))  # Resize qr here
        image.paste(qr_code_image, qr_code_position)
        response = HttpResponse(content_type='image/png')
        image.save(response, 'PNG')
        response['Content-Disposition'] = f'attachment; filename="attendee_info_{attendee.id}.png"'

        return response

    except Attendee.DoesNotExist:
        return HttpResponse("Attendee not found", status=404)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)