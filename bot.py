import asyncio
import os
import shutil
import sqlite3
import subprocess
import uuid
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import (
    TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter,
)
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, Message, ReplyKeyboardMarkup,
)

# ---------- Sozlamalar ----------
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
HAMMAGA_XABAR = False       # True: hamma foydalanuvchiga, False: faqat adminga
DAILY_LIMIT = 5            # kuniga nechta konvertatsiya
MAX_MB = 20                 # kiruvchi fayl limiti
MAX_CHIQISH_MB = 50         # chiquvchi fayl limiti
DB_FILE = "bot.db"

FORMATLAR = {
    "mp3": ["-acodec", "libmp3lame", "-b:a", "192k"],
    "wav": ["-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1"],
    "ogg": ["-acodec", "libvorbis", "-q:a", "5"],
}

YAXSHILASH_FILTRI = (
    "highpass=f=80,"
    "afftdn=nf=-25,"
    "acompressor=threshold=-18dB:ratio=3,"
    "loudnorm=I=-16:TP=-1.5"
)

# ---------- Matnlar (3 til) ----------
TEXTS = {
    "uz": {
        "start": "👋 Salom! Men ovoz va video ustaxonasiman.\n\n"
                 "Fayl yuboring, men:\n🎵 MP3 / WAV / OGG ga o'giraman\n"
                 "✨ Ovozni tozalayman\n\nTilni pastdan tanlang 👇",
        "help": "ℹ️ Yordam\n\n1. Video yoki audio fayl yuboring (20 MB gacha)\n"
                "2. Formatni tanlang\n3. Natijani oling\n\n"
                "Kuniga {limit} ta bepul konvertatsiya.\n"
                "Buyruqlar: /start, /help, /limit",
        "choose": "Faylni oldim ✅\nQaysi formatga o'girib beray?",
        "enhance": "✨ Ovozni yaxshilash",
        "converting": "⏳ Konvertatsiya qilinmoqda...",
        "limit_reached": "⛔ Bugungi limit tugadi ({limit}/{limit}). Ertaga yana urinib ko'ring.",
        "limit_info": "📊 Bugun: {used}/{limit} ta ishlatildi.\nQoldi: {left} ta.",
        "fail": "❌ Bu faylni o'gira olmadim.",
        "too_big_in": "❌ Fayl {mb} MB dan katta. Kichikroq fayl yuboring.",
        "too_big_out": "❌ Natija 50 MB dan katta. MP3 ni tanlab ko'ring.",
        "send_first": "Avval fayl yuboring",
        "other": "Iltimos, video yoki audio fayl yuboring 🎬",
        "btn_limit": "📊 Mening limitim",
        "btn_help": "ℹ️ Yordam",
        "lang_set": "✅ Til o'zgartirildi.",
    },
    "ru": {
        "start": "👋 Привет! Я мастерская звука и видео.\n\n"
                 "Отправьте файл, и я:\n🎵 Конвертирую в MP3 / WAV / OGG\n"
                 "✨ Очищу звук\n\nВыберите язык ниже 👇",
        "help": "ℹ️ Помощь\n\n1. Отправьте видео или аудио (до 20 МБ)\n"
                "2. Выберите формат\n3. Получите результат\n\n"
                "{limit} бесплатных конвертаций в день.\n"
                "Команды: /start, /help, /limit",
        "choose": "Файл получен ✅\nВ какой формат конвертировать?",
        "enhance": "✨ Улучшить звук",
        "converting": "⏳ Конвертация...",
        "limit_reached": "⛔ Лимит на сегодня исчерпан ({limit}/{limit}). Попробуйте завтра.",
        "limit_info": "📊 Сегодня: {used}/{limit}.\nОсталось: {left}.",
        "fail": "❌ Не удалось обработать файл.",
        "too_big_in": "❌ Файл больше {mb} МБ. Отправьте файл поменьше.",
        "too_big_out": "❌ Результат больше 50 МБ. Попробуйте MP3.",
        "send_first": "Сначала отправьте файл",
        "other": "Пожалуйста, отправьте видео или аудио 🎬",
        "btn_limit": "📊 Мой лимит",
        "btn_help": "ℹ️ Помощь",
        "lang_set": "✅ Язык изменён.",
    },
    "en": {
        "start": "👋 Hi! I'm an audio & video workshop.\n\n"
                 "Send a file and I will:\n🎵 Convert to MP3 / WAV / OGG\n"
                 "✨ Clean up the audio\n\nPick a language below 👇",
        "help": "ℹ️ Help\n\n1. Send a video or audio file (up to 20 MB)\n"
                "2. Choose a format\n3. Get the result\n\n"
                "{limit} free conversions per day.\n"
                "Commands: /start, /help, /limit",
        "choose": "File received ✅\nWhich format do you need?",
        "enhance": "✨ Enhance audio",
        "converting": "⏳ Converting...",
        "limit_reached": "⛔ Daily limit reached ({limit}/{limit}). Try again tomorrow.",
        "limit_info": "📊 Today: {used}/{limit} used.\nLeft: {left}.",
        "fail": "❌ I couldn't process this file.",
        "too_big_in": "❌ File is larger than {mb} MB. Send a smaller one.",
        "too_big_out": "❌ Result is over 50 MB. Try MP3.",
        "send_first": "Send a file first",
        "other": "Please send a video or audio file 🎬",
        "btn_limit": "📊 My limit",
        "btn_help": "ℹ️ Help",
        "lang_set": "✅ Language changed.",
    },
}

