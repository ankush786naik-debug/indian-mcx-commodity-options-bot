# Indian MCX Commodity Options Scanner

Paper-only MCX options signal scanner for configured commodities (currently Crude Oil and Natural Gas). It reads Upstox market data, evaluates the multi-timeframe strategy, checks option quote quality and news risk, and sends alerts to Telegram. It does **not** place orders.

## Safety and notification behavior

- Live order execution must remain disabled in `config.yaml`.
- Every completed scanner run attempts to send a Telegram run report, including `NO_TRADE`, blocked, unavailable-data, and error outcomes.
- Telegram requests retry up to three times. If the report cannot be delivered, the process exits with an error and GitHub Actions preserves the scan log artifact.
- A Telegram message cannot be guaranteed when Telegram, the network, the bot token, or the chat ID is unavailable/invalid. Check the failed Actions run and its `mcx-scan-log` artifact in that case.
- A directional alert is a paper candidate only. Verify the live quote and contract independently; do not treat a green workflow as proof of profitability.

## Required GitHub Actions secrets

Set these in **Repository Settings → Secrets and variables → Actions → New repository secret**:

- `UPSTOX_ACCESS_TOKEN`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Never paste tokens into source code, commits, or chat.

## Run

1. Open the repository's **Actions** tab.
2. Select **MCX Commodity Signal Scanner**.
3. Select **Run workflow** and confirm the branch.
4. Wait for completion, then check the Telegram run report.
5. If the run fails, open its log artifact and review the error.

Pull requests run the automated test suite. Pushes to `main` and manual workflow dispatch run tests and the paper scanner.

## Local tests

Install dependencies and run:

```bash
python -m pip install -r requirements.txt
pytest -q
```
