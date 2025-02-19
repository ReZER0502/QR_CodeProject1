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
from django.utils.timezone import now
from .models import QRTemplate

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
        'is_present': attendee.is_present  # True/False value
    } for attendee in attendees]

    return JsonResponse({'attendees': data})

@login_required
def update_attendee_count(request):
    event_id = request.GET.get('event_id')
    if not event_id:
        return JsonResponse({'error': 'Missing event ID'}, status=400)

    try:
        event = Event.objects.get(id=event_id)
        attendees_count = event.attendee_set.count()  # Count attendees

        print(f"Event ID: {event_id}, Attendees Count: {attendees_count}")  # Debugging
        return JsonResponse({'attendees_count': attendees_count})

    except Event.DoesNotExist:
        print(f"Event ID {event_id} not found")  # Debugging
        return JsonResponse({'error': 'Invalid event ID'}, status=400)

def admin_login(request):
    permanent_admin_emails = ["gcagbayani@natcco.coop", "gjhalos@natcco.coop"]  # Hardcoded permanent admins
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Check if the email belongs to a permanent admin
        if email in permanent_admin_emails:
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('admin_dashboard')  # Redirect to the admin dashboard
            else:
                return render(request, 'registration/login.html', {'error': 'Invalid credentials.'})

        # For non-permanent admins, deny access to the dashboard
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

PERMANENT_ADMIN_EMAILS = ["gcagbayani@natcco.coop", "gjhalos@natcco.coop"]
@login_required
def admin_dashboard(request):
    if request.user.email not in PERMANENT_ADMIN_EMAILS:
        return HttpResponseForbidden('You do not have permission to access this page.')

    form = AdminWhitelistForm()
    event_form = EventForm()
    template_form = QRTemplateForm()  # Initialize the template form

    if request.method == 'POST':
        # Handle adding new admins
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

        # Handle adding new events
        elif 'add_event' in request.POST:
            event_form = EventForm(request.POST)
            if event_form.is_valid():
                event_form.save()
                return redirect('admin_dashboard')

        # Handle adding new QR templates (Image Upload)
        elif 'add_template' in request.POST:
            template_form = QRTemplateForm(request.POST, request.FILES)
            if template_form.is_valid():
                template_form.save()  # Save the new template
                return redirect('admin_dashboard')  # Redirect to the same page to show the newly added template

    # Fetch required data
    whitelisted_emails = AdminWhitelist.objects.all()
    attendees = Attendee.objects.all()
    events = Event.objects.filter(date__gte=now()).order_by('date')[:3]
    latest_events = Event.objects.filter(date__gte=now()).order_by('date')[:3]  # Only upcoming 3 events
    qr_templates = QRTemplate.objects.all()  # Fetch all QR templates for displaying

    return render(request, 'registration/admin_dashboard.html', {
        'form': form,
        'event_form': event_form,
        'template_form': template_form,  # Add the template form to the context
        'whitelisted_emails': whitelisted_emails,
        'attendees': attendees,
        'events': events,  
        'latest_events': latest_events,  # Send only 3 upcoming events
        'qr_templates': qr_templates,  # Send the list of templates to the template
    })

def templates_view(request):
    qr_templates = QRTemplate.objects.all()  # Get all QR templates
    return render(request, 'admin_dashboard.html', {
        'qr_templates': qr_templates
    })

@login_required
def download_attendees_csv(request):
    # Restrict to permanent admins or users with the necessary permissions
    if request.user.email not in PERMANENT_ADMIN_EMAILS:
        return HttpResponseForbidden("You do not have permission to perform this action.")

    # Create the HttpResponse object with the appropriate CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="attendees.csv"'

    writer = csv.writer(response)
    # Write the header row, including 'Present Time'
    writer.writerow(['First Name', 'Last Name', 'Email', 'Present Time', 'Status'])

    # Query all attendees and write their data
    attendees = Attendee.objects.all()
    for attendee in attendees:
        # Format the 'present_time' before writing it to the CSV
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
        # qr logic gen.
        qr_data = f"{settings.BASE_URL}/registration/mark_attendance/?attendee_id={attendee.id}"
        qrcode_img = qrcode.make(qr_data)
        qrcode_img = qrcode_img.convert("RGBA")

        # Fetch muna as first...
        try:
            qr_template = QRTemplate.objects.get(event=attendee.event)
            background_path = qr_template.image.path  # then gamit sya nung updated template based sa event
        except QRTemplate.DoesNotExist:
            background_path = os.path.join(settings.BASE_DIR, 'staticfiles', 'img', 'default_template.jpg') #fallback dito

        background = Image.open(background_path).convert("RGBA")
        qrcode_img = qrcode_img.resize((700, 700))
        background_width, background_height = background.size
        qr_width, qr_height = qrcode_img.size
        position = ((background_width - qr_width) // 2, (background_height - qr_height) // 2)

        background.paste(qrcode_img, position, qrcode_img)

        canvas = BytesIO()
        background.save(canvas, format='PNG')
        canvas.seek(0)
        qr_code_file = ContentFile(canvas.getvalue(), name=f'qr_code_{attendee.first_name}_{attendee.last_name}.png')
        attendee.qr_code.save(f'qr_code_{attendee.id}.png', qr_code_file, save=True)
        subject = 'Your Registration QR Code'
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
        print(f"Error in background task: {e}")


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
                return render(request, 'registration/register.html', {'form': form, 'events': events})
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
        permanent_admin_email = ["gcagbayani@natcco.coop", "gjhalos@natcco.coop"]
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
    # Process the attendance logic
    attendee_id = request.GET.get('attendee_id')
    if attendee_id:
        try:
            attendee = Attendee.objects.get(id=attendee_id)

            if attendee.is_present:
                return render(request, 'res.html', {
                    'success': False,
                    'message': 'Attendee already marked present!'
                })
            else:
                # Mark the attendee as present
                attendee.is_present = True
                attendee.present_time = timezone.now() + timedelta(hours=8)  # Adjust time zone as needed
                attendee.save()
            
            attendee_name = f"{attendee.first_name} {attendee.last_name}"
            return render(request, 'res.html', {
                'success': True,
                'message': 'Attendance marked successfully!',
                'attendee_name': attendee_name
            })

        except Attendee.DoesNotExist:
            return render(request, 'res.html', {
                'success': False,
                'message': 'Attendee not found.'
            })

    return render(request, 'res.html', {
        'success': False,
        'message': 'Invalid entry. Please scan the attendees QR Code.'
    })


#'C:\Windows\Fonts\ArialNova-Bold.ttf' Pwede natin tong palitan, depende sa client.

def download_qr(request, attendee_id):
    attendee = get_object_or_404(Attendee, id=attendee_id)
    if not attendee.qr_code:
        return HttpResponse("QR code not found.", status=404)
    qr_code_file_path = attendee.qr_code.path
    with open(qr_code_file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type="image/png")
        response['Content-Disposition'] = f'attachment; filename="qr_code_{attendee.first_name}_{attendee.last_name}.png"'
        return response