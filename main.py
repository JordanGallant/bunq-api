from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Response
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
):
    try:
        # Enhanced logging for debugging
        print(f"Received file: {file.filename}, size: {file.size}, content_type: {file.content_type}")
        
        # Check API key first - most common issue
        if not REPLICATE_API_KEY:
            print("ERROR: Replicate API key not configured")
            raise HTTPException(status_code=500, detail="Replicate API key not configured")
            
        # Set API key for replicate
        os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_KEY
        
        # Read uploaded file
        swap_face_content = await file.read()
        print(f"Read {len(swap_face_content)} bytes from uploaded file")
        
        try:
            # Try to upload to temporary URL
            swap_face_url = await upload_to_temp_url(swap_face_content)
            print(f"Uploaded to temporary URL: {swap_face_url}")
        except Exception as upload_error:
            print(f"Error uploading to temporary URL: {str(upload_error)}")
            raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(upload_error)}")
        
        # Direct image URL - using a known working image for testing
        base_image_url = "https://i.ibb.co/s938KWxH/angry-old-man-shouting.jpg"
        
        # Call Replicate API
        input_data = {
            "swap_image": swap_face_url,
            "input_image": base_image_url
        }
        
        print(f"Calling Replicate API with input: {input_data}")
        
        try:
            output = replicate.run(
                "cdingram/face-swap:d1d6ea8c8be89d664a07a457526f7128109dee7030fdac424788d762c71ed111",
                input=input_data
            )
            print(f"Replicate API response: {output}")
        except Exception as replicate_error:
            print(f"Replicate API error: {str(replicate_error)}")
            raise HTTPException(status_code=500, detail=f"Replicate API error: {str(replicate_error)}")
        
        # Download the result image
        if not output:
            print("No output from Replicate API")
            raise HTTPException(status_code=500, detail="Face swap processing failed - no output")
        
        try:
            # The output from this model is a URL to the processed image
            async with httpx.AsyncClient() as client:
                print(f"Downloading result from: {output}")
                response = await client.get(output.url)
                print(f"Downloading result from: {output.url}")
                print(f"Download response status: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"Error downloading result: {response.text}")
                    raise HTTPException(status_code=500, detail="Failed to retrieve processed image")
                    
                image_data = response.content
                print(f"Downloaded {len(image_data)} bytes of image data")
        except Exception as download_error:
            print(f"Error downloading result: {str(download_error)}")
            raise HTTPException(status_code=500, detail=f"Failed to download result: {str(download_error)}")
        
        # Return the image
        print("Returning image response")
        return StreamingResponse(io.BytesIO(image_data), media_type="image/jpeg")
        
    except Exception as e:
        # Detailed error logging
        import traceback
        error_details = traceback.format_exc()
        print(f"Face swap error: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=f"Face swap failed: {str(e)}")