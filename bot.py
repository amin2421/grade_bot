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

# ذخیره وضعیت کاربران
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
        logger.info(f"🔍 بررسی عضویت کاربر {user_id} در کانال {CHANNEL_ID}")
        
        # ابتدا سعی می‌کنیم وضعیت بات در کانال را بررسی کنیم
        try:
            bot_member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=context.bot.id)
            logger.info(f"وضعیت بات در کانال: {bot_member.status}")
            
            if bot_member.status not in ['administrator', 'creator']:
                logger.error(f"❌ بات در کانال ادمین نیست! وضعیت: {bot_member.status}")
                return False
                
        except Exception as bot_err:
            logger.error(f"❌ خطا در بررسی وضعیت بات: {bot_err}")
            return False
        
        # حالا وضعیت کاربر را بررسی می‌کنیم
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        logger.info(f"وضعیت عضویت کاربر {user_id}: {member.status}")
        
        # وضعیت‌های مجاز
        allowed_statuses = ['member', 'administrator', 'creator', 'restricted']
        
        # اگر وضعیت restricted است، بررسی می‌کنیم آیا می‌تواند پیام ببیند
        if member.status == 'restricted':
            if hasattr(member, 'is_member') and member.is_member:
                logger.info(f"کاربر {user_id} restricted اما عضو است")
                return True
            else:
                logger.info(f"کاربر {user_id} restricted و عضو نیست")
                return False
        
        is_member = member.status in allowed_statuses
        
        logger.info(f"کاربر {user_id} عضو است: {is_member} (وضعیت: {member.status})")
        return is_member
        
    except Exception as e:
        logger.error(f"❌ خطای جدی در بررسی عضویت کاربر {user_id}: {str(e)}")
        
        # اطلاعات بیشتر درباره خطا
        if "user not found" in str(e).lower():
            logger.error("⚠️ کاربر در کانال پیدا نشد")
        elif "chat not found" in str(e).lower():
            logger.error("⚠️ کانال پیدا نشد - ممکن است آیدی اشتباه باشد")
        elif "not enough rights" in str(e).lower():
            logger.error("⚠️ ربات دسترسی کافی ندارد")
        elif "forbidden" in str(e).lower():
            logger.error("⚠️ ربات از کانال اخراج شده یا ادمین نیست")
        
        return False

async def test_bot_access(update: Update, context: CallbackContext) -> None:
    """تست دسترسی بات به کانال"""
    try:
        user_id = update.effective_user.id
        
        # تست 1: بررسی وضعیت بات در کانال
        try:
            bot_member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=context.bot.id)
            status_msg = f"✅ وضعیت بات در کانال: {bot_member.status}\n"
        except Exception as e:
            status_msg = f"❌ خطا در بررسی وضعیت بات: {str(e)}\n"
        
        # تست 2: بررسی عضویت کاربر
        try:
            user_member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            status_msg += f"✅ وضعیت کاربر {user_id}: {user_member.status}\n"
        except Exception as e:
            status_msg += f"❌ خطا در بررسی وضعیت کاربر: {str(e)}\n"
        
        # تست 3: دریافت اطلاعات کانال
        try:
            chat = await context.bot.get_chat(chat_id=CHANNEL_ID)
            status_msg += f"✅ اطلاعات کانال:\n"
            status_msg += f"   عنوان: {chat.title}\n"
            status_msg += f"   نوع: {chat.type}\n"
            status_msg += f"   آیدی: {chat.id}\n"
        except Exception as e:
            status_msg += f"❌ خطا در دریافت اطلاعات کانال: {str(e)}\n"
        
        await update.message.reply_text(f"🧪 نتایج تست دسترسی:\n\n{status_msg}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در تست: {str(e)}")

