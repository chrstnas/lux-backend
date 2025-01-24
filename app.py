from flask import Flask, jsonify, request  # Added request here
import stripe

app = Flask(__name__)

# Replace this with your Stripe secret key (sk_test_...)
stripe.api_key = 'sk_test_51QhEsZL2PO7NUOev7FzttFOE9gb1hQ9QOO8WxKyubPValfvunLXBFkDbslKf6WNMWC3gPX0LEuWVT3F0nIeRQbwI00Rmw5QwQe'

@app.route('/create-payment-intent', methods=['POST'])
def create_payment():
    try:
        data = request.get_json()
        amount = data.get('amount', 500)
        print(f"Received request with amount: {amount}")  # Add logging
        
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='usd',
            automatic_payment_methods={"enabled": True}
        )
        print(f"Created payment intent: {intent.id}")  # Add logging
        return jsonify({
            'clientSecret': intent.client_secret
        })
    except Exception as e:
        print(f"Error: {str(e)}")  # Add logging
        return jsonify(error=str(e)), 403