from . import config
def plan_queries(budget=None):
    n=min(config.QUERY_BUDGET if budget is None else budget,len(config.KEYWORDS)*len(config.LOCATIONS)); return [(k,l) for k in config.KEYWORDS for l in config.LOCATIONS][:n]
