# ITRFill — Complete Setup Guide

---

## STEP 1 — Get your FREE Gemini API Key (5 minutes)

1. Open: https://aistudio.google.com
2. Sign in with your Google account
3. Click "Get API Key" button
4. Click "Create API Key"
5. Copy the key — looks like: AIzaSyXXXXXXXXXXXXXXXXXXXXX

FREE limits:
- 1,500 requests per day
- Enough for hundreds of Form 16 readings daily
- No credit card needed

---

## STEP 2 — Setup in WSL

Open your WSL terminal and run:

```bash
# Go to project
cd /mnt/c/Users/ADMIN/Desktop/itrfill

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install all packages
pip install -r requirements.txt

# Install Playwright browser (needed for auto-filing)
playwright install chromium
playwright install-deps chromium
```

---

## STEP 3 — Configure your keys

```bash
cp .env.example .env
nano .env
```

Fill in:
```
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXX        ← from aistudio.google.com
RAZORPAY_KEY_ID=rzp_test_XXXXXXXXX         ← from dashboard.razorpay.com
RAZORPAY_KEY_SECRET=XXXXXXXXXXXXX          ← from dashboard.razorpay.com
SECRET_KEY=ITRFill@India2025#Secure99      ← keep this as is
```

Save: Ctrl+X → Y → Enter

---

## STEP 4 — Run locally

```bash
python app.py
```

Open browser: http://localhost:5000

---

## STEP 5 — Deploy to Render.com (FREE, public URL)

### 5a. Push to GitHub
```bash
sudo apt install git -y
git config --global user.email "your@email.com"
git config --global user.name "Your Name"

cd /mnt/c/Users/ADMIN/Desktop/itrfill
git init
git add .
git commit -m "ITRFill - AI ITR filing app"
```

Go to github.com → New Repository → name: itrfill → Create

```bash
git remote add origin https://github.com/YOURUSERNAME/itrfill.git
git push -u origin main
```

### 5b. Deploy on Render
1. Go to render.com → Sign up free
2. New → Web Service
3. Connect GitHub → select itrfill repo
4. Render reads render.yaml automatically
5. Add Environment Variables:
   - GEMINI_API_KEY
   - RAZORPAY_KEY_ID
   - RAZORPAY_KEY_SECRET
6. Click Deploy

Your app is live at: https://itrfill.onrender.com

---

## HOW AUTO-FILING WORKS

When user provides their IT portal password:

1. Playwright opens incometax.gov.in in a headless browser
2. Logs in with user's PAN + password
3. Navigates to e-File → ITR → Upload XML
4. Uploads the generated ITR-1 XML
5. Reaches Aadhaar OTP verification screen
6. App notifies user: "Enter OTP now"
7. User enters OTP (30 seconds)
8. ITR is filed ✓

If user does NOT provide password:
- App generates XML only
- User uploads manually (3 minutes)

---

## REVENUE

₹299 per filing
- Razorpay fee: ₹6
- Gemini API: ₹0 (free)
- Hosting: ₹0 (free on Render)
- YOUR PROFIT: ₹293 per filing

100 filings/month = ₹29,300
1000 filings/month = ₹2,93,000

ITR season: June 1 — July 31 every year
This is when 8 crore Indians file. Be ready before June.

---

## MARKETING (FREE)

Week 1: WhatsApp to all your contacts
Week 2: LinkedIn post
Week 3: Reddit r/IndiaTax, r/IndiaInvestments
Week 4: YouTube Short showing the demo

Message to send:
"I built a tool that files your ITR automatically in 10 minutes.
Upload Form 16, AI does everything, costs ₹299.
Try it: https://itrfill.onrender.com"

---

## SWITCH TO LIVE PAYMENTS

When ready to charge real money:
1. Login to Razorpay → complete KYC (PAN + bank)
2. Get LIVE keys from Settings → API Keys
3. Update in Render environment variables
4. Done — real payments start flowing

---

## PUSH UPDATES

After any code change:
```bash
git add .
git commit -m "Update"
git push
```
Render auto-deploys every time you push.
```
