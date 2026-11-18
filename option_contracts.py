from datetime import date

from upstox_client import UpstoxClient


class OptionContracts:

    def __init__(self, client=None):
        self.client = client or UpstoxClient()

    def get_contracts(self, underlying_key, expiry_date=None):
        """
        Retrieve option contracts for an underlying instrument.

        expiry_date can be YYYY-MM-DD or an Upstox supported
        expiry keyword such as current_month.
        """

        if not isinstance(underlying_key, str) or not underlying_key.strip():
            raise ValueError("A valid underlying instrument key is required.")

        params = {"instrument_key": underlying_key}

        if expiry_date:
            params["expiry_date"] = expiry_date

        response = self.client.get(
            "/v2/option/contract",
            params=params,
        )

        if response.get("status") != "success":
            raise RuntimeError("Upstox option contracts request failed.")

        contracts = response.get("data")

        if not isinstance(contracts, list):
            raise RuntimeError("Invalid option contracts response.")

        return [
            contract for contract in contracts
            if contract.get("instrument_type") in ("CE", "PE")
            and contract.get("instrument_key")
            and contract.get("expiry")
            and contract.get("strike_price") is not None
            and contract.get("lot_size")
        ]

    def select_contract(
        self,
        contracts,
        option_type,
        underlying_price,
        expiry_date=None,
    ):
        """
        Select the nearest strike for the requested option type.
        """

        option_type = option_type.upper()

        if option_type not in ("CE", "PE"):
            raise ValueError("Option type must be CE or PE.")

        if underlying_price <= 0:
            raise ValueError("Underlying price must be positive.")

        today = date.today()

        valid = []

        for contract in contracts:
            if contract.get("instrument_type") != option_type:
                continue

            try:
                expiry = date.fromisoformat(contract["expiry"])
                strike = float(contract["strike_price"])
                lot_size = int(contract["lot_size"])
            except (ValueError, TypeError, KeyError):
                continue

            if expiry < today or strike <= 0 or lot_size <= 0:
                continue

            if expiry_date and contract["expiry"] != expiry_date:
                continue

            valid.append((contract, expiry, strike))

        if not valid:
            return None

        # Prefer the nearest available expiry.
        nearest_expiry = min(item[1] for item in valid)

        same_expiry = [
            item for item in valid
            if item[1] == nearest_expiry
        ]

        # Select the strike nearest to the underlying price.
        selected = min(
            same_expiry,
            key=lambda item: abs(item[2] - underlying_price),
        )

        return selected[0]

    def close(self):
        self.client.close()
      
