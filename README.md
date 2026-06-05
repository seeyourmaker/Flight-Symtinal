# Flight Symtinal

## Goal

Build a lightweight personal flight price monitoring system.

The project monitors only two round-trip journeys:

1. Mumbai <-> Guwahati
2. Mumbai <-> Bangkok

## Requirements

- Python only
- Use Playwright for scraping
- Use CSV for storage
- No database
- Telegram notifications
- GitHub Actions automation

## Coding Style

- Simple and beginner friendly
- Functions should be small
- Add comments explaining logic
- Explain complex code inline

## Teaching Mode

When generating code:

1. Explain why files are created
2. Explain major functions
3. Explain commands to run
4. Do not over-engineer
5. Prefer readability over optimization

## Definition Of Done

The system should:

- Fetch flight prices
- Store historical prices
- Track 90-day lows
- Send Telegram alerts
- Run automatically every 6 hours
