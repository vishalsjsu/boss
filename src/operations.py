import random
import string

from utils import *

mongo_con = get_mongo_connection()
db = get_banking_db(mongo_con)

def account_number_exists(acc_num):
    accounts = get_accounts_collection(db)
    return bool(accounts.find_one({"number":acc_num}))


def username_exists(username):
    users = get_users_collection(db)
    return bool(users.find_one({"username":username}))


def exceeds_daily_transfer_limit(account_type, amount):
    if account_type == ACCOUNT_TYPE_SAVINGS:
        if amount > SAVINGS_DAILY_TRANSFER_LIMIT:
            return True
    if account_type == ACCOUNT_TYPE_CHECKING:
        if amount > CHECKING_DAILY_TRANSFER_LIMIT:
            return True

    return False


def get_account_balance(acc_number):
    accounts = get_accounts_collection(db)
    account = accounts.find_one({"number":acc_number})
    return account["balance"]


def get_account_details_by_username(username):
    accounts = get_accounts_collection(db)
    return accounts.find_one({"username":username})


def delete_bank_acccount_by_username(username):
    accounts = get_accounts_collection(db)
    accounts.remove({"username":username})


def delete_user_acccount_by_username(username):
    users = get_users_collection(db)
    users.remove({"username":username})


def put_account_on_hold_by_username(username):
    accounts = get_accounts_collection(db)
    accounts.update({"username":username},{"$set":{"hold":True}})


def reactivate_account_by_username(username):
    accounts = get_accounts_collection(db)
    accounts.update({"username":username, "hold":True},{"$set":{"hold":False}})


def is_account_on_hold(username):
    accounts = get_accounts_collection(db)
    account =  accounts.find_one({"username":username})
    return account.get("hold",False)


def get_account_details_by_account_number(account_number):
    accounts = get_accounts_collection(db)
    return accounts.find_one({"number":account_number})


def insert_bank_account_into_database(account):
    accounts = get_accounts_collection(db)
    accounts.insert(account)


def insert_user_account_into_database(user):
    users = get_users_collection(db)
    users.insert(user)


def insert_employee_account_into_database(employee):
    employees = get_employees_collection(db)
    employees.insert(employee)


def add_transaction_to_db(transaction):
    transactions = get_transactions_collection(db)
    transactions.insert(transaction)


def update_account_balance(acc_num, new_bal):
    accounts = get_accounts_collection(db)
    accounts.update({"number":acc_num},{"$set":{"balance":new_bal}})


def create_customer_account(account_type, details):
    account = {}
    user = {}

    acc_num = generate_account_number()
    username = generate_username()
    password = generate_password()

    account["name"] = details["name"]
    account["email"] = details["email"]
    account["ssn"] = details["ssn"]
    account["type"] = account_type
    account["username"] = username
    account["password"] = password
    account["number"] = acc_num
    
    user["username"] = username
    user["password"] = password
    user["type"] = USER_TYPE_CUSTOMER

    insert_user_account_into_database(user)
    insert_bank_account_into_database(account)
    return account, user


def create_teller_account(name, email):
    user = {}
    employee = {}

    username = generate_username()
    password = generate_password()
    employee_id = generate_employee_id()

    employee["name"] = name
    employee["email"] = email
    employee["username"] = username
    employee["employee_id"] = int(employee_id)

    user["username"] = username
    user["password"] = password
    user["type"] = USER_TYPE_TELLER

    insert_user_account_into_database(user)
    insert_employee_account_into_database(employee)
    return user


def generate_account_number():
    '''Generate random 10 digit account number, always starting with 578.
       The first account number created will be 5780000001.'''

    acc_num = 5780000001
    while account_number_exists(acc_num):
        acc_num = random.randint(5780000001, 5789999999)

    return acc_num


def generate_username():
    '''Generate random alphanumeric username.'''

    username = ''
    while True:
        for i in range(USERNAME_MIN_LENGTH):
            username += random.choice(string.lowrcase + string.uppercase + string.digits)

        if not username_exists(username):
            return username


def generate_password():
    '''Generate random password having alphabets, numbers and special characters.'''

    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(chars) for _ in range(PASSWORD_MIN_LENGTH))


def generate_employee_id():
    now = datetime.datetim.today()
    employees = get_employees_collection(db)
    last = employees.find_one(sort=[("employee_id", pymongo.DESCENDING)])
    if not last:
        new_id = "001"
    else:
        str_len = len(str(last["employee_id"]))
        new_id = (3 - str_len) * "0" + str(last["employee_id"])

    employee_id = str(now.year) + new_id
    return employee_id


def get_account_summary_by_username(username):
    summary = {}
    account = get_account_details_by_username(username)
    if not account:
        raise Exception("Account details not available!")

    summary["account_number"] = account["number"]
    summary["account_type"] = account["type"]
    summary["account_balance"] = account["balance"]
    summary["account_holder_name"] = account["holder_name"]
    return summary

def get_account_summary_by_account_number(account_number):
    summary = {}
    account = get_account_details_by_account_number(account_number)
    if not account:
        raise Exception("Account details not available!")

    summary["account_number"] = account["number"]
    summary["account_type"] = account["type"]
    summary["account_balance"] = account["balance"]
    summary["account_holder_name"] = account["holder_name"]
    return summary
