# Copy this file to: lms_project/local_settings.py
# Then fill in your credentials. This file is .gitignored.

# ── Site URL (REQUIRED for setup link emails to work) ─────────────────────────
# While developing with ngrok:
SITE_BASE_URL = 'https://uncontagiously-nonplanetary-aleisha.ngrok-free.app'
# While running locally:
# SITE_BASE_URL = 'http://127.0.0.1:8000'

SCHOOL_NAME = 'Your High School Name'

# ── Gmail SMTP ────────────────────────────────────────────────────────────────
# Step 1: Enable 2FA on your Gmail
# Step 2: myaccount.google.com → Security → App Passwords → create one
# Step 3: Paste the 16-char code as EMAIL_HOST_PASSWORD

EMAIL_BACKEND      = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST_USER    = 'yourschool@gmail.com'
EMAIL_HOST_PASSWORD = 'xxxx xxxx xxxx xxxx'   # Gmail App Password
DEFAULT_FROM_EMAIL  = 'EduLMS <yourschool@gmail.com>'

# ── Google OAuth (for "Continue with Google" login) ────────────────────────────
# Step 1: Go to https://console.cloud.google.com
# Step 2: APIs & Services → Credentials → Create OAuth 2.0 Client ID
# Step 3: Application type: Web application
# Step 4: Authorised redirect URIs: http://127.0.0.1:8000/auth/google/login/callback/
#          (or your ngrok URL for dev)
# Step 5: Copy the Client ID and Secret below

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APP': {
            'client_id': 'YOUR_GOOGLE_CLIENT_ID',
            'secret':    'YOUR_GOOGLE_CLIENT_SECRET',
            'key':       '',
        }
    }
}

# ── Jitsi Meet ─────────────────────────────────────────────────────────────────
# Default: uses free public meet.jit.si server (no setup needed)
JITSI_DOMAIN = 'meet.jit.si'
# Optional: use your own 8x8.vc account for private/branded rooms
# JITSI_DOMAIN = 'YOUR_8X8_DOMAIN'
