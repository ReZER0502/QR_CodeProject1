from django.shortcuts import render, redirect
from django.utils import timezone
import qrcode
from .models import Attendee
from django.shortcuts import get_object_or_404
from io import BytesIO
from datetime import timedelta
from django.core.files.base import ContentFile
from django.http import HttpResponse
from PIL import Image, ImageDraw, ImageFont
import os
from django.contrib import messages

def register(request):
    if request.method == 'POST':
        try:
            my_email = Attendee.objects.filter(email=request.POST['email']).first()
            my_name = Attendee.objects.filter(name=request.POST['name']).first()

            if my_email:
                messages.error(request, "This email is already registered.")
                return render(request, 'registration/register.html')

            if my_name:
                messages.error(request, "This name is already registered. Please use a different name.")
                return render(request, 'registration/register.html')

            attendee = Attendee.objects.create(
                name=request.POST['name'],
                email=request.POST['email'],
                department=request.POST['department'],
                sub_department=request.POST['sub_department'],
            )

            qr_data = f"http://10.0.0.52:8000/registration/mark_attendance/?attendee_id={attendee.id}"
            qrcode_img = qrcode.make(qr_data)
            canvas = BytesIO()
            qrcode_img.save(canvas, format='PNG')
            canvas.seek(0)
            qr_code_file = ContentFile(canvas.getvalue(), name=f'qr_code_{attendee.id}.png')
            attendee.qr_code.save(f'qr_code_{attendee.id}.png', qr_code_file)
            attendee.save() 
            messages.success(request, "Registration Successful!")  
            return redirect('success', attendee_id=attendee.id)

        except Exception as e:
            messages.error(request, "An error occurred while registering. Please try again.")
            print(f"Error: {e}")  
            return render(request, 'registration/register.html') 

    return render(request, 'registration/register.html')

def success(request, attendee_id):
    attendee = get_object_or_404(Attendee, id=attendee_id)
    return render(request, 'registration/success.html', {'attendee': attendee})

def mark_attendance(request):
    allowed_ips = ['10.0.0.10', '192.168.1.101']
    ip = request.META.get('REMOTE_ADDR')
    if ip not in allowed_ips:
        return render(request, 'res.html', {
            'success': False,
            'message': 'WALA KANG JOWA!! DI KA NYA CRUSH. ANG MASAKPLAP PA AY MAY IBA NA YUN.'
        })

    attendee_id = request.GET.get('attendee_id')
    if attendee_id:
        try:
            attendee = Attendee.objects.get(id=attendee_id)
            print(f'Before marking attendee: {attendee.name}, is_present: {attendee.is_present}')

            if attendee.is_present:
                print(f"Attendee {attendee.name} already marked present.")
                return render(request, 'res.html', {
                    'success': False,
                    'message': 'Attendance marked successfully!'
                })
                
            else:
                attendee.is_present = True
                attendee.present_time = timezone.now() + timedelta(hours=8)  
                attendee.save(update_fields=['is_present', 'present_time']) 
                print(f"Marked {attendee.name} as present.")  
                
            print(f"After Marking: {attendee.name}, is_present: {attendee.is_present}")
                 
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

#'C:\Windows\Fonts\ArialNova-Bold.ttf' We can change this

def download_attendee_info(request, attendee_id):
    try:
        attendee = Attendee.objects.get(id=attendee_id)
         #Eto yung sa background change natin right after implementing the design 
        background_path = os.path.join('C:/xampp/htdocs/test/QR_CodeProject1/static/img/my_qr.jpg')
        background = Image.open(background_path)
        image_width = 600
        image_height = 800
        background = background.resize((image_width, image_height))
        
        overlay = Image.new('RGBA', (image_width, image_height), (255, 255, 255, 0))  
        draw = ImageDraw.Draw(overlay)

        font_path = os.path.join('C:\Windows\Fonts\ArialNova-Bold.ttf')
        font = ImageFont.truetype(font_path, 36)
        small_font = ImageFont.truetype(font_path, 24)

        name_text = f"Name: {attendee.name}"
        department_text = f"Department: {attendee.department}"
        sub_department_text = f"Sub-Department: {attendee.sub_department}"
        
        name_position = (50, 100)
        department_position = (50, 200)
        sub_department_position = (50, 250)
        
        draw.text(name_position, name_text, font=small_font, fill='black')
        draw.text(department_position, department_text, font=small_font, fill='black')
        draw.text(sub_department_position, sub_department_text, font=small_font, fill='black')
        line_position = (50, 300, image_width - 50, 300)
        draw.line(line_position, fill="gray", width=3)
        qr_code_position = (150, 350)  
        qr_code_image = Image.open(attendee.qr_code.path)
        qr_code_image = qr_code_image.resize((300, 300))  
        overlay.paste(qr_code_image, qr_code_position, qr_code_image.convert('RGBA'))
        final_image = Image.alpha_composite(background.convert('RGBA'), overlay)

        response = HttpResponse(content_type='image/png')
        final_image = final_image.convert('RGB')  
        final_image.save(response, 'PNG')
        response['Content-Disposition'] = f'attachment; filename="{attendee.name}_info.png"'

        return response

    except Attendee.DoesNotExist:
        return HttpResponse("Attendee not found", status=404)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)
