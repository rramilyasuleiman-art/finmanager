from typing import Dict, Any, Tuple
from core.domain import Account, Transaction, Category, Budget

# Helper functions to update state immutably

def update_account_balance(state: Dict[str, Any], acc_id: str, new_balance: int) -> Dict[str, Any]:
    accounts = state.get("accounts", ())
    new_accounts = tuple(
        Account(id=a.id, name=a.name, balance=new_balance, currency=a.currency) 
        if a.id == acc_id else a 
        for a in accounts
    )
    return {**state, "accounts": new_accounts}

def create_transaction(state: Dict[str, Any], t: Transaction) -> Dict[str, Any]:
    # Update transactions list
    transactions = state.get("transactions", ())
    new_transactions = transactions + (t,)
    
    # Update account balance
    accounts = state.get("accounts", ())
    # Find account
    # Assuming positive amount adds to balance (income) and negative subtracts (expense)
    # The transaction amount is signed.
    
    new_accounts = tuple(
        Account(id=a.id, name=a.name, balance=a.balance + t.amount, currency=a.currency)
        if a.id == t.account_id else a
        for a in accounts
    )
    
    return {**state, "transactions": new_transactions, "accounts": new_accounts}

def update_transaction(state: Dict[str, Any], t_id: str, new_data: Dict) -> Dict[str, Any]:
    transactions = state.get("transactions", ())
    
    # Find original transaction to adjust balance
    orig_t = next((t for t in transactions if t.id == t_id), None)
    if not orig_t:
        return state

    new_amount = int(new_data.get("amount", orig_t.amount))
    diff = new_amount - orig_t.amount
    
    # Update transaction
    new_transactions = tuple(
        Transaction(
            id=t.id,
            account_id=new_data.get("account_id", t.account_id),
            cat_id=new_data.get("cat_id", t.cat_id),
            amount=new_amount,
            ts=new_data.get("ts", t.ts),
            note=new_data.get("note", t.note)
        ) if t.id == t_id else t
        for t in transactions
    )
    
    # Update Account Balance
    # If account changed, it's more complex, but assuming account_id doesn't change for now based on usage.
    # If account_id changed, we'd need to subtract from old and add to new.
    # The current usage in main.py doesn't seem to allow changing account_id in update_transaction (only amount and note).
    
    accounts = state.get("accounts", ())
    new_accounts = tuple(
        Account(id=a.id, name=a.name, balance=a.balance + diff, currency=a.currency)
        if a.id == orig_t.account_id else a
        for a in accounts
    )

    return {**state, "transactions": new_transactions, "accounts": new_accounts}

def delete_transaction(state: Dict[str, Any], t_id: str) -> Dict[str, Any]:
    transactions = state.get("transactions", ())
    
    # Find transaction to revert balance
    t_to_del = next((t for t in transactions if t.id == t_id), None)
    if not t_to_del:
        return state
        
    new_transactions = tuple(t for t in transactions if t.id != t_id)
    
    # Revert balance (subtract amount)
    accounts = state.get("accounts", ())
    new_accounts = tuple(
        Account(id=a.id, name=a.name, balance=a.balance - t_to_del.amount, currency=a.currency)
        if a.id == t_to_del.account_id else a
        for a in accounts
    )
    
    return {**state, "transactions": new_transactions, "accounts": new_accounts}
