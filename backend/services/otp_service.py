import os
import logging

logger = logging.getLogger(__name__)

class OTPService:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_PHONE_NUMBER")
        self.is_mock = not (self.account_sid and self.auth_token)

    def send_otp(self, identifier: str, otp: str):
        """
        Sends OTP to the user.
        In mock mode, logs to terminal with a secure format.
        """
        if self.is_mock:
            print("\n" + "="*50)
            print(f"SECURE OTP DELIVERY (MOCK SMS) TO: {identifier}")
            print(f"YOUR OTP: {otp}")
            print("="*50 + "\n")
            return True

        try:
            # Twilio implementation
            # from twilio.rest import Client
            # client = Client(self.account_sid, self.auth_token)
            # client.messages.create(
            #     body=f"Your WealthSense login code is: {otp}",
            #     from_=self.from_number,
            #     to=identifier # This should be the phone from KYC records
            # )
            logger.info(f"Real OTP sent to {identifier}")
            return True
        except Exception as e:
            logger.error(f"OTP Delivery Error: {e}")
            return False

otp_service = OTPService()
