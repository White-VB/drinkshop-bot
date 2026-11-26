# Drinkshop Telegram Bot

Telegram catalog and order bot built with Python, python-telegram-bot and PostgreSQL.

## Required environment variables
- `BOT_TOKEN`: token from BotFather
- `ADMIN_ID`: numeric Telegram user ID of the shop administrator
- `DATABASE_URL`: PostgreSQL connection URL provided by Railway

## Deploy
Deploy this repository as a Railway service, add a PostgreSQL database, and set the variables above. The app uses long polling; do not configure a public domain.

## Important before public launch
Product names, sparkling-wine sweetness categories, wine colors, official product photos, descriptions and awards are provisional/unverified where noted. Verify them against producer labels or official product pages before enabling sales. This starter stores inventory and sends order notifications; order confirmation, delivery rules, payment and age/legal compliance should be configured for the shop's jurisdiction.
