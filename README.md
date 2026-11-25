# Indian MCX Commodity Options Signal Bot

Paper-only scanner for MCX Crude Oil and Natural Gas using Upstox market data.

## Notifications and schedule

- GitHub Actions runs the tests and scanner when changes are pushed to `main`.
- A scheduled scan runs Monday-Friday at **09:15 Asia/Kolkata**.
- You can also start a scan manually from **GitHub → Actions → MCX Commodity Signal Scanner → Run workflow**.
- Every completed scan attempts to send a Telegram report, including no-trade, quote-mismatch, news-blocked, option-rejected, and signal outcomes.
- If tests or the scanner fail, the workflow has a separate Telegram failure-notification step with retries.

## Required GitHub Actions secrets

Add these under **Repository → Settings → Secrets and variables → Actions → New repository secret**:

- `UPSTOX_ACCESS_TOKEN`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Never commit tokens or paste them into chat. Start the Telegram bot and confirm the bot can message your chat before enabling scheduled scans.

## Telegram message behavior

- A valid paper candidate sends a separate signal message.
- The end-of-scan report lists the result for each commodity.
- Failed Telegram requests are retried three times.
- A signal is saved to signal history only after Telegram confirms delivery, so a temporary send failure can be retried.
- If the selected contract's quote does not match its instrument token, the bot reports the mismatch and does **not** create a trade signal from an unrelated contract.

## Safety

- Paper mode only.
- Live order execution is disabled and must remain disabled.
- A Telegram delivery cannot be guaranteed if Telegram, GitHub Actions, internet connectivity, or credentials are unavailable/invalid. The workflow retries and records delivery failures in its logs.
- A successful workflow means the code ran and the tests passed; it does not guarantee a profitable trade or a qualifying market setup.
