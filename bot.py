import csv
import logging
import os
import sys
from threading import Thread
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters, CallbackQueryHandler
from flask import Flask

TOKEN = "8255204107:AAF4_v6kvDiYZEuOuwClrh4Dd4MHGhOWpFE"
CHANNEL_ID = -1001234567890  # آیدی عددی کانال شما (باید تغییر دهید)
CHANNEL_LINK = "https://t.me/+29MDo7noLR0xMzZk"  # لینک عمومی کانال

print("=" * 50)
print(f"شروع اجرا در: {time.ctime()}")
print("=" * 50)

try:
    web_app = Flask(__name__)
    print("✅ Flask وارد شد")
except Exception as e:
    print(f"❌ خطای Flask: {e}")
    sys.exit(1)

@web_app.route('/')
def home():
    return "✅ ربات تلگرام نمره‌یاب فعال است"

@web_app.route('/health')
def health_check():
    return "OK", 200

def run_web_server():
    try:
        port = int(os.environ.get('PORT', 10000))
        print(f"🌐 سرور وب روی پورت {port} راه‌اندازی می‌شود...")
        web_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"❌ خطای سرور وب: {e}")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ذخیره وضعیت کاربران (به صورت موقت در حافظه)
user_status = {}

def search_grade(name: str, student_id: str) -> str:
    try:
        if not os.path.exists('grades.csv'):
            print("❌ فایل grades.csv یافت نشد!")
            logger.error("فایل grades.csv یافت نشد!")
            return None
            
        with open('grades.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if (row['name'].strip() == name.strip() and 
                    row['student_id'].strip() == student_id.strip()):
                    return row['grade']
        return None
    except Exception as e:
        logger.error(f"خطا در جستجوی نمره: {e}")
        return None

async def check_channel_membership(user_id: int, context: CallbackContext) -> bool:
    """بررسی عضویت کاربر در کانال"""
    try:
        # بررسی دقیق‌تر عضویت
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        logger.info(f"وضعیت عضویت کاربر {user_id}: {member.status}")
        
        # وضعیت‌های مجاز
        allowed_statuses = ['member', 'administrator', 'creator']
        is_member = member.status in allowed_statuses
        
        logger.info(f"کاربر {user_id} عضو است: {is_member}")
        return is_member
        
    except Exception as e:
        logger.error(f"خطا در بررسی عضویت کانال برای کاربر {user_id}: {e}")
        # اگر خطا رخ داد، فرض می‌کنیم کاربر عضو نیست
        return False

