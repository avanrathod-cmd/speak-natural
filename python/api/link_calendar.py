import os
from dotenv import load_dotenv
from pathlib import Path
import sys

current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))
from utils.attendee_utils import link_google_calendar

load_dotenv()

refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
client_id = os.getenv("GOOGLE_CLIENT_ID")
client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
user_email = os.getenv("GOOGLE_USER_EMAIL", "")

calendar_data = link_google_calendar(refresh_token, client_id, client_secret, user_email)
print(calendar_data)
calendar_id = calendar_data['id']
print(f"Linked calendar with ID: {calendar_id}")
print("Use this calendar_id in the 'Schedule Attendee' button")