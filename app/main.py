import os 
from airtable import Airtable 
from dotenv import load_dotenv 
from flask import Flask, request, session
from pprint import pprint
import vonage
 
load_dotenv()
app = Flask(__name__)

grocery_lists = {}
app_name = "GroceryList"

AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")

VONAGE_API_KEY = os.environ.get('VONAGE_API_KEY')
VONAGE_API_SECRET = os.environ.get('VONAGE_API_SECRET')
VONAGE_NUMBER = os.environ.get('VONAGE_NUMBER')
AIRTABLE = Airtable(AIRTABLE_BASE_ID, 'Table 1', AIRTABLE_API_KEY)


client = vonage.Client(key=VONAGE_API_KEY, secret=VONAGE_API_SECRET)
sms = vonage.Sms(client)

@app.route('/webhooks/inbound-sms', methods=['GET', 'POST'])
def inbound_sms():
    data = dict(request.form) or dict(request.args)
    body = data["text"]
    number = data["msisdn"]

    if body.lower() == "list":
        send_list(number)
    elif body.lower() == "delete": 
        delete_list(number)    
    else:
        add(body, number)
    return ('', 204)


def add(item, number):
    record = get_record_for(number)
    if not record: 
        fields = get_fields_for(number, item)
        AIRTABLE.insert(fields) 
        return

    item_list = record['fields']['list']
    fields = get_fields_for(number, item_list+", "+item)
    AIRTABLE.replace(record['id'], fields)
        

def delete_list(number):
    record = get_record_for(number)
    if not record: 
        send_message(number, "No list exists for your number. Add items to create a new list!")
        return
 
    AIRTABLE.delete(record['id'])
    send_message(number, "List deleted.")

def send_list(number):
    record = get_record_for(number)
    if record and "list" in record['fields']: 
        item_list = record['fields']['list']
        send_message(number, item_list.replace(", ", "\n"))
        send_message(number, "To delete this list and start fresh, send DELETE")
    else:
        send_message(number, "No list exists for your number. Add items to create a new list!")

def send_message(number, text):
    responseData = sms.send_message(
        {
        "from": VONAGE_NUMBER,
        "to": number,
        "text": text,
        }
    )
    return responseData["messages"][0]["status"] == "0"

def get_fields_for(number, items):
    return {"phoneNumber": number, "list": items}


def get_record_for(number): 
    record = AIRTABLE.match("phoneNumber", number)
    if not len(record):
        return None
    return record     

if __name__ == "__main__":

    app.run()

