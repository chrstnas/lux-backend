from flask import Flask, jsonify, request
import stripe
import os
import requests
import json
import uuid

# Square Configuration
SQUARE_APPLICATION_ID = os.getenv("SQUARE_APPLICATION_ID")  # sq0idp-KDndMxSr3s3O7bYeVzqdQw
SQUARE_APPLICATION_SECRET = os.getenv("SQUARE_APPLICATION_SECRET")  # Your secret
SQUARE_ENVIRONMENT = 'sandbox'  # Change to 'production' later

app = Flask(__name__)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@app.route('/debug/square-config', methods=['GET'])
def debug_square_config():
    return jsonify({
        'SQUARE_APPLICATION_ID': SQUARE_APPLICATION_ID,
        'SQUARE_ENVIRONMENT': SQUARE_ENVIRONMENT,
        'has_secret': SQUARE_APPLICATION_SECRET is not None
    })

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
            automatic_payment_methods={
                "enabled": True,
                "allow_redirects": "always"
            }
        )
        print(f"Created intent with secret: {intent.client_secret}")
        return jsonify({
            'clientSecret': intent.client_secret
        })
    except Exception as e:
        print(f"Error creating payment intent: {e}")
        return jsonify(error=str(e)), 403

# STRIPE CONNECT ENDPOINTS
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
            country='US',
            email=business_email,
            business_type='individual',
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

@app.route('/stripe-return', methods=['GET'])
def stripe_return():
    return """
    <html>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h2>✅ Stripe Setup Complete!</h2>
            <p>You can now close this window and return to the LUX app.</p>
            <script>
                setTimeout(function() {
                    window.close();
                }, 3000);
            </script>
        </body>
    </html>
    """

@app.route('/stripe-refresh', methods=['GET'])
def stripe_refresh():
    return """
    <html>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h2>🔄 Setting up Stripe...</h2>
            <p>Please wait while we set up your account.</p>
        </body>
    </html>
    """

@app.route('/payment-return')
def payment_return():
    return """
    <html>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h2>✅ Payment Complete!</h2>
            <p>Your payment was processed successfully. You can close this window.</p>
            <script>
                setTimeout(function() {
                    window.close();
                }, 3000);
            </script>
        </body>
    </html>
    """

