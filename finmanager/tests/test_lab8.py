import pytest
import asyncio
from core.domain import Transaction
from core.service import ReportService


@pytest.mark.asyncio
async def test_async_expenses_by_month():
    rs = ReportService({})

    t1 = Transaction("t1", "a", "c", -100, "2023-01-01", "n")
    t2 = Transaction("t2", "a", "c", -200, "2023-01-02", "n")
    t3 = Transaction("t3", "a", "c", -50, "2023-02-01", "n")

    trans = [t1, t2, t3]
    months = ["2023-01", "2023-02", "2023-03"]

    res = await rs.expenses_by_month(trans, months)

    assert res["2023-01"] == 300
    assert res["2023-02"] == 50
    assert res["2023-03"] == 0

@pytest.mark.asyncio
async def test_async_empty_transactions():
    rs = ReportService({})
    trans = []
    months = ["2023-01"]
    res = await rs.expenses_by_month(trans, months)
    assert res["2023-01"] == 0

@pytest.mark.asyncio
async def test_async_no_matching_months():
    rs = ReportService({})
    t1 = Transaction("t1", "a", "c", -100, "2023-05-01", "n")
    trans = [t1]
    months = ["2023-01"]
    res = await rs.expenses_by_month(trans, months)
    assert res["2023-01"] == 0

@pytest.mark.asyncio
async def test_async_concurrent_timing():
    # Verify that tasks effectively run properly (hard to test exact concurrency without mocking sleep, 
    # but can verify result correctness with multiple items)
    rs = ReportService({})
    t1 = Transaction("t1", "a", "c", -100, "2023-01-01", "n")
    t2 = Transaction("t2", "a", "c", -100, "2023-01-01", "n")
    trans = [t1, t2]
    months = ["2023-01"] * 10 # Same month queried multiple times
    
    start = asyncio.get_running_loop().time()
    res = await rs.expenses_by_month(trans, months)
    end = asyncio.get_running_loop().time()
    
    # Should be correct for all
    assert len(res) == 1 # Dictionary deduplicates keys
    assert res["2023-01"] == 200

@pytest.mark.asyncio
async def test_async_ignore_income():
    rs = ReportService({})
    t1 = Transaction("t1", "a", "c", 100, "2023-01-01", "n") # Income
    trans = [t1]
    months = ["2023-01"]
    res = await rs.expenses_by_month(trans, months)
    assert res["2023-01"] == 0
