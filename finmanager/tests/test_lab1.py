import pytest

from core.domain import Account, Budget, Transaction
from core.transforms import account_balance, add_transaction, load_seed, update_budget


def test_load_seed():
    accs, cats, trans, buds = load_seed("data/seed.json")
    assert len(accs) >= 3
    assert len(cats) >= 10
    assert len(trans) >= 100
    assert len(buds) >= 3
    assert isinstance(accs[0], Account)


def test_add_transaction():
    t_list = (Transaction("1", "acc1", "c1", 100, "2023-01-01", "test"),)
    new_t = Transaction("2", "acc1", "c1", 200, "2023-01-02", "test2")

    updated = add_transaction(t_list, new_t)
    assert len(updated) == 2
    assert updated[1] == new_t
    assert t_list  # Original should be unchanged


def test_update_budget():
    b1 = Budget("b1", "c1", 1000, "month")
    b2 = Budget("b2", "c2", 2000, "month")
    budgets = (b1, b2)

    updated = update_budget(budgets, "b1", 1500)
    assert len(updated) == 2
    assert updated[0].limit == 1500
    assert updated[1].limit == 2000  # Unchanged
    assert budgets[0].limit == 1000  # Original unchanged


def test_account_balance():
    t1 = Transaction("1", "acc1", "c1", 100, "2023-01-01", "test")
    t2 = Transaction("2", "acc1", "c1", -50, "2023-01-02", "test")
    t3 = Transaction("3", "acc2", "c1", 500, "2023-01-03", "test")  # Different account

    trans = (t1, t2, t3)

    assert account_balance(trans, "acc1") == 50
    assert account_balance(trans, "acc2") == 500
    assert account_balance(trans, "acc3") == 0


def test_immutability():
    # Verify that we can't change fields (basic check for Frozen dataclass)
    acc = Account("1", "Test", 100, "USD")
    with pytest.raises(Exception):  # FrozenInstanceError
        acc.balance = 200
