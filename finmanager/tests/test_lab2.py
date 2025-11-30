from core.domain import Category, Transaction
from core.recursion import flatten_categories, sum_expenses_recursive
from core.transforms import by_amount_range, by_category, by_date_range


def test_filters():
    t1 = Transaction("1", "acc1", "c1", 100, "2023-01-01", "test")
    t2 = Transaction("2", "acc1", "c2", -50, "2023-01-02", "test")

    # by_category
    f_cat = by_category("c1")
    assert f_cat(t1) is True
    assert f_cat(t2) is False

    # by_date_range
    f_date = by_date_range("2023-01-01", "2023-01-01")
    assert f_date(t1) is True
    assert f_date(t2) is False

    # by_amount_range
    f_amt = by_amount_range(40, 60)
    assert f_amt(t1) is False
    assert f_amt(t2) is True


def test_recursion_flatten():
    c1 = Category("c1", "Root", None, "expense")
    c2 = Category("c2", "Child", "c1", "expense")
    c3 = Category("c3", "Grandchild", "c2", "expense")
    c4 = Category("c4", "Other", None, "expense")

    cats = (c1, c2, c3, c4)

    flat = flatten_categories(cats, "c1")
    # Should be c1, c2, c3 in some order
    ids = [c.id for c in flat]
    assert "c1" in ids
    assert "c2" in ids
    assert "c3" in ids
    assert "c4" not in ids
    assert len(flat) == 3


def test_recursion_sum():
    c1 = Category("c1", "Root", None, "expense")
    c2 = Category("c2", "Child", "c1", "expense")
    cats = (c1, c2)

    t1 = Transaction("1", "a", "c1", -100, "ts", "n")
    t2 = Transaction("2", "a", "c2", -50, "ts", "n")
    trans = (t1, t2)

    # Sum for c1 should include c1 (-100) and c2 (-50) = -150
    assert sum_expenses_recursive(cats, trans, "c1") == -150
    # Sum for c2 should include only c2 = -50
    assert sum_expenses_recursive(cats, trans, "c2") == -50

def test_recursion_flatten_empty():
    # Test flattening when category has no children
    c1 = Category("c1", "Root", None, "expense")
    cats = (c1,)
    flat = flatten_categories(cats, "c1")
    assert len(flat) == 1
    assert flat[0].id == "c1"

def test_recursion_sum_no_match():
    # Test recursive sum when no transactions match
    c1 = Category("c1", "Root", None, "expense")
    cats = (c1,)
    t1 = Transaction("1", "a", "c2", -100, "ts", "n") # Different category
    trans = (t1,)
    
    # Should be 0
    assert sum_expenses_recursive(cats, trans, "c1") == 0
