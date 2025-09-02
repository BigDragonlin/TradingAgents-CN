from app_email.send_email.sender import send_email
from app_email.receice_email.receiver import receive_emails
from tradingagents.config.database_manager import DatabaseManager

class EmailManager:
    def __init__(self):
        self.send_email = send_email()
        # self.receiver = receiver()
        self.database_manager = DatabaseManager()

    def send_email(self):
        pass


    def receive_email(self):
        pass

