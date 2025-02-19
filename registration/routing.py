from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/attendee_status/(?P<event_id>\d+)/$', consumers.AttendeeStatusConsumer.as_asgi()),
]
    
