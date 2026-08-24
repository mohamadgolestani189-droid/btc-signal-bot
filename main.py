import os
import requests
import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

SYMBOL = "BTCUSDT"
INTERVAL = "15m"
LIMIT = 100

API_URL = "https://api.kraken.com/0/public/OHLC"


def get_market_data():
    params = {
        "pair": "XBTUSDT",
        "interval": 15
    }

    response = requests.get(API_URL, params=params, timeout=15)
    response.raise_for_status()

    data = response.json()

    if data.get("error"):
        raise RuntimeError(str(data["error"]))

    result = data["result"]

    pair_key = next(key for key in result if key != "last")
    candles = result[pair_key]

    df = pd.DataFrame(
        candles,
        columns=[
            "time",
            "open",
            "high",
            "low",
            "close",
            "vwap",
            "volume",
            "count"
        ]
    )

    df["close"] = pd.to_numeric(df["close"])
    df["high"] = pd.to_numeric(df["high"])
    df["low"] = pd.to_numeric(df["low"])

    return df


def calculate_signal(df):
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()

    last = df.iloc[-1]

    price = last["close"]

    if last["ema20"] > last["ema50"]:
        signal = "LONG"
        tp = price * 1.02
        sl = price * 0.95
    elif last["ema20"] < last["ema50"]:
        signal = "SHORT"
        tp = price * 0.98
        sl = price * 1.05
    else:
        signal = "NO SIGNAL"
        tp = None
        sl = None

    return signal, price, tp, sl


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 BTC 15M Signal Bot\n\n"
        "برای دریافت سیگنال بیت‌کوین دستور زیر را بفرست:\n"
        "/signal"
    )


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        df = get_market_data()
        signal_type, price, tp, sl = calculate_signal(df)

        if signal_type == "NO SIGNAL":
            message = (
                "📊 BTC/USDT — تایم‌فریم 15 دقیقه\n\n"
                "⏳ فعلاً سیگنال معتبر نداریم."
            )
        else:
            message = (
                f"📊 BTC/USDT — 15M\n\n"
                f"🚨 Signal: {signal_type}\n"
                f"💰 Entry: {price:.2f}\n"
                f"🎯 TP: {tp:.2f}\n"
                f"🛑 SL: {sl:.2f}"
            )

        await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(
            "❌ خطا در دریافت اطلاعات بازار.\n"
            f"جزئیات: {str(e)[:200]}"
        )


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not configured.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal))

    print("Bot started successfully.")

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
