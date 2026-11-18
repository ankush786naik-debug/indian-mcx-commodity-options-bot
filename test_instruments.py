
from instruments import InstrumentMaster


SAMPLE_INSTRUMENTS = [
    {
        "segment": "MCX_FO",
        "trading_symbol": "GOLD FUT",
        "name": "GOLD",
        "instrument_type": "FUT",
        "instrument_key": "MCX_FO|GOLD_FUT",
    },
    {
        "segment": "MCX_FO",
        "trading_symbol": "GOLD 70000 CE",
        "name": "GOLD",
        "instrument_type": "CE",
        "instrument_key": "MCX_FO|GOLD_CE",
    },
    {
        "segment": "MCX_FO",
        "trading_symbol": "GOLD 70000 PE",
        "name": "GOLD",
        "instrument_type": "PE",
        "instrument_key": "MCX_FO|GOLD_PE",
    },
    {
        "segment": "NSE_FO",
        "trading_symbol": "NIFTY CE",
        "name": "NIFTY",
        "instrument_type": "CE",
        "instrument_key": "NSE_FO|NIFTY_CE",
    },
]


def test_mcx_filter():
    master = InstrumentMaster()
    master.instruments = SAMPLE_INSTRUMENTS

    results = master.get_mcx_instruments()

    assert len(results) == 3
    assert all(x["segment"] == "MCX_FO" for x in results)


def test_gold_search():
    master = InstrumentMaster()
    master.instruments = SAMPLE_INSTRUMENTS

    results = master.search_commodity("GOLD")

    assert len(results) == 3


def test_goldm_does_not_match_gold():
    master = InstrumentMaster()
    master.instruments = [
        {
            "segment": "MCX_FO",
            "name": "GOLDM",
            "trading_symbol": "GOLDM FUT",
            "instrument_type": "FUT",
        }
    ]

    assert master.search_commodity("GOLD") == []


def test_option_contract_filter():
    master = InstrumentMaster()
    master.instruments = SAMPLE_INSTRUMENTS

    results = master.get_option_contracts("GOLD")

    assert len(results) == 2
    assert {x["instrument_type"] for x in results} == {"CE", "PE"}


def test_futures_filter():
    master = InstrumentMaster()
    master.instruments = SAMPLE_INSTRUMENTS

    results = master.get_mcx_futures("GOLD")

    assert len(results) == 1
    assert results[0]["instrument_type"] == "FUT"


def test_invalid_commodity():
    master = InstrumentMaster()

    try:
        master.search_commodity("UNKNOWN")
        assert False
    except ValueError:
        pass
        
