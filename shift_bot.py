import logging
import json
import os
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8709919503:AAFC_7-pA8N1OWwZy1eObYFjxqPyqe1D41k"
DATA_FILE = "shifts_data.json"

logging.basicConfig(level=logging.INFO)

# ─── Ma'lumotlarni saqlash ───────────────────────────────────────────────────

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(data, user_id):
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "shift_active": False,
            "shift_start": None,
            "total_km": 0,
            "fuel_cost": 0,
            "earnings": 0,
            "shifts": []
        }
    return data[uid]

# ─── Klaviatura ──────────────────────────────────────────────────────────────

def main_keyboard():
    keyboard = [
        [KeyboardButton("🟢 Shift boshlash"), KeyboardButton("🔴 Shift tugatish")],
        [KeyboardButton("⛽ Yoqilg'i qo'shish"), KeyboardButton("📍 KM qo'shish")],
        [KeyboardButton("💰 Daromad qo'shish"), KeyboardButton("📊 Statistika")],
        [KeyboardButton("📅 Bugungi hisobot"), KeyboardButton("🗂 Barcha shiftlar")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ─── Handlerlar ──────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚗 *Shift Boshqaruv Botiga Xush Kelibsiz!*\n\n"
        "Bu bot Yandex Pro haydovchilari uchun:\n"
        "✅ Shift boshqaruv\n"
        "✅ Daromad hisoblash\n"
        "✅ Yoqilg'i xarajat\n"
        "✅ KM hisobi\n\n"
        "Quyidagi tugmalardan foydalaning 👇",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    data = load_data()
    user = get_user(data, user_id)

    # ─── Shift boshlash ───────────────────────────────────────────────────────
    if text == "🟢 Shift boshlash":
        if user["shift_active"]:
            await update.message.reply_text("⚠️ Shift allaqachon boshlangan!")
        else:
            user["shift_active"] = True
            user["shift_start"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            user["_session_km"] = 0
            user["_session_fuel"] = 0
            user["_session_earnings"] = 0
            save_data(data)
            await update.message.reply_text(
                f"🟢 *Shift boshlandi!*\n"
                f"🕐 Vaqt: {datetime.now().strftime('%H:%M')}\n"
                f"📅 Sana: {datetime.now().strftime('%d.%m.%Y')}\n\n"
                f"Omad tilaymiz! 🚗",
                parse_mode="Markdown"
            )

    # ─── Shift tugatish ───────────────────────────────────────────────────────
    elif text == "🔴 Shift tugatish":
        if not user["shift_active"]:
            await update.message.reply_text("⚠️ Aktiv shift yo'q!")
        else:
            start_time = datetime.strptime(user["shift_start"], "%Y-%m-%d %H:%M:%S")
            end_time = datetime.now()
            duration = end_time - start_time
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)

            session_km = user.get("_session_km", 0)
            session_fuel = user.get("_session_fuel", 0)
            session_earnings = user.get("_session_earnings", 0)
            sof_foyda = session_earnings - session_fuel

            shift_record = {
                "sana": start_time.strftime("%d.%m.%Y"),
                "boshlash": start_time.strftime("%H:%M"),
                "tugatish": end_time.strftime("%H:%M"),
                "davomiyligi": f"{hours}s {minutes}d",
                "km": session_km,
                "yoqilgi": session_fuel,
                "daromad": session_earnings,
                "sof_foyda": sof_foyda
            }
            user["shifts"].append(shift_record)
            user["total_km"] += session_km
            user["fuel_cost"] += session_fuel
            user["earnings"] += session_earnings
            user["shift_active"] = False
            user["shift_start"] = None
            save_data(data)

            await update.message.reply_text(
                f"🔴 *Shift tugadi!*\n\n"
                f"⏱ Davomiyligi: {hours} soat {minutes} daqiqa\n"
                f"📍 KM: {session_km} km\n"
                f"⛽ Yoqilg'i: {session_fuel:,} so'm\n"
                f"💵 Daromad: {session_earnings:,} so'm\n"
                f"💰 Sof foyda: {sof_foyda:,} so'm",
                parse_mode="Markdown"
            )

    # ─── Yoqilg'i qo'shish ───────────────────────────────────────────────────
    elif text == "⛽ Yoqilg'i qo'shish":
        context.user_data["waiting_for"] = "fuel"
        await update.message.reply_text("⛽ Yoqilg'i xarajatini so'mda kiriting:\n\nMasalan: *50000*", parse_mode="Markdown")

    # ─── KM qo'shish ─────────────────────────────────────────────────────────
    elif text == "📍 KM qo'shish":
        context.user_data["waiting_for"] = "km"
        await update.message.reply_text("📍 Necha km yurdingizni kiriting:\n\nMasalan: *120*", parse_mode="Markdown")

    # ─── Daromad qo'shish ─────────────────────────────────────────────────────
    elif text == "💰 Daromad qo'shish":
        context.user_data["waiting_for"] = "earnings"
        await update.message.reply_text("💰 Daromad miqdorini so'mda kiriting:\n\nMasalan: *150000*", parse_mode="Markdown")

    # ─── Statistika ───────────────────────────────────────────────────────────
    elif text == "📊 Statistika":
        total_shifts = len(user["shifts"])
        total_km = user["total_km"]
        total_fuel = user["fuel_cost"]
        total_earnings = user["earnings"]
        total_profit = total_earnings - total_fuel

        await update.message.reply_text(
            f"📊 *Umumiy Statistika*\n\n"
            f"🔄 Jami shiftlar: {total_shifts} ta\n"
            f"📍 Jami KM: {total_km} km\n"
            f"⛽ Jami yoqilg'i: {total_fuel:,} so'm\n"
            f"💵 Jami daromad: {total_earnings:,} so'm\n"
            f"💰 Jami sof foyda: {total_profit:,} so'm",
            parse_mode="Markdown"
        )

    # ─── Bugungi hisobot ──────────────────────────────────────────────────────
    elif text == "📅 Bugungi hisobot":
        bugun = datetime.now().strftime("%d.%m.%Y")
        bugungi = [s for s in user["shifts"] if s["sana"] == bugun]

        if not bugungi:
            await update.message.reply_text(f"📅 Bugun ({bugun}) hech qanday shift yo'q.")
        else:
            msg = f"📅 *Bugungi hisobot ({bugun})*\n\n"
            for i, s in enumerate(bugungi, 1):
                msg += (
                    f"*{i}-shift:*\n"
                    f"🕐 {s['boshlash']} — {s['tugatish']} ({s['davomiyligi']})\n"
                    f"📍 {s['km']} km | ⛽ {s['yoqilgi']:,} so'm\n"
                    f"💵 {s['daromad']:,} so'm | 💰 {s['sof_foyda']:,} so'm\n\n"
                )
            await update.message.reply_text(msg, parse_mode="Markdown")

    # ─── Barcha shiftlar ──────────────────────────────────────────────────────
    elif text == "🗂 Barcha shiftlar":
        if not user["shifts"]:
            await update.message.reply_text("📂 Hali hech qanday shift yo'q.")
        else:
            last5 = user["shifts"][-5:]
            msg = "🗂 *Oxirgi 5 ta shift:*\n\n"
            for i, s in enumerate(last5, 1):
                msg += (
                    f"*{s['sana']} — {i}-shift*\n"
                    f"⏱ {s['boshlash']}—{s['tugatish']} | {s['davomiyligi']}\n"
                    f"📍 {s['km']} km | 💰 {s['sof_foyda']:,} so'm\n\n"
                )
            await update.message.reply_text(msg, parse_mode="Markdown")

    # ─── Raqam kiritish (fuel/km/earnings) ───────────────────────────────────
    elif context.user_data.get("waiting_for"):
        waiting = context.user_data.get("waiting_for")
        try:
            value = int(text.replace(" ", "").replace(",", ""))
            if waiting == "fuel":
                user["_session_fuel"] = user.get("_session_fuel", 0) + value
                save_data(data)
                context.user_data["waiting_for"] = None
                await update.message.reply_text(f"⛽ Yoqilg'i qo'shildi: *{value:,} so'm*", parse_mode="Markdown")
            elif waiting == "km":
                user["_session_km"] = user.get("_session_km", 0) + value
                save_data(data)
                context.user_data["waiting_for"] = None
                await update.message.reply_text(f"📍 KM qo'shildi: *{value} km*", parse_mode="Markdown")
            elif waiting == "earnings":
                user["_session_earnings"] = user.get("_session_earnings", 0) + value
                save_data(data)
                context.user_data["waiting_for"] = None
                await update.message.reply_text(f"💰 Daromad qo'shildi: *{value:,} so'm*", parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("⚠️ Faqat raqam kiriting! Masalan: 50000")

    else:
        await update.message.reply_text("👇 Tugmalardan foydalaning:", reply_markup=main_keyboard())

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
