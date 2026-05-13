from flask import Flask, request, render_template, jsonify, send_file, session
import os
import json
import threading
import razorpay
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from form16_parser import parse_form16_with_gemini
from tax_calculator import compare_regimes
from itr_xml_generator import generate_itr1_xml
from itr_filer import file_itr_sync
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import base64
import hashlib

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "itrfill-secret-2025")
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs('uploads', exist_ok=True)
os.makedirs('outputs', exist_ok=True)

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
PRICE_PAISE = 29900  # ₹299

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/refund')
def refund():
    return render_template('refund.html')

# Simple encryption for IT portal password
def encrypt_password(password):
    key = hashlib.sha256(app.secret_key.encode()).digest()
    key_b64 = base64.urlsafe_b64encode(key)
    f = Fernet(key_b64)
    return f.encrypt(password.encode()).decode()

def decrypt_password(encrypted):
    key = hashlib.sha256(app.secret_key.encode()).digest()
    key_b64 = base64.urlsafe_b64encode(key)
    f = Fernet(key_b64)
    return f.decrypt(encrypted.encode()).decode()

# In-memory job tracker
filing_jobs = {}

@app.route('/')
def home():
    return render_template('index.html',
                           razorpay_key=RAZORPAY_KEY_ID,
                           price=PRICE_PAISE)

@app.route('/upload', methods=['POST'])
def upload_form16():
    if 'form16' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['form16']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        form16_data = parse_form16_with_gemini(filepath)
        tax_result = compare_regimes(form16_data)
        return jsonify({
            'success': True,
            'employee_name': form16_data.get('employee_name', ''),
            'pan': form16_data.get('pan_number', ''),
            'employer_name': form16_data.get('employer_name', ''),
            'gross_salary': form16_data.get('gross_salary', 0),
            'tds_paid': form16_data.get('total_tds_deducted', 0),
            'old_regime_tax': tax_result['old_regime']['tax_liability'],
            'new_regime_tax': tax_result['new_regime']['tax_liability'],
            'recommended': tax_result['recommended'],
            'savings': tax_result['savings'],
            'old_refund': tax_result['old_regime']['refund_or_due'],
            'new_refund': tax_result['new_regime']['refund_or_due'],
            'form16_path': filepath
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/create-order', methods=['POST'])
def create_order():
    try:
        rz = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        order = rz.order.create({'amount': PRICE_PAISE, 'currency': 'INR', 'payment_capture': 1})
        return jsonify({'order_id': order['id'], 'amount': PRICE_PAISE})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/verify-payment', methods=['POST'])
def verify_payment():
    try:
        data = request.json
        rz = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        rz.utility.verify_payment_signature({
            'razorpay_order_id': data['razorpay_order_id'],
            'razorpay_payment_id': data['razorpay_payment_id'],
            'razorpay_signature': data['razorpay_signature']
        })
        return jsonify({'verified': True})
    except Exception as e:
        return jsonify({'verified': False, 'error': str(e)}), 400

@app.route('/generate-and-file', methods=['POST'])
def generate_and_file():
    data = request.json
    try:
        # Parse Form 16 again
        form16_data = parse_form16_with_gemini(data['form16_path'])

        extra_deductions = {
            'home_loan_interest': int(data.get('home_loan_interest', 0) or 0),
            'rent_paid': int(data.get('monthly_rent', 0) or 0) * 12,
            'extra_80c': int(data.get('extra_80c', 0) or 0),
            'extra_80d': int(data.get('extra_80d', 0) or 0)
        }

        tax_result = compare_regimes(form16_data, extra_deductions)

        answers = {
            'bank_details': data.get('bank_details', ''),
            'monthly_rent': data.get('monthly_rent', 0),
            'home_loan_interest': data.get('home_loan_interest', 0),
            'other_income': data.get('other_income', 0),
            'extra_80c': data.get('extra_80c', 0),
            'extra_80d': data.get('extra_80d', 0)
        }

        # Generate XML
        xml_file = generate_itr1_xml(form16_data, answers, tax_result)
        regime = tax_result['recommended']
        refund = tax_result[f"{regime}_regime"]['refund_or_due']

        # Start auto-filing in background thread
        it_password = data.get('it_password', '')
        pan = form16_data.get('pan_number', '')
        job_id = f"{pan}_{regime}"

        if it_password and pan:
            encrypted_pass = encrypt_password(it_password)
            filing_jobs[job_id] = {"status": "starting", "step": "initializing"}

            def run_filer():
                try:
                    filing_jobs[job_id]["status"] = "running"
                    decrypted = decrypt_password(encrypted_pass)
                    result = file_itr_sync(pan, decrypted, xml_file)
                    filing_jobs[job_id] = result
                except Exception as e:
                    filing_jobs[job_id] = {"status": "error", "message": str(e)}

            thread = threading.Thread(target=run_filer, daemon=True)
            thread.start()

        return jsonify({
            'success': True,
            'xml_file': xml_file,
            'tax_liability': tax_result[f"{regime}_regime"]['tax_liability'],
            'refund': refund,
            'regime': regime,
            'job_id': job_id,
            'auto_filing': bool(it_password and pan)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/filing-status/<job_id>')
def filing_status(job_id):
    status = filing_jobs.get(job_id, {"status": "not_found"})
    return jsonify(status)

@app.route('/download/<path:filename>')
def download_xml(filename):
    return send_file(
        filename,
        as_attachment=True,
        download_name=os.path.basename(filename)
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

