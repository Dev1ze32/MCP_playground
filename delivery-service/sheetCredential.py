import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
import json

load_dotenv()

def get_sheet_data():
    """Fetch data from Google Sheet"""
    creds_dict = json.loads(os.getenv('GOOGLE_CREDENTIALS_JSON'))
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    
    client = gspread.authorize(creds)
    sheet = client.open_by_key(os.getenv('SHEET_ID'))
    return sheet.sheet1.get_all_values()[1:]

def parse_to_config(values_list):
    """Parse sheet data to config dictionary"""
    config = {
        "store_name": "",
        "timezone": "",
        "cutoff_time": "",
        "working_days": [],
        "couriers": {},
    }
    
    for row in values_list:
        if len(row) < 2:
            continue
        
        key, value = row[0].strip(), row[1].strip()
        
        if key == "store_name":
            config["store_name"] = value
        elif key == "timezone":
            config["timezone"] = value
        elif key == "cutoff_time":
            config["cutoff_time"] = value
        elif key == "working_days":
            config["working_days"] = [day.strip() for day in value.split(',')]
        elif key == "couriers":
            config["couriers"] = json.loads(value)
    
    return config