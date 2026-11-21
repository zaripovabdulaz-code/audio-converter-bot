# 🎧 Audio Converter Bot

Telegram bot: video yoki audio faylni MP3, WAV, OGG formatlariga o'giradi va ovozni yaxshilaydi (shovqinni kamaytirish, balandlikni tenglashtirish).

**Demo:** [@Shaxsiy_konvertor_bot](https://t.me/Shaxsiy_konvertor_bot)

## Imkoniyatlar

- 🎵 Video/audio → MP3, WAV, OGG
- ✨ Ovozni yaxshilash (ffmpeg filtrlari)
- 🌐 3 tilli interfeys: 🇺🇿 O'zbekcha, 🇷🇺 Русский, 🇬🇧 English
- 📊 Kunlik limit (har foydalanuvchiga 10 ta)
- 🛠 Admin buyrug'i `/stat`: foydalanuvchilar va konvertatsiya statistikasi
- 💾 SQLite ma'lumotlar bazasi

## Texnologiyalar

Python 3.12, aiogram 3, ffmpeg, SQLite

## O'rnatish

1. Python va [ffmpeg](https://ffmpeg.org) o'rnating.
2. Loyihani yuklab oling:
   ```
   git clone https://github.com/zaripovabdulaz-code/audio-converter-bot.git
   cd audio-converter-bot
   pip install -r requirements.txt
   ```
3. `.env.example` faylni `.env` deb nusxalang va to'ldiring:
   ```
   BOT_TOKEN=@BotFather bergan token
   ADMIN_ID=sizning Telegram ID'ingiz
   ```
4. Ishga tushiring:
   ```
   python bot.py
   ```

## Buyruqlar

| Buyruq | Vazifasi |
|---|---|
| `/start` | Boshlash, til tanlash |
| `/help` | Yordam |
| `/limit` | Bugungi limit |
| `/id` | Telegram ID'ingiz |
| `/stat` | Statistika (faqat admin) |

## Skrinshotlar

(bu yerga 2-3 ta skrinshot qo'shiladi)

## Muallif

Abdulaziz: [GitHub](https://github.com/zaripovabdulaz-code)