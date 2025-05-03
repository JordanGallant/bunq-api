from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Response, Body
from fastapi.responses import StreamingResponse
from lib.bunq_lib import BunqClient
from dotenv import load_dotenv
import os
from typing import Dict, Any, Optional
from fastapi.middleware.cors import CORSMiddleware
from functools import lru_cache
import replicate
import io
import httpx
import base64

load_dotenv()
USER_API_KEY = os.getenv("API_KEY")
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY")  # Add this to your .env file

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@lru_cache() #ensuring bunqclient is set up -> authorization
def get_bunq_client():
    client = BunqClient(USER_API_KEY, service_name='PeterScript')
    client.create_session()
    return client

def fetch_account_balance(monetary_account_id: str):
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

@app.get("/")
@app.head("/") 
async def root():
    return {"message": "Welcome to the BunqScript API", 
            "documentation": "/docs",
            "available_endpoints": [
                "/monetary_account",
                "/get_cards",
                "/payment",
                "/transactions",
                "/account_details",
                "/account_balance",
                "/face_swap"
            ]}

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

@app.post("/payment")
async def payment(
    amount: str = Body(...),
    iban: str = Body(...),
    monetary_account_id: str = Depends(get_primary_monetary_account_id)
):
    client = get_bunq_client()
    payment = client.create_payment(
        amount=amount,
        recipient_iban=iban,
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

@app.get("/account_balance")
async def get_account_balance(monetary_account_id: str = Depends(get_primary_monetary_account_id)):
    return fetch_account_balance(monetary_account_id)

# New function to upload file to a temporary URL for Replicate
async def upload_to_temp_url(file_data: bytes) -> str:
    
    try:
        IMGBB_API_KEY = os.getenv("IMGBB_API_KEY")
        url = f"https://api.imgbb.com/1/upload?key={IMGBB_API_KEY}"
        
        files = {
            "image": base64.b64encode(file_data).decode("utf-8"),
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=files)
            result = response.json()
            
            if response.status_code != 200 or not result.get("success"):
                raise HTTPException(status_code=500, detail="Failed to upload image")
                
            return result["data"]["url"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading image: {str(e)}")

@app.post("/face_swap")
async def face_swap(
    file: UploadFile = File(...),
    monetary_account_id: str = Depends(get_primary_monetary_account_id)
):
    try:
        print(f"Received file: {file.filename}, size: {file.size}, content_type: {file.content_type}")

        if not REPLICATE_API_KEY:
            raise HTTPException(status_code=500, detail="Replicate API key not configured")

        os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_KEY
        swap_face_content = await file.read()

        try:
            swap_face_url = await upload_to_temp_url(swap_face_content)
        except Exception as upload_error:
            raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(upload_error)}")

        # 🔽 Get balance and set base image accordingly
        balance_info = fetch_account_balance(monetary_account_id)
        try:
            balance_value = float(balance_info["value"])
        except (ValueError, TypeError):
            raise HTTPException(status_code=500, detail="Invalid balance value")

        if balance_value > 1000:
            base_image_url = "https://i.ibb.co/tM6X9T81/8640671.jpg"
        elif balance_value < 100:
            base_image_url = "https://i.ibb.co/s938KWxH/angry-old-man-shouting.jpg"
        else:
            base_image_url = "https://default-image-url.com/image.jpg"  # Optional middle case

        input_data = {
            "swap_image": swap_face_url,
            "input_image": base_image_url
        }

        try:
            output = replicate.run(
                "cdingram/face-swap:d1d6ea8c8be89d664a07a457526f7128109dee7030fdac424788d762c71ed111",
                input=input_data
            )
        except Exception as replicate_error:
            raise HTTPException(status_code=500, detail=f"Replicate API error: {str(replicate_error)}")

        if not output:
            raise HTTPException(status_code=500, detail="Face swap processing failed - no output")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(output.url)
                if response.status_code != 200:
                    raise HTTPException(status_code=500, detail="Failed to retrieve processed image")
                image_data = response.content
        except Exception as download_error:
            raise HTTPException(status_code=500, detail=f"Failed to download result: {str(download_error)}")

        return StreamingResponse(io.BytesIO(image_data), media_type="image/jpeg")

    except Exception as e:
        import traceback
        print(f"Face swap error: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Face swap failed: {str(e)}")
