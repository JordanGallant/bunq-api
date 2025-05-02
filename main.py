from fastapi import FastAPI
from lib.bunq_lib import BunqClient
from dotenv import load_dotenv
import os
load_dotenv()
USER_API_KEY = os.getenv("API_KEY")

bunq_client = BunqClient(USER_API_KEY, service_name='PeterScript')


# Run these 1x to initialize your application 
bunq_client.create_installation()
bunq_client.create_device_server()


bunq_client.create_session()

app = FastAPI()


@app.get("/monetary_account") #gets our monetary account
def get_monetary_account():
    response = bunq_client.request(endpoint='monetary-account',method='GET',data={})
    return response

@app.get("/get_cards")
def get_cards():
    response = bunq_client.request(endpoint='card',method='GET',data={})
    return response


@app.get("/request")
def request():
    endpoint = f"monetary-account/"
    response = bunq_client.request(endpoint=endpoint, method='GET', data=None)
    return response

@app.get("/payment") ## makes a payent from us
def payment():
    payment = bunq_client.create_payment(
        amount='0.10', 
        recipient_iban='NL14RABO0169202917',
        currency='EUR',
        from_monetary_account_id='1989601', 
        description='test'
    )
    return payment

@app.get("/transactions") #get all transactions for monetary account (recieves and sends)
def get_transactions():
    monetary_account_id = '2106783'
    endpoint = f"monetary-account/{monetary_account_id}/payment?count=200" #limit is 200
    response = bunq_client.request(endpoint=endpoint, method='GET', data=None)
    return response

#USER ID:1879691
#MONETARY ACCOUNT ID: 2106783

