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
        print("STRIPE KEY DIAGNOSTICS:")
        print(f"Stripe Secret Key Prefix: {stripe.api_key[:7]}")
        print(f"Stripe Secret Key Contains 'live': {'live' in stripe.api_key}")
        
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

# ✅ NEW STRIPE CONNECT ENDPOINTS
@app.route('/create-express-account', methods=['POST'])
def create_express_account():
    try:
        data = request.get_json()
        business_id = data.get('business_id')
        business_name = data.get('business_name')
        business_email = data.get('business_email')
        
        print(f"Creating Express account for business: {business_id}")
        
        account = stripe.Account.create(
            type='express',
            country='US',  # Adjust based on your merchants' countries
            email=business_email,
            business_type='individual',  # or 'company' based on your needs
            metadata={
                'business_id': business_id,
                'platform': 'lux'
            }
        )
        
        print(f"✅ Created Express account: {account.id}")
        
        return jsonify({
            'account_id': account.id,
            'success': True
        })
        
    except Exception as e:
        print(f"❌ Error creating Express account: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 400

@app.route('/create-onboarding-link', methods=['POST'])
def create_onboarding_link():
    try:
        data = request.get_json()
        account_id = data.get('account_id')
        return_url = data.get('return_url')
        refresh_url = data.get('refresh_url')
        
        print(f"Creating onboarding link for account: {account_id}")
        
        account_link = stripe.AccountLink.create(
            account=account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type='account_onboarding',
        )
        
        print(f"✅ Created onboarding link for account: {account_id}")
        
        return jsonify({
            'url': account_link.url,
            'success': True
        })
        
    except Exception as e:
        print(f"❌ Error creating onboarding link: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 400

@app.route('/create-express-login', methods=['POST'])
def create_express_login():
    try:
        data = request.get_json()
        account_id = data.get('account_id')
        
        print(f"Creating login link for account: {account_id}")
        
        login_link = stripe.Account.create_login_link(account_id)
        
        print(f"✅ Created login link for account: {account_id}")
        
        return jsonify({
            'url': login_link.url,
            'success': True
        })
        
    except Exception as e:
        print(f"❌ Error creating login link: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 400

@app.route('/account-status/<account_id>', methods=['GET'])
def account_status(account_id):
    try:
        print(f"Checking status for account: {account_id}")
        
        account = stripe.Account.retrieve(account_id)
        
        return jsonify({
            'charges_enabled': account.charges_enabled,
            'payouts_enabled': account.payouts_enabled,
            'details_submitted': account.details_submitted,
            'success': True
        })
        
    except Exception as e:
        print(f"❌ Error checking account status: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 400

@app.route('/transfer-to-merchant', methods=['POST'])
def transfer_to_merchant():
    try:
        data = request.get_json()
        destination_account = data.get('destination_account')
        amount_cents = data.get('amount_cents')
        currency = data.get('currency', 'usd')
        description = data.get('description')
        metadata = data.get('metadata', {})
        
        print(f"Creating transfer to {destination_account} for ${amount_cents/100}")
        
        transfer = stripe.Transfer.create(
            amount=amount_cents,
            currency=currency,
            destination=destination_account,
            description=description,
            metadata=metadata
        )
        
        print(f"✅ Created transfer: {transfer.id} Amount: ${amount_cents/100}")
        
        return jsonify({
            'transfer_id': transfer.id,
            'success': True
        })
        
    except Exception as e:
        print(f"❌ Error creating transfer: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 400

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
