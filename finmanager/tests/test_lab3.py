import time

from core.domain import Transaction
from core.memo import forecast_expenses


def test_forecast_memoization():
    t1 = Transaction("1", "acc1", "c1", -100, "ts", "n")
    t2 = Transaction("2", "acc1", "c1", -200, "ts", "n")
    trans = (t1, t2)

    # First call - slow
    start = time.perf_counter()
    res1 = forecast_expenses("c1", trans, 1)
    end = time.perf_counter()
    dur1 = end - start

    assert res1 == 150  # (100+200)/2 * 1
    assert dur1 >= 0.1  # Should simulate delay

    # Second call - fast
    start = time.perf_counter()
    res2 = forecast_expenses("c1", trans, 1)
    end = time.perf_counter()
    dur2 = end - start

    assert res2 == 150
    assert dur2 < 0.01  # Should be instant

    # Different args - slow again
    start = time.perf_counter()
    res3 = forecast_expenses("c1", trans, 2)
    end = time.perf_counter()
    dur3 = end - start

    assert res3 == 300  # 150 * 2
    assert dur3 >= 0.1

def test_forecast_empty_transactions():
    # If no transactions match, should return 0
    trans = ()
    start = time.perf_counter()
    res = forecast_expenses("c1", trans, 1)
    end = time.perf_counter()
    
    assert res == 0
    # Even if result is 0, simulate delay applies if not cached
    assert (end - start) >= 0.1

def test_forecast_no_matching_category():
    t1 = Transaction("1", "acc1", "c2", -100, "ts", "n")
    trans = (t1,)
    
    res = forecast_expenses("c1", trans, 1)
    assert res == 0

def test_forecast_only_income_ignored():
    # Forecast logic filters for amount < 0
    t1 = Transaction("1", "acc1", "c1", 100, "ts", "n") # Income
    trans = (t1,)
    
    res = forecast_expenses("c1", trans, 1)
    assert res == 0

def test_forecast_calculation_logic():
    # Verify the math: (100 + 300) / 2 = 200 avg. 200 * 3 periods = 600
    t1 = Transaction("1", "acc1", "c1", -100, "ts", "n")
    t2 = Transaction("2", "acc1", "c1", -300, "ts", "n")
    trans = (t1, t2)
    
    res = forecast_expenses("c1", trans, 3)
    assert res == 600