@app.route('/create-balance-payment', methods=['POST'])
def create_balance_payment():
    try:
        data = request.get_json()
        merchant_stripe_account = data.get('merchant_stripe_account')  # Connected account ID
        amount_cents = data.get('amount_cents')  # Amount in cents
        base_amount_cents = data.get('base_amount_cents')  # Base without tip
        tip_amount_cents = data.get('tip_amount_cents', 0)  # Tip amount
        merchant_rate = data.get('merchant_rate', 0)  # Reward percentage
        transaction_id = data.get('transaction_id')  # For tracking
        
        print(f"Creating balance payment to merchant: {merchant_stripe_account}")
        print(f"Total amount: ${amount_cents/100} (Base: ${base_amount_cents/100}, Tip: ${tip_amount_cents/100})")
        print(f"Merchant rate: {merchant_rate}%")
        
        # Calculate what merchant gets (base minus rewards + full tip)
        reward_amount = int(base_amount_cents * merchant_rate / 100)
        platform_fee = int(base_amount_cents * 0.01)  # 1% platform fee on base only
        merchant_receives = base_amount_cents - reward_amount - platform_fee + tip_amount_cents
        
        print(f"Merchant receives: ${merchant_receives/100}")
        print(f"Reward pool: ${reward_amount/100}")
        print(f"Platform fee: ${platform_fee/100}")
        
        # Create the transfer to merchant
        transfer = stripe.Transfer.create(
            amount=merchant_receives,
            currency='usd',
            destination=merchant_stripe_account,
            description=f"Payment for transaction {transaction_id}",
            metadata={
                'transaction_id': transaction_id,
                'base_amount': base_amount_cents,
                'tip_amount': tip_amount_cents,
                'reward_amount': reward_amount,
                'platform_fee': platform_fee
            }
        )
        
        print(f"✅ Transfer created: {transfer.id}")
        
        return jsonify({
            'transfer_id': transfer.id,
            'merchant_received': merchant_receives,
            'reward_amount': reward_amount,
            'platform_fee': platform_fee,
            'success': True
        })
        
    except stripe.error.StripeError as e:
        print(f"❌ Stripe error: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 400
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 400

@app.route('/get-recent-charge', methods=['POST'])
def get_recent_charge():
    try:
        data = request.get_json()
        account_id = data.get('account_id')
        
        print(f"Fetching recent charges for account: {account_id}")
        
        # Get charges from the connected account
        charges = stripe.Charge.list(
            limit=1,
            stripe_account=account_id
        )
        
        if charges.data:
            charge = charges.data[0]
            return jsonify({
                'amount': charge.amount,
                'description': charge.description,
                'created': charge.created,
                'success': True
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No recent charges found'
            })
            
    except Exception as e:
        print(f"❌ Error fetching charges: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 400

@app.route('/square/oauth/authorize', methods=['POST'])
def square_oauth_authorize():
    """Generate Square OAuth URL for merchant to connect"""
    try:
        data = request.get_json()
        business_id = data.get('business_id')
        
        print(f"🔍 DEBUG: Received business_id: {business_id}")
        print(f"🔍 DEBUG: SQUARE_APPLICATION_ID: {SQUARE_APPLICATION_ID}")
        print(f"🔍 DEBUG: SQUARE_ENVIRONMENT: {SQUARE_ENVIRONMENT}")
        
        # Generate state parameter for security
        state = f"business_{business_id}_{uuid.uuid4()}"
        print(f"🔍 DEBUG: Generated state: {state}")
        
        base_url = 'https://connect.squareupsandbox.com' if SQUARE_ENVIRONMENT == 'sandbox' else 'https://connect.squareup.com'
        
        oauth_url = f"{base_url}/oauth2/authorize?" \
                   f"client_id={SQUARE_APPLICATION_ID}&" \
                   f"scope=MERCHANT_PROFILE_READ+ORDERS_READ+PAYMENTS_READ&" \
                   f"session=false&" \
                   f"state={state}"
        
        print(f"🔍 DEBUG: Generated OAuth URL: {oauth_url}")
        
        return jsonify({
            'oauth_url': oauth_url,
            'state': state,
            'success': True
        })
        
    except Exception as e:
        print(f"❌ Error generating Square OAuth URL: {e}")
        return jsonify({'error': str(e), 'success': False}), 400



@app.route('/square/oauth/callback', methods=['GET'])
def square_oauth_callback():
    """Handle Square OAuth callback"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            print(f"❌ Square OAuth error: {error}")
            return f"<html><body><h2>❌ Connection Failed</h2><p>{error}</p></body></html>"
        
        if not code:
            return "<html><body><h2>❌ No authorization code received</h2></body></html>"
        
        # Exchange code for access token
        base_url = 'https://connect.squareupsandbox.com' if SQUARE_ENVIRONMENT == 'sandbox' else 'https://connect.squareup.com'
        
        token_data = {
            'client_id': SQUARE_APPLICATION_ID,
            'client_secret': SQUARE_APPLICATION_SECRET,
            'code': code,
            'grant_type': 'authorization_code'
        }
        
        response = requests.post(f"{base_url}/oauth2/token", json=token_data)
        token_response = response.json()
        
        if 'access_token' not in token_response:
            print(f"❌ Token exchange failed: {token_response}")
            return "<html><body><h2>❌ Token exchange failed</h2></body></html>"



        access_token = token_response['access_token']
        merchant_id = token_response['merchant_id']
        
        print(f"✅ Square OAuth successful for merchant: {merchant_id}")  # Fix indentation
        
        # Save tokens in memory (replace with database later)
        if not hasattr(square_oauth_callback, 'tokens'):
            square_oauth_callback.tokens = {}
        
        business_id = state.split('_')[1] if state and 'business_' in state else 'default'
        square_oauth_callback.tokens[business_id] = {
            'access_token': access_token,
            'merchant_id': merchant_id
        }
        print(f"✅ Saved Square token for business: {business_id}")
        
        return """



        <html>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h2>✅ Square Connected Successfully!</h2>
                <p>You can now close this window and return to the LUX app.</p>
                <script>
                    setTimeout(function() {
                        window.close();
                    }, 3000);
                </script>
            </body>
        </html>
        """
        
    except Exception as e:
        print(f"❌ Square OAuth callback error: {e}")
        return f"<html><body><h2>❌ Connection Error</h2><p>{str(e)}</p></body></html>"


@app.route('/square/get-recent-order', methods=['POST'])
def get_recent_square_order():
    """Fetch merchant's most recent Square order"""
    try:
        data = request.get_json()
        business_id = data.get('business_id')
        
        # Get token from memory
        if hasattr(square_oauth_callback, 'tokens') and business_id in square_oauth_callback.tokens:
            access_token = square_oauth_callback.tokens[business_id]['access_token']
            print(f"✅ Found Square token for business: {business_id}")
        else:
            print(f"❌ No Square token found for business: {business_id}")
            return jsonify({'error': 'No Square connection found', 'success': False}), 400
            
        base_url = 'https://connect.squareupsandbox.com' if SQUARE_ENVIRONMENT == 'sandbox' else 'https://connect.squareup.com'
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Get recent orders
        response = requests.post(f"{base_url}/v2/orders/search", 
                               headers=headers,
                               json={
                                   "limit": 1,
                                   "query": {
                                       "sort": {
                                           "sort_field": "CREATED_AT",
                                           "sort_order": "DESC"
                                       }
                                   }
                               })

        print(f"Square API response status: {response.status_code}")
        print(f"Square API response: {response.text[:500]}")  # First 500 chars

        if response.status_code != 200:
            error_detail = response.json().get('errors', [{}])[0].get('detail', 'Unknown error')
            print(f"❌ Square API error: {error_detail}")
            return jsonify({
                'error': f'Square API error: {error_detail}',
                'success': False
            }), 400
        
        orders_data = response.json()
        
        if not orders_data.get('orders'):
            return jsonify({'success': False, 'message': 'No recent orders found'})
        
        recent_order = orders_data['orders'][0]
        total_money = recent_order.get('total_money', {})
        amount_cents = total_money.get('amount', 0)
        
        return jsonify({
            'amount': amount_cents,  # Amount in cents
            'currency': total_money.get('currency', 'USD'),
            'order_id': recent_order.get('id'),
            'success': True
        })
        
    except Exception as e:
        print(f"❌ Error fetching Square order: {e}")
        return jsonify({'error': str(e), 'success': False}), 400
        
if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
