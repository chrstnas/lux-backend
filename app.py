from flask import Flask, jsonify, request, send_file
import stripe
import os
import requests
import json
import uuid
import hashlib
from datetime import datetime
import base64
import io
import tempfile
import zipfile
import subprocess

# Initialize Flask app first
app = Flask(__name__)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Square Configuration
SQUARE_APPLICATION_ID = os.getenv("SQUARE_APPLICATION_ID")
SQUARE_APPLICATION_SECRET = os.getenv("SQUARE_APPLICATION_SECRET")
SQUARE_ENVIRONMENT = 'production'

# Apple Wallet Configuration
PASS_TYPE_ID = os.getenv("PASS_TYPE_ID")  # pass.com.tinas.lux.loyalty
TEAM_ID = os.getenv("TEAM_ID")  # Your Apple Team ID
PASS_CERTIFICATE = os.getenv("PASS_CERTIFICATE")  # Base64 encoded certificate
PASS_PRIVATE_KEY = os.getenv("PASS_PRIVATE_KEY")  # Base64 encoded private key
WWDR_CERTIFICATE = os.getenv("WWDR_CERTIFICATE")  # Base64 encoded WWDR cert



# Color mapping for satBack tiers
def get_tier_color(sat_back):
    """Convert satBack percentage to RGB color string"""
    colors = {
        0: "rgb(156, 163, 175)",  # Gray
        1: "rgb(239, 68, 68)",    # Red
        2: "rgb(251, 146, 60)",   # Orange
        3: "rgb(250, 204, 21)",   # Yellow
        4: "rgb(34, 197, 94)",    # Green
        5: "rgb(59, 130, 246)",   # Blue
        6: "rgb(99, 102, 241)",   # Indigo
        7: "rgb(147, 51, 234)"    # Violet
    }
    
    if sat_back >= 7:
        return colors[7]  # Violet for 7-11%
    return colors.get(sat_back, colors[0])

def fix_base64_padding(base64_string):
    """Fix base64 padding issues"""
    if not base64_string:
        return b''
    # Add padding if needed
    missing_padding = len(base64_string) % 4
    if missing_padding:
        base64_string += '=' * (4 - missing_padding)
    return base64.b64decode(base64_string)


@app.route('/generate-wallet-pass', methods=['POST'])
def generate_wallet_pass():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        merchant_id = data.get('merchant_id')
        merchant_name = data.get('merchant_name')
        merchant_location = data.get('location', {})
        stamps = data.get('stamps', [])
        sat_back = data.get('sat_back', 0)
        credit_balance = data.get('credit_balance', 0)
        
        print(f"Generating pass for user {user_id} at {merchant_name}")
        
        # Create unique serial number
        serial_number = f"{user_id}-{merchant_id}"
        
        # Create pass.json
        pass_json = {
            "formatVersion": 1,
            "passTypeIdentifier": PASS_TYPE_ID,
            "serialNumber": serial_number,
            "teamIdentifier": TEAM_ID,
            "organizationName": "LUX",
            "description": f"{merchant_name} Loyalty Card",
            "foregroundColor": "rgb(255, 255, 255)",
            "backgroundColor": get_tier_color(sat_back),
            "logoText": merchant_name,
            
            "barcode": {
                "format": "PKBarcodeFormatQR",
                "message": f"{user_id}:{merchant_id}",
                "messageEncoding": "iso-8859-1"
            },
            
            "locations": [{
                "latitude": merchant_location.get('lat', 34.0522),
                "longitude": merchant_location.get('lng', -118.2437),
                "relevantText": f"Welcome to {merchant_name}! Tap to check in"
            }] if merchant_location.get('lat') else [],
            
            "storeCard": {
                "primaryFields": [{
                    "key": "stamps",
                    "label": "STAMPS",
                    "value": f"{len([s for s in stamps if s])}/20",
                    "textAlignment": "PKTextAlignmentCenter"
                }],
                
                "secondaryFields": [
                    {
                        "key": "rewards",
                        "label": "REWARDS",
                        "value": f"{sat_back}% back",
                        "textAlignment": "PKTextAlignmentLeft"
                    },
                    {
                        "key": "credit",
                        "label": "CREDIT",
                        "value": f"${credit_balance:.2f}",
                        "textAlignment": "PKTextAlignmentRight"
                    }
                ],
                
                "backFields": [
                    {
                        "key": "member",
                        "label": "Member Since",
                        "value": datetime.now().strftime("%B %Y")
                    },
                    {
                        "key": "lastvisit",
                        "label": "Last Visit", 
                        "value": datetime.now().strftime("%B %d, %Y")
                    }
                ]
            }
        }
        
        # Create the .pkpass file manually
        pass_data = create_pkpass_manually(pass_json)
        
        # Return the pass file
        return send_file(
            io.BytesIO(pass_data),
            mimetype='application/vnd.apple.pkpass',
            as_attachment=True,
            download_name=f'{merchant_name.lower().replace(" ", "-")}-loyalty.pkpass'
        )
        
    except Exception as e:
        print(f"Error generating pass: {str(e)}")
        return jsonify({'error': str(e)}), 400

