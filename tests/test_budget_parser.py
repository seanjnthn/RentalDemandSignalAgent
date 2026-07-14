from rdsa.budget_parser import parse_budget


def test_budget_parser_magnitudes_and_localized_numbers():
    assert parse_budget("900 rb").min_amount == 900_000
    assert parse_budget("Rp900rb").max_amount == 900_000
    assert parse_budget("900 ribu").min_amount == 900_000
    assert parse_budget("2 jt").min_amount == 2_000_000
    assert parse_budget("Rp2,5 juta").min_amount == 2_500_000
    result = parse_budget("3-4 juta")
    assert (result.min_amount, result.max_amount) == (3_000_000, 4_000_000)
    yearly = parse_budget("35 juta/tahun")
    assert yearly.original_yearly == 35_000_000
    assert yearly.monthly_min == yearly.monthly_max == 35_000_000 // 12
    assert parse_budget("Rp5.000.000").min_amount == 5_000_000


def test_bare_number_is_ambiguous():
    result = parse_budget("900")
    assert result.confidence == "low"
    assert result.min_amount is None and result.max_amount is None
