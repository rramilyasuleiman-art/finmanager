from core.domain import Category, Transaction
from core.lazy import iter_transactions, lazy_top_categories


def test_iter_transactions():
    t1 = Transaction("t1", "a", "c1", -10, "ts", "n")
    t2 = Transaction("t2", "a", "c2", -20, "ts", "n")
    trans = (t1, t2)

    # Test iteration
    it = iter_transactions(trans)
    assert next(it) == t1
    assert next(it) == t2

    # Test filtering
    it_filter = iter_transactions(trans, lambda t: t.amount == -20)
    assert next(it_filter) == t2
    try:
        next(it_filter)
        assert False
    except StopIteration:
        assert True


def test_lazy_top_categories():
    c1 = Category("c1", "Food", None, "expense")
    c2 = Category("c2", "Transport", None, "expense")
    cats = (c1, c2)

    t1 = Transaction("t1", "a", "c1", -100, "ts", "n")
    t2 = Transaction("t2", "a", "c1", -50, "ts", "n")
    t3 = Transaction("t3", "a", "c2", -80, "ts", "n")
    trans = (t1, t2, t3)

    # c1 total: 150, c2 total: 80

    gen = lazy_top_categories(trans, cats, 2)
    res = list(gen)

    assert len(res) == 2
    assert res[0] == ("Food", 150)
    assert res[1] == ("Transport", 80)

    gen_top1 = lazy_top_categories(trans, cats, 1)
    res_top1 = list(gen_top1)
    assert len(res_top1) == 1
    assert res_top1[0] == ("Food", 150)

def test_iter_transactions_empty():
    trans = ()
    it = iter_transactions(trans)
    # Should be empty
    try:
        next(it)
        assert False
    except StopIteration:
        assert True

def test_iter_transactions_no_match():
    t1 = Transaction("t1", "a", "c1", -10, "ts", "n")
    trans = (t1,)
    it = iter_transactions(trans, lambda t: t.amount == 999)
    # Should be empty
    try:
        next(it)
        assert False
    except StopIteration:
        assert True

def test_lazy_top_categories_ignore_income():
    # lazy_top_categories logic says: if t.amount < 0 ...
    c1 = Category("c1", "IncomeCat", None, "income")
    cats = (c1,)
    
    t1 = Transaction("t1", "a", "c1", 100, "ts", "n") # Positive amount
    trans = (t1,)
    
    gen = lazy_top_categories(trans, cats, 1)
    res = list(gen)
    
    # No expenses, so result should be empty or have 0 if implementation handles it?
    # Implementation: expenses = defaultdict(int); if t.amount < 0 ...
    # So expenses will be empty.
    assert len(res) == 0
