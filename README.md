# Indian MCX Commodity Options Scanner

Paper-only MCX options scanner for Crude Oil and Natural Gas. It uses Upstox market data, a multi-timeframe technical strategy, option quote/liquidity checks, and a news-risk filter. It does **not** place orders.

## Notifications and reliability

- Every scan sends a Telegram report, including `NO_TRADE`, unavailable quote, blocked/rejected, and signal outcomes.
- Telegram delivery retries. A failed scanner/test workflow also attempts a separate Telegram failure alert and stores the scan log as an Actions artifact.
- A Telegram message cannot be guaranteed if Telegram is unreachable, GitHub Actions is unavailable/cancelled before the fallback executes, network connectivity is down, or the bot token/chat ID is invalid. Check the failed Actions run and `mcx-scan-log` artifact.
- The workflow runs automatically on weekdays at 09:15 India time and can also be started manually from Actions.
- Live orders must remain disabled. Every candidate is paper-only; a successful workflow is not proof of profitability.

## GitHub Actions secrets

Add these under **Settings → Secrets and variables → Actions**:

- `UPSTOX_ACCESS_TOKEN`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Never store API tokens in code or commit them.

## Run and test

1. Open **Actions → MCX Commodity Signal Scanner**.
2. Choose **Run workflow** to start a manual scan.
3. Check Telegram for the scan report.
4. If the workflow fails, open its log artifact.

Run local tests:

```bash
python -m pip install -r requirements.txt
pytest -q
```
