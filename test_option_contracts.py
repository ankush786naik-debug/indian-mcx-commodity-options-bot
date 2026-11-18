import pytest

from option_contracts import OptionContracts


SAMPLE_CONTRACTS = [
    {
        "instrument_type": "CE",
        "instrument_key": "MCX_FO|GOLD_CE_70000",
        "expiry": "2026-12-31",
        "strike_price": 70000,
        "lot_size": 100,
    },
    {
        "instrument_type": "PE",
        "instrument_key": "MCX_FO|GOLD_PE_70000",
        "expiry": "2026-12-31",
        "strike_price": 70000,
        "lot_size": 100,
    },
    {
        "instrument_type": "CE",
        "instrument_key": "MCX_FO|GOLD_CE_71000",
        "expiry": "2026-12-31",
        "strike_price": 71000,
        "lot_size": 100,
    },
]


def test_select_call_contract():
    selector = OptionContracts()

    result = selector.select_contract(
        SAMPLE_CONTRACTS,
        "CE",
        70500,
    )

    assert result is not None
    assert result["instrument_type"] == "CE"


def test_select_put_contract():
    selector = OptionContracts()

    result = selector.select_contract(
        SAMPLE_CONTRACTS,
        "PE",
        70500,
    )

    assert result is not None
    assert result["instrument_type"] == "PE"


def test_invalid_option_type():
    selector = OptionContracts()

    with pytest.raises(ValueError):
        selector.select_contract(
            SAMPLE_CONTRACTS,
            "FUT",
            70500,
        )


def test_invalid_underlying_price():
    selector = OptionContracts()

    with pytest.raises(ValueError):
        selector.select_contract(
            SAMPLE_CONTRACTS,
            "CE",
            0,
        )


def test_no_matching_contract():
    selector = OptionContracts()

    result = selector.select_contract(
        SAMPLE_CONTRACTS,
        "PE",
        70500,
        expiry_date="2027-12-31",
    )

    assert result is None
  
