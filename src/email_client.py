import smtplib
import sys

from bson import ObjectId

sys.path.append("..")

from constants import *
sys.path.append(CONFIG_FILE_PATH)

from config import *
from utils import *

class EmailClient:

    def __int__(self):
        mongoCon = get_mongo_connection()
        db = get_banking_db(mongoCon)
        me = smtplib.SMTP(host='smtp.gmail.com', port=587)
        me.starttls()
        me.login(PROJECT_EMAIL_ID, PROJECT_EMAIL_PASSWORD)


    def sendAccountCreatedUpdate(self, acc_num):
        accounts = get_accounts_collection(db)
        account = accounts.find_one({"number":acc_num})
        if not account:
            raise Exception("Account does not exist")

        name = account["name"]
        email = account["email"]
        msg = get_account_created_template()
        msg_body = msg.substitute(CUSTOMER_NAME=name.title())
        message = 'Subject: {}\n\n{}'.format("Congratulations! You're all set", msg_body)
        s.sendmail(PROJECT_EMAIL_ID, email, message)


    def sendTransferUpdate(self, payer, payee):
        accounts = get_accounts_collection(db)
        payer_acc = accounts.find_one({"number":payer["acc_num"]})

        email = payer_acc["email"]
        name = payer_acc["name"]
        payee_acc_num = payee_acc["acc_num"]
        payee_acc = accounts.find_one({"number":payee_acc_num})

        sent_msg = get_money_sent_template()
        sent_msg_body = sent_msg.substitute(PAYER_NAME=name.title(), PAYEE_NAME=payee_acc["name"].title(), 
                                            DATE=payer["date"], AMOUNT=str(payer["debits"]), FEES='0',
                                            MODE=payer["mode"])

        rcvd_money = get_money_received_template()
        rvcd_msg_body = sent_msg.substitute(PAYER_NAME=name.title(), PAYEE_NAME=payee_acc["name"].title(), 
                                            DATE=payee["date"], AMOUNT=str(payee["credits"]),
                                            MODE=payee["mode"])

        message = 'Subject: {}\n\n{}'.format("You sent money", sent_msg_body)
        s.sendmail(PROJECT_EMAIL_ID, payer_acc["email"], message)

        message = 'Subject: {}\n\n{}'.format("You received money", rcvd_msg_body)
        s.sendmail(PROJECT_EMAIL_ID, payee_acc["email"], message)


    def sendDepositUpdate(self, deposit):
        accounts = get_accounts_collection(db)
        account = accounts.find_one({"number":deposit["account_number"]})

        msg = get_money_deposit_template()
        msg_body = msg.substitute(DATE=deposit["date"], AMOUNT=str(deposit["credits"]),
                                  MODE=deposit["mode"])

        message = 'Subject: {}\n\n{}'.format("You received money", msg_body)
        s.sendmail(PROJECT_EMAIL_ID, account["email"], message)


    def sendWithdrawUpdate(self, withdraw):
        accounts = get_accounts_collection(db)
        account = accounts.find_one({"number":withdraw["account_number"]})

        msg = get_money_withdraw_template()
        msg_body = msg.substitute(DATE=withdraw["date"], AMOUNT=str(withdraw["debits"]),
                                  MODE=withdraw["mode"])

        message = 'Subject: {}\n\n{}'.format("You withdrew money", msg_body)
        s.sendmail(PROJECT_EMAIL_ID, account["email"], message)