def create_pkpass_manually(pass_json):
    """Create a properly signed .pkpass file"""
    import subprocess
    
    # Create a temporary directory for pass contents
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write pass.json
        pass_json_path = os.path.join(temp_dir, 'pass.json')
        with open(pass_json_path, 'w') as f:
            json.dump(pass_json, f)
        
        # Create placeholder icon (required!)
        icon_path = os.path.join(temp_dir, 'icon.png')
        # Create a simple 29x29 black square as placeholder
        with open(icon_path, 'wb') as f:
            # PNG header + minimal black square
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x1d\x00\x00\x00\x1d\x08\x02\x00\x00\x00\xfd\xd4\x9as\x00\x00\x00\x1dIDATx\x9c\xed\xc1\x01\r\x00\x00\x00\xc2\xa0\xf7Om\x0e7\xa0\x00\x00\x00\x00\x00\x00\x00\x00\xbe\r!\x00\x00\x01\x9a`\xe1\xd5\x00\x00\x00\x00IEND\xaeB`\x82')
        
        # Create manifest.json
        manifest = {}
        for filename in os.listdir(temp_dir):
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, 'rb') as f:
                content = f.read()
                manifest[filename] = hashlib.sha1(content).hexdigest()
        
        manifest_path = os.path.join(temp_dir, 'manifest.json')
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f)
        
        # Decode certificates from environment variables
        cert_pem = fix_base64_padding(os.getenv('PASS_CERTIFICATE', ''))
        key_pem = fix_base64_padding(os.getenv('PASS_PRIVATE_KEY', ''))
        wwdr_pem = fix_base64_padding(os.getenv('WWDR_CERTIFICATE', ''))
        
        # Write certificates to temp files
        cert_path = os.path.join(temp_dir, 'cert.pem')
        key_path = os.path.join(temp_dir, 'key.pem')
        wwdr_path = os.path.join(temp_dir, 'wwdr.pem')
        
        with open(cert_path, 'wb') as f:
            f.write(cert_pem)
        with open(key_path, 'wb') as f:
            f.write(key_pem)
        with open(wwdr_path, 'wb') as f:
            f.write(wwdr_pem)
        
        # Sign the manifest using OpenSSL
        signature_path = os.path.join(temp_dir, 'signature')
        
        # Create the signature using OpenSSL command
        openssl_cmd = [
            'openssl', 'smime', '-sign',
            '-signer', cert_path,
            '-inkey', key_path,
            '-certfile', wwdr_path,
            '-in', manifest_path,
            '-out', signature_path,
            '-outform', 'DER',
            '-binary'
        ]
        
        try:
            subprocess.run(openssl_cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"Signing error: {e.stderr.decode()}")
            # For now, create placeholder if signing fails
            with open(signature_path, 'wb') as f:
                f.write(b'signature_placeholder')
        
        # Create the .pkpass file (ZIP archive)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add files in specific order
            zip_file.write(pass_json_path, 'pass.json')
            zip_file.write(manifest_path, 'manifest.json')
            zip_file.write(signature_path, 'signature')
            zip_file.write(icon_path, 'icon.png')
        
        return zip_buffer.getvalue()




