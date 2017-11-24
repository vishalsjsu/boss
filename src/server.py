#!/home/vishal/anaconda2/bin/python2.7

import socket
import json
import sys
import getopt
import uuid
import datetime

from thread import *
from constants import *
from logger import get_logger

sys.path.append(CONFIG_FILE_PATH)
from config import *
from utils import *

log = get_logger(logFileName="socketServer.log")

mongoConection = get_mongo_connection()

def passiveTCP(port):
    sock = socket.socket()
    sock.bind(("0.0.0.0",port))
    sock.listen(10)

    return sock


def main():
    try:
        optlist, args = getopt.getopt(sys.argv[1:], "p:")
    except getopt.GetoptError as err:
        log.error(str(err))
        usage()
        sys.exit(-1)

    port = SERVER_PORT
    for opt, arg in optlist:
        if opt == '-p':
            port = int(arg)

    sock = passiveTCP(port)
    while True:
        con, addr = sock.accept()
        start_new_thread(handleClient,(con,))


def usage():
    log.info('/server.py -p port')


def get_account_smmary(request):
    if "username" in request:
        return get_account_summary_by_username(request["username"])
    if "account_number" in request:
        return get_account_summary_by_account_number(request["account_number"])


def create_new_account(request):
    msg = {}
    if request["user_type"] == USER_TYPE_TELLER:
        user = create_teller_account(request["name"], request["email"])
    if request["user_type"] == USER_TYPE_CUSTOMER:
        account, user = create_customer_account(request["account_type"], request)

    msg["result"] = 'success'
    return msg


def delete_account(request):
    username = request.get("username")
    account = get_account_details_by_username(username)
    if not username_exists(username):
        raise Exception("User account does not exist!")

    delete_bank_acccount_by_username(username)
    delete_user_acccount_by_username(username)


def freeze_account(request):
    username = request.get("username")
    account = get_account_details_by_username(username)
    if not username_exists(username):
        raise Exception("User account does not exist!")

    put_account_on_hold_by_username(username)


def reactivate_account(request):
    username = request.get("username")
    account = get_account_details_by_username(username)
    if not username_exists(username):
        raise Exception("User account does not exist!")

    reactivate_account_by_username(username)


def validate_funds_transfer(request):
    msg = {}

    username = request.get("username")
    payer_acc = get_account_details_by_username(username)

    payee_acc_num = request["account_number"]
    payee_acc = get_account_details_by_account_number(payee_acc_num)

    amount = request["amount"]

    if not username_exists(username):
        raise Exception("User account does not exist!")

    payer_account_type = payer_acc["type"]
    payee_account_type = payee_acc["type"]
    if not payee_acc:
        msg["errmsg"] = 'Invalid Payee account number'
        msg["result"] = 'failed'
        return msg

    if payer_account_type == ACCOUNT_TYPE_DEPOSIT or payee_account_type == ACCOUNT_TYPE_DEPOSIT:
        msg["errmsg"] = 'Transfer not allowed to/from deposit account'
        msg["result"] = 'failed'
        return msg

    if is_account_on_hold(username):
        msg["errmsg"] = 'Account put on hold'
        msg["result"] = 'failed'
        return msg

    if get_account_balance(payer_acc["number"]) < amount:
        msg["errmsg"] = 'Insufficient funds'
        msg["result"] = 'failed'
        return msg

    if exceeds_daily_transfer_limit(account_type, amount):
        msg["errmsg"] = 'This transaction exceeds daily transaction limit'
        msg["result"] = 'failed'
        return msg

    msg["result"] = 'passed'
    return msg


def transfer(request):
    msg = {}

    username = request.get("username")
    payer_acc = get_account_details_by_username(username)
    payee_acc = get_account_details_by_account_number(request["account_number"])
    amount = request["amount"]

    validation = validate_funds_transfer(request)
    if validation["result"] != 'passed':
        return validation

    log.debug("Transfering $%d from %d to %d"%(payer_acc["number"], payee_acc["number"]))
    transaction = {}
    transaction["account_number"] = payer_acc["number"]
    transaction["type"] = TRANSACTION_TYPE_TRANSFER
    transaction["credits"] = 0
    transaction["debits"] = amount
    transaction["date"] = datetime.datetime.today().strftime("%m/%d/%y")
    transaction["mode"] = "Online Transfer"
    add_transaction_to_db(transaction)

    transaction["account_number"] = payee_acc["number"]
    transaction["type"] = TRANSACTION_TYPE_TRANSFER
    transaction["credits"] = amount
    transaction["debits"] = 0
    transaction["mode"] = "Online Transfer"
    add_transaction_to_db(transaction)

    payee_new_balance = payee_acc["balance"] + amount
    payer_new_balance = payer_acc["balance"] - amount

    update_account_balance(payee_acc["number"], payee_new_balance)
    update_account_balance(payer_acc["number"], payer_new_balance)

    log.debug("Transfered $%d from %d to %d"%(payer_acc["number"], payee_acc["number"]))
    msg["result"] = 'passed'
    msg["errmsg"] = 'Transfer Complete!'
    return msg