async def verify_membership(update: Update, context: CallbackContext) -> None:
    """بررسی عضویت کاربر با دکمه"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    logger.info(f"درخواست بررسی عضویت از کاربر {user_id}")
    
    try:
        # بررسی مجدد وضعیت عضویت
        is_member = await check_channel_membership(user_id, context)
        
        if is_member:
            # ذخیره وضعیت تأیید شده
            user_status[user_id] = {
                "verified": True,
                "timestamp": time.time()
            }
            
            logger.info(f"عضویت کاربر {user_id} تأیید شد")
            
            await query.edit_message_text(
                "✅ عضویت شما تأیید شد!\n\n"
                "حالا می‌توانید اطلاعات خود را به این فرمت ارسال کنید:\n"
                "نام و نام خانوادگی،شماره دانشجویی\n\n"
                "مثال:\n"
                "بهنام احمدی،14044121000"
            )
        else:
            # حذف وضعیت قبلی کاربر (اگر وجود داشت)
            if user_id in user_status:
                del user_status[user_id]
            
            logger.info(f"کاربر {user_id} هنوز عضو نیست")
            
            keyboard = [
                [InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK)],
                [InlineKeyboardButton("🔄 بررسی مجدد عضویت", callback_data="verify_membership")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "❌ هنوز در کانال عضو نیستید!\n\n"
                "⚠️ توجه: پس از عضویت در کانال، کمی صبر کنید (۱۰-۲۰ ثانیه)\n"
                "سپس روی دکمه 'بررسی مجدد عضویت' کلیک کنید.\n\n"
                f"🔗 لینک کانال: {CHANNEL_LINK}",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"خطا در تایید عضویت کاربر {user_id}: {e}")
        
        await query.edit_message_text(
            "⚠️ خطا در بررسی عضویت. لطفاً دوباره تلاش کنید.\n\n"
            "روی دکمه زیر کلیک کنید:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تلاش مجدد", callback_data="verify_membership")]
            ])
        )

async def handle_message(update: Update, context: CallbackContext) -> None:
    try:
        user_id = update.effective_user.id
        text = update.message.text.strip()
        logger.info(f"پیام دریافتی از {user_id}: {text}")
        
        # بررسی وضعیت تأیید کاربر
        if user_id not in user_status or not user_status[user_id].get("verified", False):
            # اگر کاربر تأیید نشده، پیام عضویت نشان داده شود
            keyboard = [
                [InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK)],
                [InlineKeyboardButton("✅ بررسی عضویت من", callback_data="verify_membership")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "👋 برای استفاده از ربات، ابتدا باید در کانال ما عضو شوید:\n\n"
                "1. روی دکمه 'عضویت در کانال' کلیک کنید\n"
                "2. پس از عضویت، ۱۰-۲۰ ثانیه صبر کنید\n"
                "3. سپس روی 'بررسی عضویت من' کلیک کنید\n\n"
                f"🔗 کانال: {CHANNEL_LINK}",
                reply_markup=reply_markup
            )
            return
        
        # اگر کاربر تأیید شده، پردازش نمره
        if '،' in text:
            parts = text.split('،')
        else:
            parts = text.split(',')
        
        if len(parts) != 2:
            await update.message.reply_text('⚠️ فرمت صحیح: «نام و نام خانوادگی، شماره دانشجویی»')
            return
        
        name, student_id = parts[0].strip(), parts[1].strip()
        grade = search_grade(name, student_id)
        
        if grade:
            await update.message.reply_text(f'✅ نمره شما: {grade}')
            logger.info(f"نمره یافت شد: {name} -> {grade}")
        else:
            await update.message.reply_text('❌ اطلاعات یافت نشد. لطفاً بررسی کنید.')
            logger.info(f"نمره یافت نشد: {name}, {student_id}")
            
    except Exception as e:
        logger.error(f"خطا در پردازش پیام: {e}")

async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ بررسی عضویت من", callback_data="verify_membership")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """
    سلام! 👋
    
    برای دریافت نمره ابتدا باید در کانال ما عضو شوید:
    
    1️⃣ روی دکمه 'عضویت در کانال' کلیک کنید
    2️⃣ پس از عضویت، ۱۰-۲۰ ثانیه صبر کنید
    3️⃣ سپس روی 'بررسی عضویت من' کلیک کنید
    
    بعد از تأیید عضویت، اطلاعات خود را به این شکل ارسال کنید:
    
    نام و نام خانوادگی،شماره دانشجویی
    
    مثال:
    بهنام احمدی،14044121000
    
    ⚠️ توجه: پس از عضویت در کانال، کمی صبر کنید تا سیستم به‌روزرسانی شود.
    """
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

def main():
    print("🚀 در حال راه‌اندازی سرویس...")
    
    server_thread = Thread(target=run_web_server, daemon=True)
    server_thread.start()
    print("🌐 سرور وب فعال شد")
    time.sleep(1)
    
    try:
        print("🤖 در حال راه‌اندازی ربات تلگرام...")
        application = Application.builder().token(TOKEN).build()
        
        # ثبت دستورات
        application.add_handler(CommandHandler("start", start))
        
        # ثبت هندلر برای دکمه‌ها
        application.add_handler(CallbackQueryHandler(verify_membership, pattern="^verify_membership$"))
        
        # ثبت هندلر برای پیام‌های متنی
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("✅ ربات تلگرام آماده است!")
        print("=" * 50)
        
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
        )
        
    except Exception as e:
        print(f"❌ خطای اصلی: {e}")
        logger.error(f"خطای اصلی: {e}")

if __name__ == '__main__':
    main()