async def verify_membership(update: Update, context: CallbackContext) -> None:
    """بررسی عضویت کاربر با دکمه"""
    query = update.callback_query
    await query.answer("در حال بررسی...")
    
    user_id = query.from_user.id
    logger.info(f"🔍 درخواست بررسی عضویت از کاربر {user_id}")
    
    try:
        # بررسی مجدد وضعیت عضویت
        is_member = await check_channel_membership(user_id, context)
        
        if is_member:
            # ذخیره وضعیت تأیید شده
            user_status[user_id] = {
                "verified": True,
                "timestamp": time.time(),
                "checked_at": time.ctime()
            }
            
            logger.info(f"✅ عضویت کاربر {user_id} تأیید شد")
            
            await query.edit_message_text(
                "✅ ✅ عضویت شما تأیید شد!\n\n"
                "🎉 حالا می‌توانید اطلاعات خود را ارسال کنید:\n\n"
                "📝 فرمت:\n"
                "نام و نام خانوادگی،شماره دانشجویی\n\n"
                "مثال:\n"
                "بهنام احمدی،14044121000"
            )
        else:
            # حذف وضعیت قبلی کاربر
            if user_id in user_status:
                del user_status[user_id]
            
            logger.warning(f"⚠️ کاربر {user_id} هنوز عضو نیست یا مشکل دسترسی وجود دارد")
            
            keyboard = [
                [InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK)],
                [InlineKeyboardButton("🔄 بررسی مجدد عضویت", callback_data="verify_membership")],
                [InlineKeyboardButton("🛠️ راهنمایی مشکل", callback_data="help_access")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "❌ عضویت شما تأیید نشد!\n\n"
                "🔍 دلایل احتمالی:\n"
                "1. هنوز عضو کانال نشده‌اید\n"
                "2. ربات ادمین کانال نیست\n"
                "3. کانال بیش‌ازحد خصوصی است\n\n"
                "🛠️ راه‌حل:\n"
                "1. مطمئن شوید عضو کانال شده‌اید\n"
                "2. از ادمین بخواهید ربات را ادمین کند\n"
                "3. روی دکمه زیر کلیک کنید\n\n"
                f"🔗 کانال: {CHANNEL_LINK}",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"❌ خطا در تایید عضویت کاربر {user_id}: {str(e)}")
        
        await query.edit_message_text(
            f"⚠️ خطای فنی: {str(e)[:100]}\n\n"
            "لطفاً با ادمین تماس بگیرید یا دوباره تلاش کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تلاش مجدد", callback_data="verify_membership")]
            ])
        )

async def help_access(update: Update, context: CallbackContext) -> None:
    """راهنمایی برای مشکل دسترسی"""
    query = update.callback_query
    await query.answer()
    
    help_text = """
    🛠️ راهنمایی رفع مشکل عضویت:
    
    1. ✅ اطمینان حاصل کنید ربات در کانال ادمین است:
       - به تنظیمات کانال بروید
       - Administrators → Add Admin
       - ربات را انتخاب کنید
       - ✅ تمام دسترسی‌ها را فعال کنید
    
    2. ✅ اطمینان حاصل کنید کانال خیلی خصوصی نباشد:
       - Settings → Channel Type
       - بهتر است Private نباشد
    
    3. ✅ تست وضعیت:
       دستور /test را در چت با ربات ارسال کنید
    
    4. 📞 اگر مشکل ادامه داشت:
       با ادمین اصلی کانال تماس بگیرید
    """
    
    await query.edit_message_text(
        help_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 بررسی مجدد عضویت", callback_data="verify_membership")]
        ])
    )

async def handle_message(update: Update, context: CallbackContext) -> None:
    try:
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        # اگر دستور /test بود
        if text.lower() == "/test":
            await test_bot_access(update, context)
            return
            
        logger.info(f"پیام دریافتی از {user_id}: {text}")
        
        # بررسی وضعیت تأیید کاربر
        if user_id not in user_status or not user_status[user_id].get("verified", False):
            keyboard = [
                [InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK)],
                [InlineKeyboardButton("✅ بررسی عضویت من", callback_data="verify_membership")],
                [InlineKeyboardButton("🧪 تست دسترسی (/test)", callback_data="test_access")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "👋 برای دریافت نمره، ابتدا در کانال عضو شوید:\n\n"
                "1. روی 'عضویت در کانال' کلیک کنید\n"
                "2. پس از عضویت، روی 'بررسی عضویت من' کلیک کنید\n"
                "3. اگر مشکل داشتید، از /test استفاده کنید\n\n"
                f"🔗 {CHANNEL_LINK}",
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
        [InlineKeyboardButton("✅ بررسی عضویت من", callback_data="verify_membership")],
        [InlineKeyboardButton("🧪 تست دسترسی", callback_data="test_access")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
    سلام! 👋
    
    برای دریافت نمره ابتدا باید در کانال ما عضو شوید:
    
    🔗 {CHANNEL_LINK}
    
    🛠️ اگر مشکل دارید:
    1. از /test استفاده کنید
    2. مطمئن شوید ربات ادمین کانال است
    
    📝 بعد از تأیید عضویت، اطلاعات خود را ارسال کنید:
    
    نام و نام خانوادگی،شماره دانشجویی
    
    مثال:
    بهنام احمدی،14044121000
    """
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def test_access(update: Update, context: CallbackContext) -> None:
    """هدایت به تست دسترسی"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "برای تست دسترسی، لطفاً در چت ربات دستور زیر را ارسال کنید:\n\n"
        "`/test`\n\n"
        "این دستور وضعیت دسترسی ربات را بررسی می‌کند.",
        parse_mode='Markdown'
    )

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
        application.add_handler(CommandHandler("test", test_bot_access))
        
        # ثبت هندلر برای دکمه‌ها
        application.add_handler(CallbackQueryHandler(verify_membership, pattern="^verify_membership$"))
        application.add_handler(CallbackQueryHandler(help_access, pattern="^help_access$"))
        application.add_handler(CallbackQueryHandler(test_access, pattern="^test_access$"))
        
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
