from django.shortcuts import render, redirect
from django.utils import timezone
import qrcode
from django.shortcuts import get_object_or_404
from io import BytesIO
from datetime import timedelta
from django.core.files.base import ContentFile
from django.http import HttpResponse, HttpResponseForbidden
from PIL import Image
from django.contrib import messages
from .forms import RegistrationForm, AdminUserCreationForm, AdminWhitelistForm, QRTemplateForm
from django.contrib.auth import authenticate,login
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import Attendee, AdminWhitelist, QRTemplate
import logging
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.messages import get_messages
import os
import csv
from django.http import JsonResponse
from .models import Event
from .forms import EventForm
from django.utils.timezone import now, localtime
from .models import QRTemplate
from .models import MealClaim 

def reset_attendance(request):
    if request.method == 'POST':
        Attendee.objects.update(is_present=False, present_time=None)
        return JsonResponse({"success": True, "message": "Attendance has been reset for all attendees."})
    return JsonResponse({"success": False, "message": "Invalid request method."}, status=400)
 
#Live monitoring function para di na kailangan refresh
@login_required
def get_attendees_status(request):
    attendees = Attendee.objects.all()
    data = [{
        'first_name': attendee.first_name,
        'last_name': attendee.last_name,
        'is_present': attendee.is_present  # boolean
    } for attendee in attendees]

    return JsonResponse({'attendees': data})

@login_required
def update_attendee_count(request):
    event_id = request.GET.get('event_id')
    if not event_id:
        return JsonResponse({'error': 'Missing event ID'}, status=400)

    try:
        event = Event.objects.get(id=event_id)
        attendees_count = event.attendee_set.count() 

        print(f"Event ID: {event_id}, Attendees Count: {attendees_count}")  
        return JsonResponse({'attendees_count': attendees_count})

    except Event.DoesNotExist:
        print(f"Event ID {event_id} not found")  
        return JsonResponse({'error': 'Invalid event ID'}, status=400)

def admin_login(request):
    permanent_admin_emails = ["gcagbayani@natcco.coop", "gjhalos@natcco.coop", "spobusan@natcco.coop", "agpol@natcco.coop"]  # Hardcoded permanent admins
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        if email in permanent_admin_emails:
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('admin_dashboard')  
            else:
                return render(request, 'registration/login.html', {'error': 'Invalid credentials.'})

        return render(request, 'registration/login.html', {'error': 'Restricted Area!'})

    return render(request, 'registration/login.html')

logging.basicConfig(level=logging.DEBUG)
def register_admin(request):
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            if not AdminWhitelist.objects.filter(email=email).exists():
                messages.error(request, "This email is not authorized to register as an admin.")
                return redirect('register_admin')
            
            admin_user = form.save()
            if admin_user:
                logging.debug(f"Admin user created with email: {admin_user.email}")
            else:
                logging.error("Admin user creation failed.")
            
            messages.success(request, "Admin registered successfully.")
            return redirect('register_admin')
        else:
            logging.error(f"Form is invalid: {form.errors}")
    else:
        form = AdminUserCreationForm()

    storage = get_messages(request)
    messages_list = [msg.message for msg in storage]

    return render(request, 'registration/register_admin.html', {
        'form': form,
        'messages': messages_list
    })

PERMANENT_ADMIN_EMAILS = ["gcagbayani@natcco.coop", "gjhalos@natcco.coop", "spobusan@natcco.coop", "agpol@natcco.coop"]
@login_required
def admin_dashboard(request):
    if request.user.email not in PERMANENT_ADMIN_EMAILS:
        return HttpResponseForbidden('You do not have permission to access this page.')

    form = AdminWhitelistForm()
    event_form = EventForm()
    template_form = QRTemplateForm()  

    if request.method == 'POST':
        if 'add_admin' in request.POST:
            form = AdminWhitelistForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data.get('email')
                _, created = AdminWhitelist.objects.get_or_create(email=email)
                return JsonResponse({
                    'status': 'success' if created else 'error',
                    'message': f"{email} has been whitelisted." if created else "This email is already whitelisted."
                })
            return JsonResponse({'status': 'error', 'errors': list(form.errors.values())})

        elif 'add_event' in request.POST:
            event_form = EventForm(request.POST)
            if event_form.is_valid():
                event_form.save()
                return redirect('admin_dashboard')

        elif 'add_template' in request.POST:
            template_form = QRTemplateForm(request.POST, request.FILES)
            if template_form.is_valid():
                template_form.save()  
                return redirect('admin_dashboard')  

    whitelisted_emails = AdminWhitelist.objects.all()
    attendees = Attendee.objects.all()
    events = Event.objects.filter(date__gte=now()).order_by('date')[:3]
    latest_events = Event.objects.filter(date__gte=now()).order_by('date')[:3] 
    qr_templates = QRTemplate.objects.all()  

    return render(request, 'registration/admin_dashboard.html', {
        'form': form,
        'event_form': event_form,
        'template_form': template_form,  
        'whitelisted_emails': whitelisted_emails,
        'attendees': attendees,
        'events': events,  
        'latest_events': latest_events,  
        'qr_templates': qr_templates,  
    })

