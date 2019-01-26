from __future__ import print_function
import time
import ynab
import api_settings
import datetime
from ynab.rest import ApiException
from pprint import pprint
from  Helpers import create_authenticated_http_session,get_accounts,get_transactions,getTransactionDate,getPayee,getMemo, getOut, getIn,getIntAmountMilli,getYnabTransactionDate,get_transactions_period,getYnabSyncId


def findMatchingTransfer(original_account, transaction, accounts_transactions_list, accounts):
    compare = transaction.copy()
    compare['amount'] = transaction['amount'] * -1
    for account_idx in range(len(accounts)):
        if accounts[account_idx]['ID'] != original_account:
            for t in accounts_transactions_list[account_idx]:
                if getYnabSyncId(t) == getYnabSyncId(compare):
                    d = {}
                    d['Name'] = accounts[account_idx]['Name']
                    d['Account'] = accounts[account_idx]['account']
                    return d

# Configure API key authorization: bearer
configuration = ynab.Configuration()
configuration.api_key['Authorization'] = api_settings.api_key
configuration.api_key_prefix['Authorization'] = 'Bearer'

# create an instance of the API class
api_instance = ynab.TransactionsApi(ynab.ApiClient(configuration))

#SBanken auth
http_session = create_authenticated_http_session(api_settings.CLIENTID, api_settings.SECRET)
today = datetime.date.today()
endDate = today - datetime.timedelta(1)
startDate = today - datetime.timedelta(6)   # Last 5 days

accounts = []
for mapping in api_settings.mapping:
    accounts.append(get_transactions_period(
        http_session, 
        api_settings.CUSTOMERID,
        mapping['ID'],
        startDate,
        endDate))


for account_idx in range(len(accounts)):
    transactions = accounts[account_idx]
    account_map = api_settings.mapping[account_idx]
    ynab_transactions = []

    for item in transactions:
        payee_id = None
        payee_name = getPayee(item)
        transaction = ynab.TransactionDetail(
            date=getYnabTransactionDate(item), 
            amount=getIntAmountMilli(item), 
            cleared='uncleared', 
            approved=False, 
            account_id=account_map['account'],
            memo=getMemo(item),
            import_id=getYnabSyncId(item)
        )
        transaction.payee_name = payee_name

        if item['transactionTypeCode'] == 200: # Transfer between own accounts
            payee = findMatchingTransfer(account_map['ID'], item, accounts, api_settings.mapping)
            if payee != None:
                payee_id = payee['Account']
                payee_id if payee_id != '' else None
                payee_name = payee['Name'] if payee_id == None else None
                transaction.memo += ': '+payee['Name']
                transaction.payee_name = 'Transfer '
                if transaction.amount > 0:
                    transaction.payee_name += 'from: '
                else:
                    transaction.payee_name += 'to: '

                transaction.payee_name += payee['Name']

        if len(account_map['account']) > 2:
            ynab_transactions.append(transaction)

    if len(ynab_transactions) > 0:

        try:
            # Create new transaction
            api_response = api_instance.create_transaction(api_settings.budget_id, {"transactions":ynab_transactions})
        except ApiException as e:
            print("Exception when calling TransactionsApi->create_transaction: %s\n" % e)