LIMIT_TUGMALARI = {TEXTS[l]["btn_limit"] for l in TEXTS}
HELP_TUGMALARI = {TEXTS[l]["btn_help"] for l in TEXTS}

bot = Bot(TOKEN)
dp = Dispatcher()
fayllar = {}  # user_id -> file_id


def T(lang: str, key: str, **kw) -> str:
    return TEXTS[lang][key].format(**kw) if kw else TEXTS[lang][key]


# ---------- Ma'lumotlar bazasi ----------
def db():
    return sqlite3.connect(DB_FILE)


def db_init():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'uz', joined TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS usage(
            user_id INTEGER, day TEXT, count INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, day))""")


def user_qosh(uid: int):
    with db() as c:
        c.execute("INSERT OR IGNORE INTO users(id, lang, joined) VALUES(?, 'uz', ?)",
                  (uid, date.today().isoformat()))


def user_ochir(uid: int):
    with db() as c:
        c.execute("DELETE FROM users WHERE id=?", (uid,))


def get_lang(uid: int) -> str:
    with db() as c:
        r = c.execute("SELECT lang FROM users WHERE id=?", (uid,)).fetchone()
    return r[0] if r else "uz"


def set_lang(uid: int, lang: str):
    user_qosh(uid)
    with db() as c:
        c.execute("UPDATE users SET lang=? WHERE id=?", (lang, uid))


def bugun_soni(uid: int) -> int:
    with db() as c:
        r = c.execute("SELECT count FROM usage WHERE user_id=? AND day=?",
                      (uid, date.today().isoformat())).fetchone()
    return r[0] if r else 0


def usage_qosh(uid: int):
    with db() as c:
        c.execute("""INSERT INTO usage(user_id, day, count) VALUES(?, ?, 1)
                     ON CONFLICT(user_id, day) DO UPDATE SET count=count+1""",
                  (uid, date.today().isoformat()))


def statistika() -> dict:
    bugun = date.today().isoformat()
    with db() as c:
        return {
            "users": c.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "new_today": c.execute("SELECT COUNT(*) FROM users WHERE joined=?",
                                   (bugun,)).fetchone()[0],
            "active_today": c.execute("SELECT COUNT(*) FROM usage WHERE day=?",
                                      (bugun,)).fetchone()[0],
            "conv_today": c.execute("SELECT COALESCE(SUM(count),0) FROM usage WHERE day=?",
                                    (bugun,)).fetchone()[0],
            "conv_total": c.execute("SELECT COALESCE(SUM(count),0) FROM usage").fetchone()[0],
        }


def barcha_userlar() -> list:
    with db() as c:
        return [r[0] for r in c.execute("SELECT id FROM users")]


# ---------- Tugmalar ----------
def menyu(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=T(lang, "btn_limit")),
                   KeyboardButton(text=T(lang, "btn_help"))]],
        resize_keyboard=True,
    )


def til_tugmalari() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
    ]])


def format_tugmalari(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎵 MP3", callback_data="fmt_mp3"),
            InlineKeyboardButton(text="🎼 WAV", callback_data="fmt_wav"),
            InlineKeyboardButton(text="🎧 OGG", callback_data="fmt_ogg"),
        ],
        [InlineKeyboardButton(text=T(lang, "enhance"), callback_data="fmt_yaxshi")],
    ])


# ---------- Ishga tushish xabari ----------
async def ishga_tushdi_xabari():
    qabul = barcha_userlar() if HAMMAGA_XABAR else [ADMIN_ID]
    for uid in qabul:
        try:
            await bot.send_message(uid, "🟢 Bot qayta ishga tushdi! Kechikish uchun uzr.")
        except TelegramForbiddenError:
            user_ochir(uid)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except Exception:
            pass
        await asyncio.sleep(0.05)


# ---------- ffmpeg ----------
def ogir(kirish: Path, chiqish: Path, fmt: str) -> bool:
    natija = subprocess.run(
        ["ffmpeg", "-y", "-i", str(kirish), "-vn", *FORMATLAR[fmt], str(chiqish)],
        capture_output=True, text=True, errors="ignore",
    )
    if natija.returncode != 0:
        print("FFMPEG XATOSI:\n", natija.stderr[-800:])
    return natija.returncode == 0 and chiqish.exists()


def yaxshila(kirish: Path, chiqish: Path) -> bool:
    natija = subprocess.run(
        ["ffmpeg", "-y", "-i", str(kirish), "-vn", "-af", YAXSHILASH_FILTRI,
         "-acodec", "libmp3lame", "-b:a", "192k", str(chiqish)],
        capture_output=True, text=True, errors="ignore",
    )
    if natija.returncode != 0:
        print("FFMPEG XATOSI:\n", natija.stderr[-800:])
    return natija.returncode == 0 and chiqish.exists()


# ---------- Buyruqlar ----------
@dp.message(CommandStart())
async def start(m: Message):
    user_qosh(m.from_user.id)
    lang = get_lang(m.from_user.id)
    await m.answer(T(lang, "start"), reply_markup=til_tugmalari())
    await m.answer("👇", reply_markup=menyu(lang))


@dp.callback_query(F.data.startswith("lang_"))
async def til_tanlandi(c: CallbackQuery):
    lang = c.data.removeprefix("lang_")
    set_lang(c.from_user.id, lang)
    await c.answer(T(lang, "lang_set"))
    await c.message.edit_text(T(lang, "start"), reply_markup=til_tugmalari())
    await c.message.answer(T(lang, "lang_set"), reply_markup=menyu(lang))


@dp.message(Command("help"))
async def help_buyrugi(m: Message):
    lang = get_lang(m.from_user.id)
    await m.answer(T(lang, "help", limit=DAILY_LIMIT), reply_markup=menyu(lang))


@dp.message(Command("limit"))
async def limit_buyrugi(m: Message):
    lang = get_lang(m.from_user.id)
    used = bugun_soni(m.from_user.id)
    await m.answer(T(lang, "limit_info", used=used, limit=DAILY_LIMIT,
                     left=max(0, DAILY_LIMIT - used)))


@dp.message(Command("id"))
async def mening_id(m: Message):
    await m.answer(f"ID: {m.from_user.id}")


@dp.message(Command("stat"))
async def stat(m: Message):
    if m.from_user.id != ADMIN_ID:
        return
    s = statistika()
    await m.answer(
        "📊 Statistika\n\n"
        f"👥 Jami foydalanuvchi: {s['users']}\n"
        f"🆕 Bugun qo'shilgan: {s['new_today']}\n"
        f"🔥 Bugun faol: {s['active_today']}\n"
        f"🔄 Bugungi konvertatsiya: {s['conv_today']}\n"
        f"📦 Jami konvertatsiya: {s['conv_total']}"
    )


# ---------- Menyu tugmalari ----------
@dp.message(F.text.in_(LIMIT_TUGMALARI))
async def menyu_limit(m: Message):
    await limit_buyrugi(m)


@dp.message(F.text.in_(HELP_TUGMALARI))
async def menyu_help(m: Message):
    await help_buyrugi(m)


# ---------- Fayl qabul qilish ----------
@dp.message(F.video | F.voice | F.audio | F.video_note | F.document)
async def fayl_keldi(m: Message):
    user_qosh(m.from_user.id)
    lang = get_lang(m.from_user.id)
    fayl = m.video or m.voice or m.audio or m.video_note or m.document
    if fayl.file_size and fayl.file_size > MAX_MB * 1024 * 1024:
        await m.answer(T(lang, "too_big_in", mb=MAX_MB))
        return
    fayllar[m.from_user.id] = fayl.file_id
    await m.answer(T(lang, "choose"), reply_markup=format_tugmalari(lang))


@dp.callback_query(F.data.startswith("fmt_"))
async def format_tanlandi(c: CallbackQuery):
    uid = c.from_user.id
    lang = get_lang(uid)
    file_id = fayllar.get(uid)
    if not file_id:
        await c.answer(T(lang, "send_first"), show_alert=True)
        return

    if uid != ADMIN_ID and bugun_soni(uid) >= DAILY_LIMIT:
        await c.answer()
        await c.message.edit_text(T(lang, "limit_reached", limit=DAILY_LIMIT))
        return

    fmt = c.data.removeprefix("fmt_")
    await c.answer()
    xabar = await c.message.edit_text(T(lang, "converting"))
    papka = Path("vaqtinchalik") / uuid.uuid4().hex
    papka.mkdir(parents=True)

    try:
        kirish = papka / "kirish"
        await bot.download(file_id, destination=kirish)

        if fmt == "yaxshi":
            chiqish = papka / "natija.mp3"
            ok = await asyncio.to_thread(yaxshila, kirish, chiqish)
            fmt = "mp3"
        else:
            chiqish = papka / f"natija.{fmt}"
            ok = await asyncio.to_thread(ogir, kirish, chiqish, fmt)

        if not ok:
            await xabar.edit_text(T(lang, "fail"))
            return
        if chiqish.stat().st_size > MAX_CHIQISH_MB * 1024 * 1024:
            await xabar.edit_text(T(lang, "too_big_out"))
            return

        if fmt == "mp3":
            await c.message.answer_audio(FSInputFile(chiqish, filename="audio.mp3"))
        else:
            await c.message.answer_document(FSInputFile(chiqish, filename=f"audio.{fmt}"))
        usage_qosh(uid)  # faqat muvaffaqiyatli bo'lsa limitga yoziladi
        await xabar.delete()
    except TelegramBadRequest as e:
        if "too big" in str(e):
            await xabar.edit_text(T(lang, "too_big_in", mb=MAX_MB))
        else:
            await xabar.edit_text(f"❌ {str(e)[:200]}")
    except Exception as e:
        await xabar.edit_text(f"❌ {str(e)[:200]}")
    finally:
        shutil.rmtree(papka, ignore_errors=True)


# ---------- Boshqa xabarlar (ENG PASTDA) ----------
@dp.message()
async def boshqa(m: Message):
    await m.answer(T(get_lang(m.from_user.id), "other"))


async def main():
    print(">>> YANGI KOD ISHLAYAPTI")
    db_init()
    me = await bot.get_me()
    print(f">>> Bot: @{me.username}")
    await ishga_tushdi_xabari()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())