from fastapi import FastAPI, HTTPException, Depends
from lib.bunq_lib import BunqClient
from dotenv import load_dotenv
import os
from typing import Dict, Any, Optional
from functools import lru_cache

load_dotenv()
USER_API_KEY = os.getenv("API_KEY")

app = FastAPI()

@lru_cache() #ensuring bunqclient is set up -> authorization
def get_bunq_client():
    client = BunqClient(USER_API_KEY, service_name='PeterScript')
    client.create_session()
    return client

async def get_primary_monetary_account_id() -> str: # function to internlly get monetary id
    client = get_bunq_client()
    response = client.request(endpoint='monetary-account', method='GET', data={})
    
    try:
        accounts = response.get('Response', [])
        if not accounts:
            raise HTTPException(status_code=404, detail="No monetary accounts found")
        
        primary_account = accounts[0].get('MonetaryAccountBank', {})
        account_id = primary_account.get('id')
        
        if not account_id:
            raise HTTPException(status_code=404, detail="Could not determine primary account ID")
            
        return str(account_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get monetary account: {str(e)}")

@app.get("/monetary_account")  #gets monetary account id
def get_monetary_account():
    client = get_bunq_client()
    response = client.request(endpoint='monetary-account', method='GET', data={})
    return response

@app.get("/get_cards") #gets cards
def get_cards():
    client = get_bunq_client()
    response = client.request(endpoint='card', method='GET', data={})
    return response

@app.get("/payment") #make a payment from us to a hardcoded iban
async def payment(monetary_account_id: str = Depends(get_primary_monetary_account_id)):
    client = get_bunq_client()
    payment = client.create_payment(
        amount='0.10', 
        recipient_iban='NL14RABO0169202917',
        currency='EUR',
        from_monetary_account_id=monetary_account_id,
        description='test'
    )
    return payment

@app.get("/transactions") #gets all transactions
async def get_transactions(monetary_account_id: str = Depends(get_primary_monetary_account_id)):
    client = get_bunq_client()
    endpoint = f"monetary-account/{monetary_account_id}/payment?count=200"
    response = client.request(endpoint=endpoint, method='GET', data=None)
    return response

@app.get("/account_details") #phone number email balance
async def get_account_details(monetary_account_id: str = Depends(get_primary_monetary_account_id)):
    client = get_bunq_client()
    endpoint = f"monetary-account/{monetary_account_id}"
    response = client.request(endpoint=endpoint, method='GET', data=None)
    return response

@app.get("/account_balance") #just balance
async def get_account_balance(monetary_account_id: str = Depends(get_primary_monetary_account_id)):
    client = get_bunq_client()
    endpoint = f"monetary-account/{monetary_account_id}"
    response = client.request(endpoint=endpoint, method='GET', data=None)
    
    try:
        account_data = response.get('Response', [])[0].get('MonetaryAccountBank', {})
        balance = account_data.get('balance', {})
        return {
            "value": balance.get('value'),
            "currency": balance.get('currency')
        }
    except (IndexError, KeyError):
        raise HTTPException(status_code=500, detail="Could not extract balance information")