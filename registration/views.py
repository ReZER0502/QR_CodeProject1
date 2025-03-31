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
import pandas as pd
from django.db import transaction
import hmac
import hashlib
import time
from django.utils.http import urlencode
from datetime import datetime, time as dt_time

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
    
logger = logging.getLogger(__name__)

def bulk_register(request):
    if request.method == "POST" and request.FILES.get("attendee_file"):
        file = request.FILES["attendee_file"]
        event_id = int(request.POST.get("event_id", 0)) 

        try:
            # Detect file type and read into DataFrame
            if file.name.endswith(".csv"):
                df = pd.read_csv(file, encoding="utf-8", header=0)
            elif file.name.endswith(".xlsx"):
                df = pd.read_excel(file, engine="openpyxl")
            else:
                messages.error(request, "Invalid file format. Please upload a CSV or Excel file.")
                return redirect("register")

            # Strip spaces from column names and standardize
            df.columns = df.columns.str.strip()

            # Find columns dynamically (case-insensitive)
            name_column = next((col for col in df.columns if "delegate name" in col.lower()), None)
            email_column = next((col for col in df.columns if "email" in col.lower()), None)

            if not name_column or not email_column:
                messages.error(request, "Missing required columns: Delegate Name or Email")
                return redirect("register")

            # Trim spaces and convert to string
            df[email_column] = df[email_column].astype(str).str.strip()
            df[name_column] = df[name_column].astype(str).str.strip()

            # Get existing emails to prevent duplicates
            existing_emails = set(Attendee.objects.values_list("email", flat=True))

            event = Event.objects.filter(id=event_id).first()
            if not event:
                messages.error(request, "Invalid event selection.")
                return redirect("register")

            # Remove duplicate emails in the uploaded file
            df = df.drop_duplicates(subset=["Email"], keep="first")

            attendees_to_create = []
            for _, row in df.iterrows():
                if row["Email"] in existing_emails:
                    continue  # Skip duplicates

                # Ensure first name is within max length
                first_name = str(row[name_column]).strip()[:70]  # Adjust based on your model

                attendees_to_create.append(
                    Attendee(
                        first_name=first_name,
                        last_name="N/A",
                        email=row["Email"],
                        department="Visitor",
                        sub_department="Visitor",
                        event=event,
                    )
                )

            # Bulk insert attendees
            with transaction.atomic():
                new_attendees = Attendee.objects.bulk_create(attendees_to_create, batch_size=500)

            # Send QR codes (Consider making this async for large files)
            for attendee in new_attendees:
                generate_qr_and_send_email(attendee)

            messages.success(request, f"Successfully registered {len(new_attendees)} attendees.")
            return redirect("register")

        except Exception as e:
            messages.error(request, f"Error processing file: {e}")
            logger.error(f"File upload error: {e}", exc_info=True)
            return redirect("register")

    messages.error(request, "Invalid form submission.")
    return redirect("register")

SECRET_KEY = settings.SECRET_KEY

def generate_secure_qr_url(attendee):
    """Generate a hashed URL with an expiration timestamp."""
    expiry_time = int(time.time()) + (60 * 60 * 2) 

    data = f"{attendee.id}:{expiry_time}"
    hash_digest = hmac.new(settings.SECRET_KEY.encode(), data.encode(), hashlib.sha256).hexdigest()[:16]

    params = urlencode({"auth": hash_digest, "id": attendee.id, "exp": expiry_time})
    return f"{settings.BASE_URL}/registration/mark_attendance/?{params}"

