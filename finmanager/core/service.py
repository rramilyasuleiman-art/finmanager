import asyncio

from typing import Any, Callable, Dict, List, Tuple

from core.domain import Budget, Transaction, Account


class BudgetService:
    def __init__(self, validators: List[Callable], calculators: List[Callable]):
        self.validators = validators
        self.calculators = calculators

    def monthly_report(
        self, budgets: tuple[Budget, ...], trans: tuple[Transaction, ...]
    ) -> Dict[str, Any]:
        """
        Calculates status for each budget.
        Using composition if applicable, or just pure logic.
        """
        report = {}
        for b in budgets:
            # Simple logic: filter trans for budget category -> sum
            spent = sum(
                abs(t.amount) for t in trans if t.cat_id == b.cat_id and t.amount < 0
            )
            status = "OK" if spent <= b.limit else "OVER"
            report[b.id] = {"limit": b.limit, "spent": spent, "status": status}
        return report

class ReportService:
    def __init__(self, aggregators: Dict[str, Callable]):
        self.aggregators = aggregators

    def category_report(
        self, cat_id: str, trans: Tuple["Transaction", ...]
    ) -> Dict[str, Any]:
        """
        Aggregates data for a category.
        """
        # Фильтруем расходы (amount < 0) по категории
        filtered = [t for t in trans if t.cat_id == cat_id and t.amount < 0]
        total = sum(abs(t.amount) for t in filtered)
        count = len(filtered)

        return {"cat_id": cat_id, "total_expense": total, "transaction_count": count}

    async def expenses_by_month(
        self, trans: List["Transaction"], months: List[str]
    ) -> Dict[str, int]:
        
        async def calc_month(m: str) -> int:
            # Имитация асинхронной работы
            await asyncio.sleep(0.01)
            # Суммируем расходы, где дата (строка) начинается с месяца m
            return sum(
                abs(t.amount) for t in trans if t.ts.startswith(m) and t.amount < 0
            )

        tasks = [calc_month(m) for m in months]
        results = await asyncio.gather(*tasks)

        return dict(zip(months, results))
    
    async def balance_forecast(
        self, accounts: List["Account"], trans: List["Transaction"]
    ) -> Dict[str, int]:
        
        await asyncio.sleep(0.01)

        # Берем текущие балансы. 
        balances = {a.id: a.balance for a in accounts}

        # Применяем транзакции 
        for t in trans:
            if t.account_id in balances:
                balances[t.account_id] += t.amount
        
        return balances
   