from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, User
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_migrate, pre_delete

class Event(models.Model):
    name = models.CharField(max_length=255)
    date = models.DateField()
    attendees_count = models.IntegerField()

    def __str__(self):
        return self.name

class QRTemplate(models.Model):
    name = models.CharField(max_length = 255)  
    image = models.ImageField(upload_to ='templates/')  
    event = models.ForeignKey(Event, on_delete = models.CASCADE, default=1)

    def __str__(self):
        return f"{self.name} - {self.event.name}"
class AdminUserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, password=None):
        user = self.create_user(email, first_name, last_name, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class AdminUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = AdminUserManager()

    USERNAME_FIELD = 'email'  
    REQUIRED_FIELDS = ['first_name', 'last_name']  

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


def prevent_admin_deletion(sender, instance, **kwargs):
    permanent_admin_email = ["# Permanent Emails here..."]
    
    if instance.email == permanent_admin_email:
        raise Exception("The permanent admin user cannot be deleted.")
pre_delete.connect(prevent_admin_deletion, sender=AdminUser)

class AdminWhitelist(models.Model):
    email = models.EmailField(unique=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

class Attendee(models.Model):
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=20, default='N/A')
    email = models.EmailField(max_length=254, unique=True)
    department = models.CharField(max_length=100, default="Visitor") # To change to coop
    is_present = models.BooleanField(default=False)
    present_time = models.DateTimeField(null=True, blank=True)
    sub_department = models.CharField(max_length=100, blank=True, null=True, default="Visitor") # to change to coop..
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, default=1)  # ForeignKey para sa Event db

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
class MealClaim(models.Model):
    attendee = models.ForeignKey(Attendee, on_delete=models.CASCADE, related_name="meal_claims")
    breakfast_claimed = models.BooleanField(default=False)
    lunch_claimed = models.BooleanField(default=False)
    dinner_claimed = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.attendee.first_name} {self.attendee.last_name} - Meals Claimed"


@receiver(post_migrate)
def create_permanent_admin(sender, **kwargs):
    #hashmap (dict) para makapag store ng permanent admins, meaning they cannot be deleated via sql code commands.
    permanent_admins = [
        {
            #permanent email 1
        },
        {
            #permanent email 2
        },
        {
            #permanent email 3
        },
        {
            #permanent email 4
        }
    ]
    
    for admin in permanent_admins:
        if not AdminUser.objects.filter(email=admin['email']).exists():
            AdminUser.objects.create_superuser(
                email=admin['email'],
                first_name=admin['first_name'],
                last_name=admin['last_name'],
                password=admin['password']
            )
            print(f"Permanent admin user '{admin['email']}' created.")
        else:
            print(f"Permanent admin user '{admin['email']}' already exists.")
        