def validate_deposit_or_withdraw(request):
    msg = {}

    username = request.get("username")
    account = get_account_details_by_username(username)
    amount = request["amount"]

    if not username_exists(username):
        raise Exception("User account does not exist!")

    if not account:
        msg["errmsg"] = 'Invalid account number'
        msg["result"] = 'failed'
        return msg

    account_type = account["type"]
    if account_type == ACCOUNT_TYPE_DEPOSIT:
        msg["errmsg"] = 'Transfer not allowed to/from deposit account'
        msg["result"] = 'failed'
        return msg

    if is_account_on_hold(username):
        msg["errmsg"] = 'Account put on hold'
        msg["result"] = 'failed'
        return msg

    if exceeds_daily_transfer_limit(account_type, amount):
        msg["errmsg"] = 'This transaction exceeds daily transaction limit'
        msg["result"] = 'failed'
        return msg

    msg["result"] = 'passed'
    return msg


def deposit(request):
    msg = {}
    acc_num = request.get("account_number")
    account = get_account_details_by_account_number(acc_num)
    amount = request["amount"]

    validation = validate_deposit_or_withdraw(request)
    if validation["result"] != 'passed':
        return validation

    transaction = {}
    transaction["account_number"] = acc_num
    transaction["type"] = TRANSACTION_TYPE_DEPOSIT
    transaction["credits"] = amount
    transaction["debits"] = 0
    transaction["date"] = datetime.datetime.today().strftime("%m/%d/%y")
    transaction["mode"] = "Cash Deposit"
    add_transaction_to_db(transaction)

    new_balance = account["balance"] + amount
    update_account_balance(acc_num, new_balance)

    msg["result"] = 'passed'
    msg["errmsg"] = 'Deposit Complete!'
    return msg


def withdraw(request):
    msg = {}
    acc_num = request.get("account_number")
    account = get_account_details_by_account_number(acc_num)
    amount = request["amount"]

    validation = validate_deposit_or_withdraw(request)
    if validation["result"] != 'passed':
        return validation

    if get_account_balance(acc_num) < amount:
        msg["errmsg"] = 'Insufficient funds'
        msg["result"] = 'failed'
        return msg

    transaction = {}
    transaction["account_number"] = acc_num
    transaction["type"] = TRANSACTION_TYPE_WITHDRAW
    transaction["credits"] = 0
    transaction["debits"] = amount
    transaction["date"] = datetime.datetime.today().strftime("%m/%d/%y")
    transaction["mode"] = "Cash Withdraw"
    add_transaction_to_db(transaction)

    new_balance = account["balance"] - amount
    update_account_balance(acc_num, new_balance)

    msg["result"] = 'passed'
    msg["errmsg"] = 'Withdraw Complete!'
    return msg


def handleClient(con):
    request = get_data_from_peer(con)
    if not request:
        print "get request failed!"

    cmd = request.get('cmd')
    if cmd == CMD_CREATE_ACCOUNT:
        response = create_account(request)
    elif cmd == CMD_DELETE_ACCOUNT:
        response = delete_account(request)
    elif cmd == CMD_FREEZE_ACCOUNT:
        response == freeze_account(request)
    elif cmd == CMD_REACTIVATE_ACCOUNT:
        response == reactivate_account(request)
    elif cmd == CMD_GET_ACCOUNT_SUMMARY:
        response = get_account_summary(request)
    elif cmd == CMD_TRANSFER_FUNDS:
        response = transfer(request)
    elif cmd == CMD_DEPOSIT_FUNDS:
        response = deposit(request)
    elif cmd == CMD_WITHDRAW_FUNDS:
        response = withdraw(request)

    if response:
        send_data_to_peer(con, response)


if __name__ == '__main__':
    main()
