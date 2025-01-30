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
        print("STRIPE MODE CHECK:")
        print(f"API Key Mode: {'LIVE' if 'live' in stripe.api_key else 'TEST'}")
        print(f"API Key Prefix: {stripe.api_key[:7]}")
        
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
    except Exception as e:
        print(f"Error creating payment intent: {e}")
        return jsonify(error=str(e)), 403

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)