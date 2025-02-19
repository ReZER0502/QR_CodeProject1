from channels.generic.websocket import AsyncWebsocketConsumer
import json

class AttendeeCountConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.event_id = self.scope['url_route']['kwargs']['event_id']
        self.room_group_name = f'attendee_count_{self.event_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        attendees_count = data['attendees_count']

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'attendee_count_update',
                'attendees_count': attendees_count
            }
        )
    async def attendee_count_update(self, event):
        attendees_count = event['attendees_count']
        await self.send(text_data=json.dumps({
            'attendees_count': attendees_count
        }))

class AttendeeStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("attendee_updates", self.channel_name)
        await self.accept()
        print("WebSocket connection established!")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("attendee_updates", self.channel_name)
        print("WebSocket disconnected!")

    async def send_attendee_update(self, event):
        await self.send(text_data=json.dumps({
            "events": event["events"]
        }))
