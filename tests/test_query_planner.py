from rdsa import config
from rdsa.query_planner import plan_queries


def test_query_budget_and_uniqueness(monkeypatch):
    monkeypatch.setattr(config, "QUERY_BUDGET", 5)
    queries = plan_queries()
    assert len(queries) <= 5
    assert len(queries) == len(set(queries))