def templates_view(request):
    qr_templates = QRTemplate.objects.all()  
    return render(request, 'admin_dashboard.html', {
        'qr_templates': qr_templates
    })

@login_required
def download_attendees_csv(request):
    if request.user.email not in PERMANENT_ADMIN_EMAILS:
        return HttpResponseForbidden("You do not have permission to perform this action.")

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="attendees.csv"'
    writer = csv.writer(response)
    writer.writerow(['First Name', 'Last Name', 'Email', 'Present Time', 'Status'])

    attendees = Attendee.objects.all()
    for attendee in attendees:
        present_time = attendee.present_time.strftime('%Y-%m-%d %H:%M:%S') if attendee.present_time else 'N/A'
        writer.writerow([
            attendee.first_name,
            attendee.last_name,
            attendee.email,
            present_time,
            'Present' if attendee.is_present else 'Absent'
        ])

    return response

def edit_user_profile(request):
    if request.user.username == "permanentadmin":
        return HttpResponseForbidden("You cannot modify the permanent admin user.")

def generate_qr_and_send_email(attendee):
    try:
        # Generate QR code data, retest mo nga dito then verify kasi 1 1/2 minute time yung processing... 
        qr_data = f"{settings.BASE_URL}/registration/mark_attendance/?attendee_id={attendee.id}"
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill="black", back_color="white").convert("RGBA")

        # qr resizing
        qr_img = qr_img.resize((500, 500), Image.LANCZOS)

        # bg resizing
        try:
            qr_template = QRTemplate.objects.get(event=attendee.event)
            background_path = qr_template.image.path
        except QRTemplate.DoesNotExist:
            background_path = os.path.join(settings.BASE_DIR, 'staticfiles', 'img', 'default_template.jpg')

        background = Image.open(background_path).convert("RGBA")
        background = background.resize((700, 700), Image.LANCZOS)  # reduced sized dito... adjust if needed
        position = ((background.width - qr_img.width) // 2, (background.height - qr_img.height) // 2)
        background.paste(qr_img, position, qr_img)

        canvas = BytesIO()
        background.save(canvas, format='PNG', optimize=True)
        canvas.seek(0)
        qr_code_file = ContentFile(canvas.getvalue(), name=f'qr_code_{attendee.id}.png')
        attendee.qr_code.save(f'qr_code_{attendee.id}.png', qr_code_file, save=True)
        
        subject = 'Your QR Code is Ready!'
        html_message = render_to_string('registration/email_template.html', {'attendee': attendee, 'qr_data': qr_data})
        plain_message = strip_tags(html_message)
        email = EmailMessage(
            subject,
            plain_message,
            to=[attendee.email],
        )
        email.attach(f'qr_code_{attendee.first_name}_{attendee.last_name}.png', canvas.getvalue(), 'image/png')
        email.send()
        
    except Exception as e:
        print(f"Error in QR generation: {e}")

def register(request):
    events = Event.objects.all()
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                existing_attendee = Attendee.objects.filter(email=form.cleaned_data['email']).first()
                if existing_attendee:
                    messages.error(request, "This email is already registered.")
                    return render(request, 'registration/register.html', {'form': form, 'events': events})
                attendee = form.save()
                generate_qr_and_send_email(attendee)
                return redirect('success', attendee_id=attendee.id)
            except Exception as e:
                messages.error(request, "An error occurred while registering. Please try again.")
                print(f"Error: {e}")
    else:
        form = RegistrationForm()
    return render(request, 'registration/register.html', {'form': form, 'events': events})

def success(request, attendee_id):
    attendee = get_object_or_404(Attendee, id=attendee_id)
    return render(request, 'registration/success.html', {'attendee': attendee})

def mark_attendance(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)

    if request.user.is_authenticated:
        permanent_admin_email = ["gcagbayani@natcco.coop", "gjhalos@natcco.coop", "agpol@natcco.coop", "spobusan@natcco.coop"]
        if request.user.email in permanent_admin_email:
            return handle_attendance_logic(request)
        if AdminWhitelist.objects.filter(email=request.user.email).exists():
            return handle_attendance_logic(request)
        messages.error(request, "You are not authorized to mark attendance.")
        return render(request, 'registration/mark_attendance.html', {
            'error': 'You are not authorized to mark attendance.'
        })

    return render(request, 'registration/mark_attendance.html', {
        'error': 'Please log in to mark attendance.'
    })

def handle_attendance_logic(request):
    attendee_id = request.GET.get('attendee_id')
    if attendee_id:
        try:
            attendee = Attendee.objects.get(id=attendee_id)
            attendee_name = f"{attendee.first_name} {attendee.last_name}"
            current_time = localtime(timezone.now()).time() 
            meal_claim, _ = MealClaim.objects.get_or_create(attendee=attendee)

            breakfast_start = timezone.datetime.strptime("06:00", "%H:%M").time()
            breakfast_end = timezone.datetime.strptime("07:00", "%H:%M").time()
            lunch_start = timezone.datetime.strptime("11:00", "%H:%M").time()
            lunch_end = timezone.datetime.strptime("13:00", "%H:%M").time()
            dinner_start = timezone.datetime.strptime("17:00", "%H:%M").time()
            dinner_end = timezone.datetime.strptime("18:00", "%H:%M").time()

            if breakfast_start <= current_time <= breakfast_end:
                if meal_claim.breakfast_claimed:
                    return render(request, 'res.html', {'success': False, 'message': 'Breakfast already claimed!', 'attendee_name': attendee_name})
                meal_claim.breakfast_claimed = True
                meal_claim.save()
                return render(request, 'res.html', {'success': True, 'message': 'Breakfast claimed successfully!', 'attendee_name': attendee_name})

            elif lunch_start <= current_time <= lunch_end:
                if meal_claim.lunch_claimed:
                    return render(request, 'res.html', {'success': False, 'message': 'Lunch already claimed!', 'attendee_name': attendee_name})
                meal_claim.lunch_claimed = True
                meal_claim.save()
                return render(request, 'res.html', {'success': True, 'message': 'Lunch claimed successfully!', 'attendee_name': attendee_name})

            elif dinner_start <= current_time <= dinner_end:
                if meal_claim.dinner_claimed:
                    return render(request, 'res.html', {'success': False, 'message': 'Dinner already claimed!', 'attendee_name': attendee_name})
                meal_claim.dinner_claimed = True
                meal_claim.save()
                return render(request, 'res.html', {'success': True, 'message': 'Dinner claimed successfully!', 'attendee_name': attendee_name})

            # pag hindi meal time, mark attendance then advice warning sa admin scanner sya
            elif not attendee.is_present:
                attendee.is_present = True
                attendee.present_time = timezone.now() + timedelta(hours=8) 
                attendee.save()
                return render(request, 'res.html', {'success': True, 'message': 'Attendance marked successfully!, Late Attendee', 'attendee_name': attendee_name})

            else:
                return render(request, 'res.html', {'success': False, 'message': 'Invalid scan time or already attended.'})
        
        except Attendee.DoesNotExist:
            return render(request, 'res.html', {'success': False, 'message': 'Attendee not found.'})

    return render(request, 'res.html', {'success': False, 'message': 'Invalid entry. Please scan the attendee\'s QR Code.'})
    #'C:\Windows\Fonts\ArialNova-Bold.ttf' Pwede natin tong palitan, depende sa gusto.

def download_qr(request, attendee_id):
    attendee = get_object_or_404(Attendee, id=attendee_id)
    if not attendee.qr_code:
        return HttpResponse("QR code not found.", status=404)
    qr_code_file_path = attendee.qr_code.path
    with open(qr_code_file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type="image/png")
        response['Content-Disposition'] = f'attachment; filename="qr_code_{attendee.first_name}_{attendee.last_name}.png"'
        return response