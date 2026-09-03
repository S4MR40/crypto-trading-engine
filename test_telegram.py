import asyncio
import os
import logging
from integrated_pipeline_ccxt import TelegramNotifier

async def main():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    print(f"🔍 Testing Telegram Credentials...")
    print(f"• Token: {'Configured' if bot_token else 'MISSING'}")
    print(f"• Chat ID: {chat_id if chat_id else 'MISSING'}\n")

    notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)

    if not notifier.enabled:
        print("❌ Telegram credentials missing. Make sure to export TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
        return

    # 1. Send simulated Position Opened notification
    open_msg = (
        "🚀 *TEST ALERT: POSITION OPENED*\n"
        "• *Symbol:* `BTC/USDT`\n"
        "• *Side:* `LONG`\n"
        "• *Entry:* `$67,500.00`\n"
        "• *Size:* `0.0296` units\n"
        "• *Take Profit:* `$69,200.00`\n"
        "• *Stop Loss:* `$66,300.00`\n"
        "• *Reason:* Uptrend (>EMA200 66800.00) + RSI Oversold (31.2) + MACD Upward Turn"
    )
    
    print("📤 Sending simulated POSITION OPENED alert...")
    await notifier.send_message(open_msg)
    await asyncio.sleep(1)

    # 2. Send simulated Position Closed notification
    close_msg = (
        "✅ *TEST ALERT: POSITION CLOSED (🎯 PROFIT)*\n"
        "• *Symbol:* `BTC/USDT`\n"
        "• *Trigger:* `TAKE_PROFIT`\n"
        "• *Entry:* `$67,500.00`\n"
        "• *Exit:* `$69,200.00`\n"
        "• *Realized PnL:* `+$50.32` (`+2.52%`)\n"
        "• *Account Balance:* `$10,050.32`"
    )
    
    print("📤 Sending simulated POSITION CLOSED alert...")
    await notifier.send_message(close_msg)
    print("\n✅ Test completed! Check your Telegram app for the 2 alert messages.")

if __name__ == "__main__":
    asyncio.run(main())
