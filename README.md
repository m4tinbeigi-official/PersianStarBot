# PersianStarBot 🌟

A multilingual Telegram bot for Persian birth date exploration, implemented in **PHP**, **Go**, **Python**, and **Rust**. Pick your birth date (Jalali calendar), get Gregorian/Hijri conversions, zodiac, holidays, moon phase images (NASA API), share options, reminders, and history!

## Features
- 📅 Select Persian birth date (1340-1385) with inline keyboards.
- 🔄 Convert to Gregorian and Hijri calendars.
- 🌙 Fetch moon phase images with watermark (NASA API).
- ✨ Show age, zodiac sign, and Iranian holidays (Calendarific API).
- 🌍 Support for 10 languages (English, Persian, etc.).
- 🔔 Set birthday reminders.
- 📜 Save and view birth date history.
- 🔒 Secure with input validation and CSRF protection.

## Implementations
| Language | Lines of Code | Speed (ms/req) | Memory (MB) | Notes |
|----------|---------------|----------------|-------------|-------|
| PHP (Laravel) | ~200 | 10-50 | ~50 | Easy to develop, heavy framework. |
| Go | ~120 | <1 | ~4 | Fast, simple, great for microservices. |
| Python (FastAPI) | ~100 | 1-5 | ~10 | Readable, rapid prototyping. |
| Rust | ~90 | <0.5 | ~2-3 | Fastest, safest, memory-efficient. |

**Winner**: Rust for its blazing speed, minimal memory usage, and safety guarantees!

## Setup

1. Clone the repo:
```bash
   git clone https://github.com/yourusername/PersianStarBot.git
   cd PersianStarBot
```

2. Set environment variables:
```
   export BOT_TOKEN=your_telegram_bot_token
   export NASA_API_KEY=your_nasa_api_key
   export CALENDARIFIC_API_KEY=your_calendarific_api_key
   ```

3. Run the bot (choose your language):
   # PHP
   ```
   cd php
   composer install
   touch database/database.sqlite
   php artisan migrate
   php artisan serve
   ```

   # Go
   ```
   cd go
   go mod tidy
   go run main.go
   ```

   # Python
   ```
   cd python
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python main.py
   ```

   # Rust
   ```
   cd rust
   cargo run
   ```

4. Set webhook:
```
   curl -F "url=https://yourdomain.com/<lang>/webhook" https://api.telegram.org/bot$BOT_TOKEN/setWebhook
```
## Dependencies
- PHP: Laravel, irazasyed/telegram-bot-sdk, morilog/jalali
- Go: go-telegram-bot-api, jmoiron/sqlx, fogleman/gg
- Python: FastAPI, python-telegram-bot, sqlalchemy, persiantools, pillow
- Rust: teloxide, sqlx, reqwest, image

## Watermark
Place watermark.png in each language folder for moon phase image branding.

## Contributing
Feel free to fork, add features, or optimize! Submit PRs with your improvements. 🙌

## License
MIT License. See LICENSE for details.

## Why PersianStarBot?
This project showcases how different languages handle the same complex task. Rust shines for performance, Python for readability, Go for simplicity, and PHP for rapid development. Pick your flavor! 🚀

## Credits
Built with ❤️ for developers exploring multilingual, culture-rich bots.

