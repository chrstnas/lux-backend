from flask import Flask, jsonify, request
import stripe
import os

app = Flask(__name__)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@app.route('/create-payment-intent', methods=['POST'])
def create_payment():
    try:
        print(f"Stripe API Key set: {stripe.api_key is not None}")
        data = request.get_json()
        amount = data.get('amount', 500)
        print(f"Creating payment intent for amount: {amount}")
        
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='usd',
            automatic_payment_methods={"enabled": True}
        )
        response = {
            'clientSecret': intent.client_secret
        }
        print(f"Sending response: {response}")
        return jsonify(response)
    except Exception as e:
        print(f"Error creating payment intent: {e}")
        return jsonify(error=str(e)), 403

if __name__ == '__main__':
    app.run(port=4242)