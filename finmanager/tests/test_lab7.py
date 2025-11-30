from core.compose import compose, pipe
from core.domain import Budget, Transaction
from core.service import BudgetService, ReportService


def test_compose():
    def f(x):
        return x + 1
    def g(x):
        return x * 2
    # compose(f, g)(x) = f(g(x)) = (x*2) + 1
    h = compose(f, g)
    assert h(3) == 7


def test_pipe():
    def f(x):
        return x + 1
    def g(x):
        return x * 2
    # pipe(x, f, g) = g(f(x)) = (x+1)*2
    assert pipe(3, f, g) == 8


def test_budget_service():
    bs = BudgetService([], [])
    b = Budget("b1", "c1", 100, "m")
    t = Transaction("t1", "a1", "c1", -50, "ts", "n")

    rep = bs.monthly_report((b,), (t,))
    assert rep["b1"]["spent"] == 50
    assert rep["b1"]["status"] == "OK"

    t2 = Transaction("t2", "a1", "c1", -60, "ts", "n")
    rep2 = bs.monthly_report((b,), (t, t2))
    assert rep2["b1"]["spent"] == 110
    assert rep2["b1"]["status"] == "OVER"


def test_report_service():
    rs = ReportService({})
    t1 = Transaction("t1", "a", "c1", -10, "ts", "n")
    t2 = Transaction("t2", "a", "c1", -20, "ts", "n")

    rep = rs.category_report("c1", (t1, t2))
    assert rep["total_expense"] == 30
    assert rep["transaction_count"] == 2

def test_compose_empty():
    # Compose with one function
    def f(x): return x * 2
    h = compose(f)
    assert h(5) == 10
    
    # Ideally compose with no functions acts as identity, but implementation uses reduce without initializer or with?
    # Let's check implementation of compose in core/compose.py
    # from functools import reduce
    # def compose(*funcs):
    #     return lambda x: reduce(lambda v, f: f(v), reversed(funcs), x)
    # If funcs is empty, reduce(..., [], x) -> x (if initial provided) or error?
    # reduce(lambda v, f: f(v), [], x) -> x
    
    h_empty = compose()
    assert h_empty(5) == 5
