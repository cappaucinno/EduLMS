from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Send a test email to verify Gmail/SMTP configuration'

    def add_arguments(self, parser):
        parser.add_argument('recipient', type=str, help='Email address to send test to')

    def handle(self, *args, **options):
        recipient = options['recipient']
        self.stdout.write(f"Backend:  {settings.EMAIL_BACKEND}")
        self.stdout.write(f"From:     {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"SMTP User:{settings.EMAIL_HOST_USER}")
        self.stdout.write(f"Sending test email to {recipient}...")
        try:
            send_mail(
                subject=f"[{settings.SCHOOL_NAME}] EduLMS Email Test",
                message="This is a test email from EduLMS. If you received this, your email configuration is working correctly.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f"✅ Email sent successfully to {recipient}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Email failed: {e}"))
            self.stdout.write(self.style.WARNING(
                "\nTroubleshooting:\n"
                "1. Copy local_settings.py.example → lms_project/local_settings.py\n"
                "2. Fill in EMAIL_HOST_USER and EMAIL_HOST_PASSWORD (Gmail App Password)\n"
                "3. Make sure 2FA is enabled on your Gmail account\n"
                "4. Re-run this command"
            ))
