from fastapi import FastAPI
from lib.bunq_lib import BunqClient


USER_API_KEY = "sandbox_510c476fe8f8a00b6d79fd8d798ad4878bc0294b5fd8bac5440cf850"

bunq_client = BunqClient(USER_API_KEY, service_name='PeterScript')


# Run these 1x to initialize your application 
bunq_client.create_installation()
bunq_client.create_device_server()


bunq_client.create_session()

app = FastAPI()


@app.get("/monetary_account")
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

@app.get("/payment")
def payment():
    payment = bunq_client.create_payment(
        amount='0.10', 
        recipient_iban='NL14RABO0169202917',
        currency='EUR',
        from_monetary_account_id='1989601', 
        description='test'
    )
    return payment
