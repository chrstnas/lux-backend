from flask import Flask, jsonify, request  # Added request here
import stripe

app = Flask(__name__)

# Replace this with your Stripe secret key (sk_test_...)
stripe.api_key = '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'

@app.route('/create-payment-intent', methods=['POST'])
def create_payment():
    try:
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
            'clientSecret': intent.client_secret  # Verify this matches exactly
        })
    except Exception as e:
        print(f"Error creating payment intent: {e}")
        return jsonify(error=str(e)), 403
