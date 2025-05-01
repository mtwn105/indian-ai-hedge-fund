import logging
from kiteconnect import KiteConnect
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("KITE_API_KEY")
api_secret = os.getenv("KITE_API_SECRET")

kite = KiteConnect(api_key=api_key)

print(f"Go to {kite.login_url()} and get the request token")

request_token = input("Enter the request token: ")

# Generate session using the request token
data = kite.generate_session(request_token, api_secret=api_secret)
logging.info("Data: %s", data)


print(f"Kite Access Token: {data['access_token']}")
