from core.domain import Account, Budget, Category, Transaction
from core.ftypes import Either, Maybe
from core.transforms import check_budget, safe_category, validate_transaction


def test_maybe():
    m_some = Maybe.just(10)
    m_none = Maybe.nothing()

    assert m_some.is_present()
    assert not m_none.is_present()

    assert m_some.map(lambda x: x * 2).get_or_else(0) == 20
    assert m_none.map(lambda x: x * 2).get_or_else(0) == 0


def test_either():
    e_right = Either.right(10)
    e_left = Either.left("Error")

    assert e_right.is_right()
    assert e_left.is_left()

    assert e_right.map(lambda x: x + 1).unwrap() == 11
    assert e_left.map(lambda x: x + 1).unwrap() == "Error"


def test_safe_category():
    c1 = Category("c1", "n", None, "t")
    cats = (c1,)

    assert safe_category(cats, "c1").is_present()
    assert not safe_category(cats, "missing").is_present()


def test_validate_transaction():
    acc = Account("a1", "n", 0, "c")
    cat = Category("c1", "n", None, "t")

    t_ok = Transaction("t1", "a1", "c1", 100, "ts", "n")
    t_bad_acc = Transaction("t2", "miss", "c1", 100, "ts", "n")
    t_bad_cat = Transaction("t3", "a1", "miss", 100, "ts", "n")

    res_ok = validate_transaction(t_ok, (acc,), (cat,))
    assert res_ok.is_right()

    res_bad_acc = validate_transaction(t_bad_acc, (acc,), (cat,))
    assert res_bad_acc.is_left()
    assert "Account" in res_bad_acc.unwrap()["error"]

    res_bad_cat = validate_transaction(t_bad_cat, (acc,), (cat,))
    assert res_bad_cat.is_left()
    assert "Category" in res_bad_cat.unwrap()["error"]


def test_check_budget():
    b = Budget("b1", "c1", 100, "month")
    t1 = Transaction("t1", "a1", "c1", -60, "ts", "n")
    t2 = Transaction("t2", "a1", "c1", -50, "ts", "n")

    # Total -60. Abs(60) <= 100. OK.
    res1 = check_budget(b, (t1,))
    assert res1.is_right()

    # Total -110. Abs(110) > 100. Fail.
    res2 = check_budget(b, (t1, t2))
    assert res2.is_left()
    assert res2.unwrap()["limit"] == 100
    assert res2.unwrap()["spent"] == 110