def generate_qr_and_send_email(attendee):
    try:
        event_end_time = datetime.combine(attendee.event.date, dt_time(20, 0))
        event_end_timestamp = int(event_end_time.timestamp()) # Expire at event end
    
        data = f"{attendee.id}:{event_end_timestamp}"
        hash_digest = hmac.new(settings.SECRET_KEY.encode(), data.encode(), hashlib.sha256).hexdigest()[:16]

        qr_data = f"{settings.BASE_URL}/registration/mark_attendance/?id={attendee.id}&auth={hash_digest}&exp={event_end_timestamp}"
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill="black", back_color="white").convert("RGBA")

        # Resize QR code
        qr_img = qr_img.resize((500, 500), Image.LANCZOS)

        # Load background template
        try:
            qr_template = QRTemplate.objects.get(event=attendee.event)
            background_path = qr_template.image.path
        except QRTemplate.DoesNotExist:
            background_path = os.path.join(settings.BASE_DIR, 'staticfiles', 'img', 'default_template.jpg')

        background = Image.open(background_path).convert("RGBA")
        background = background.resize((700, 700), Image.LANCZOS)  
        position = ((background.width - qr_img.width) // 2, (background.height - qr_img.height) // 2)
        background.paste(qr_img, position, qr_img)

        canvas = BytesIO()
        background.save(canvas, format='PNG', optimize=True)
        canvas.seek(0)
        qr_code_file = ContentFile(canvas.getvalue(), name=f'qr_code_{attendee.id}.png')
        attendee.qr_code.save(f'qr_code_{attendee.id}.png', qr_code_file, save=True)

        # Send Email with QR Code
        subject = 'Your QR Code is Ready!'
        html_message = render_to_string('registration/email_template.html', {'attendee': attendee, 'qr_data': qr_data})
        plain_message = strip_tags(html_message)
        email = EmailMessage(subject, plain_message, to=[attendee.email])
        email.attach(f'qr_code_{attendee.first_name}_{attendee.last_name}.png', canvas.getvalue(), 'image/png')
        email.send()

    except Exception as e:
        print(f"Error in QR generation: {e}")

#RETEST F(X) FOR QR SNIP / F(X) TIME INTERVALS / TRY HASHMAP 03/21/2025
def register(request):
    today = timezone.now().date()
    events = Event.objects.filter(date__gte=today)
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
    attendee_id = request.GET.get("id")
    auth_hash = request.GET.get("auth")
    expiry_time = request.GET.get("exp")

    if not (attendee_id and auth_hash and expiry_time):
        return HttpResponseForbidden("Invalid QR code")

    if int(expiry_time) < int(time.time()):
        return HttpResponseForbidden("QR code expired")

    data = f"{attendee_id}:{expiry_time}"
    expected_hash = hmac.new(SECRET_KEY.encode(), data.encode(), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(expected_hash, auth_hash):
        return HttpResponseForbidden("Invalid QR code")

    try:
        attendee = Attendee.objects.get(id=attendee_id)
    except Attendee.DoesNotExist:
        return render(request, 'res.html', {'success': False, 'message': 'Attendee not found.'})

    attendee_name = f"{attendee.first_name} {attendee.last_name}"
    current_time = localtime(now()).time() 
    meal_claim, _ = MealClaim.objects.get_or_create(attendee=attendee)

    meal_times = {
        "breakfast": (dt_time(5, 0), dt_time(7, 0)), 
        "lunch": (dt_time(11, 0), dt_time(13, 0)), 
        "dinner": (dt_time(17, 0), dt_time(18, 0)), 
    }


    if not attendee.is_present:
        attendee.is_present = True
        attendee.present_time = now() + timedelta(hours=8)
        attendee.save()
        return render(request, 'res.html', {'success': True, 'message': 'Attendance marked successfully!' 'Late Attendee', 'attendee_name': attendee_name})

    for meal, (start, end) in meal_times.items():
        if start <= current_time <= end:
            claimed_attr = f"{meal}_claimed" 
            if getattr(meal_claim, claimed_attr):  
                return render(request, 'res.html', {'success': False, 'message': f'{meal.capitalize()} already claimed!', 'attendee_name': attendee_name})
            setattr(meal_claim, claimed_attr, True)  
            meal_claim.save()
            return render(request, 'res.html', {'success': True, 'message': f'{meal.capitalize()} claimed successfully!', 'attendee_name': attendee_name})

    return render(request, 'res.html', {'success': False, 'message': 'Invalid scan time or already attended.', 'attendee_name': attendee_name})

def download_qr(request, attendee_id):
    attendee = get_object_or_404(Attendee, id=attendee_id)
    if not attendee.qr_code:
        return HttpResponse("QR code not found.", status=404)
    qr_code_file_path = attendee.qr_code.path
    with open(qr_code_file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type="image/png")
        response['Content-Disposition'] = f'attachment; filename="qr_code_{attendee.first_name}_{attendee.last_name}.png"'
        return response