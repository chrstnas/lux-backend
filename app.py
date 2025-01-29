from flask import Flask, jsonify, request
import stripe
import os

app = Flask(__name__)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@app.route('/check-mode', methods=['GET'])
def check_mode():
   return jsonify({
       'stripe_mode': 'live' if 'live' in stripe.api_key else 'test',
       'api_key_exists': stripe.api_key is not None,
       'api_key_prefix': stripe.api_key[:7] if stripe.api_key else None
   })

@app.route('/create-payment-intent', methods=['POST'])
def create_payment():
   try:
       print(f"API Key prefix: {stripe.api_key[:7]}")  # Will show sk_test or sk_live
       data = request.get_json()
       amount = data.get('amount', 500)
       print(f"Creating payment intent for amount: {amount}")
       
       intent = stripe.PaymentIntent.create(
           amount=amount,
           currency='usd',
           automatic_payment_methods={"enabled": True}
       )
       print(f"Created intent with secret: {intent.client_secret}")
       return jsonify({
           'clientSecret': intent.client_secret
       })
   except Exception