def format_stamps_for_pass(stamps):
    """Format stamps as a grid for the pass back"""
    grid = ""
    for i in range(0, 20, 5):
        row = []
        for j in range(5):
            idx = i + j
            if idx < len(stamps) and stamps[idx]:
                row.append(stamps[idx].get('emoji', '⭐'))
            else:
                row.append('○')
        grid += ' '.join(row) + '\n'
    return grid.strip()

def generate_auth_token(serial_number):
    """Generate authentication token for pass updates"""
    secret = os.getenv('PASS_UPDATE_SECRET', 'your-secret-key')
    return hashlib.sha256(f"{serial_number}-{secret}".encode()).hexdigest()[:32]

# Add this endpoint for pass updates
@app.route('/pass-updates/<serial_number>', methods=['GET'])
def get_pass_updates(serial_number):
    """Check if pass needs updates"""
    auth_token = request.headers.get('Authorization', '').replace('ApplePass ', '')
    
    # Verify auth token
    expected_token = generate_auth_token(serial_number)
    if auth_token != expected_token:
        return '', 401
    
    # Check if pass needs update (check database for changes)
    # For now, return no update needed
    return '', 204

# This is for later - payment updates
@app.route('/update-pass-for-payment', methods=['POST'])
def update_pass_for_payment():
    # We'll implement this after basic passes work
    pass

# YOUR EXISTING ENDPOINTS CONTINUE HERE...
# YOUR EXISTING ENDPOINTS CONTINUE HERE...

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
            merchant_id = square_oauth_callback.tokens[business_id]['merchant_id']
            print(f"✅ Found Square token for business: {business_id}")
        else:
            print(f"❌ No Square token found for business: {business_id}")
            return jsonify({'error': 'No Square connection found', 'success': False}), 400
            
        base_url = 'https://connect.squareupsandbox.com' if SQUARE_ENVIRONMENT == 'sandbox' else 'https://connect.squareup.com'
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # First, get the merchant's locations
        locations_response = requests.get(f"{base_url}/v2/locations", headers=headers)
        
        if locations_response.status_code != 200:
            print(f"❌ Failed to get locations: {locations_response.text}")
            return jsonify({'error': 'Failed to get merchant locations', 'success': False}), 400
            
        locations_data = locations_response.json()
        
        if not locations_data.get('locations'):
            print("❌ No locations found for merchant")
            return jsonify({'error': 'No locations found', 'success': False}), 400
            
        # Get the first location ID
        location_id = locations_data['locations'][0]['id']
        print(f"✅ Using location ID: {location_id}")
        
        # Now search for orders with the location ID
        response = requests.post(f"{base_url}/v2/orders/search", 
                               headers=headers,
                               json={
                                   "limit": 1,
                                   "location_ids": [location_id],  # Add location_ids here
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
            print("No orders found - trying payments instead")
            
            # Try getting payments instead of orders
            payments_response = requests.get(
                f"{base_url}/v2/payments",
                headers=headers,
                params={
                    "location_id": location_id,
                    "limit": 1,
                    "sort_order": "DESC"
                }
            )
            
            if payments_response.status_code == 200:
                payments_data = payments_response.json()
                if payments_data.get('payments'):
                    payment = payments_data['payments'][0]
                    amount_money = payment.get('amount_money', {})
                    return jsonify({
                        'amount': amount_money.get('amount', 0),
                        'currency': amount_money.get('currency', 'USD'),
                        'payment_id': payment.get('id'),
                        'success': True
                    })
            
            return jsonify({'success': False, 'message': 'No recent orders or payments found'})
        
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
