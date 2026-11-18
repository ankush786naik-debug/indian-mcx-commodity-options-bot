from instruments import InstrumentMaster


SAMPLE_INSTRUMENTS = [
    {
        "segment": "MCX_FO",
        "trading_symbol": "GOLDM26NOVFUT",
        "name": "GOLDM",
        "instrument_type": "FUTCOM",
        "instrument_key": "MCX_FO|GOLDM26NOVFUT",
    },
    {
        "segment": "MCX_FO",
        "trading_symbol": "GOLDM26NOVCE",
        "name": "GOLDM",
        "instrument_type": "OPTFUT",
        "instrument_key": "MCX_FO|GOLDM26NOVCE",
    },
    {
        "segment": "MCX_FO",
        "trading_symbol": "GOLDM26NOVPE",
        "name": "GOLDM",
        "instrument_type": "OPTFUT",
        "instrument_key": "MCX_FO|GOLDM26NOVPE",
    },
    {
        "segment": "NSE_FO",
        "trading_symbol": "NIFTY26NOVCE",
        "name": "NIFTY",
        "instrument_type": "OPTIDX",
        "instrument_key": "NSE_FO|NIFTY26NOVCE",
    },
]


def test_mcx_filter():
    master = InstrumentMaster()
    master.instruments = SAMPLE_INSTRUMENTS

    results = master.get_mcx_instruments()

    assert len(results) == 3
    assert all(
        item["segment"].startswith("MCX")
        for item in results
    )


def test_commodity_search():
    master = InstrumentMaster()
    master.instruments = SAMPLE_INSTRUMENTS

    results = master.search_commodity("GOLDM")

    assert len(results) == 3


def test_option_contract_filter():
    master = InstrumentMaster()
    master.instruments = SAMPLE_INSTRUMENTS

    results = master.get_option_contracts("GOLDM")

    assert len(results) == 2
    assert all(
        "OPT" in item["instrument_type"]
        for item in results
    )


def test_empty_commodity_rejected():
    master = InstrumentMaster()
    master.instruments = SAMPLE_INSTRUMENTS

    try:
        master.search_commodity("")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_no_matching_commodity():
    master = InstrumentMaster()
    master.instruments = SAMPLE_INSTRUMENTS

    assert master.search_commodity("COPPER") == []
  
