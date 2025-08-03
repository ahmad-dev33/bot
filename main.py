import logging
from telegram import __version__ as TG_VER
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from config import Config
import database as db
import os
import asyncio

async def run_bot():
    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(run_bot())

# إعداد التسجيل
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        message = query.message
    else:
        message = update.message
    
    referral_link = f"https://t.me/{context.bot.username}?start=ref_{user.id}"
    
    args = context.args
    invited_by = None
    
    if args and args[0].startswith('ref_'):
        try:
            invited_by = int(args[0][4:])
            db.add_referral(invited_by, user.id)
            db.update_balance(invited_by, 5)
        except (ValueError, IndexError):
            pass
    
    db.add_user(user.id, user.username, user.first_name, user.last_name, invited_by)
    
    keyboard = [
        [InlineKeyboardButton("💰 رصيدي", callback_data="balance")],
        [InlineKeyboardButton("📢 مشاهدة الإعلانات", callback_data="view_ads")],
        [InlineKeyboardButton("👥 دعوة الأصدقاء", callback_data="invite_friends")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="start")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = f"""
    مرحبًا {user.first_name}!
    
    🤖 أهلاً بك في بوت الربح من الإعلانات!
    
    📌 يمكنك كسب المال عن طريق:
    1. مشاهدة الإعلانات
    2. دعوة الأصدقاء
    
    ✨ الأوامر المتاحة:
    /start - إعادة تشغيل البوت
    /balance - عرض رصيدك
    
    رابط الدعوة الخاص بك:
    {referral_link}
    """
    
    if update.callback_query:
        await message.edit_text(welcome_message, reply_markup=reply_markup)
    else:
        await message.reply_text(welcome_message, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if not query.data:
        logger.error("Received empty callback data")
        return

    user_id = query.from_user.id
    
    try:
        if query.data == "balance":
            balance = db.get_user_balance(user_id)
            await query.edit_message_text(f"💰 رصيدك الحالي: {balance} وحدة")
        
        elif query.data == "view_ads":
            keyboard = []
            for ad_id, ad_data in Config.ADSTERRA_ADS.items():
                last_view = db.get_last_ad_view(user_id, ad_id)
                
                if last_view:
                    time_left = db.calculate_cooldown(last_view, ad_data['cooldown'])
                    if time_left > 0:
                        btn_text = f"{ad_data['title']} (متاح بعد {time_left} ساعة)"
                        keyboard.append([InlineKeyboardButton(btn_text, callback_data="cooldown")])
                        continue
                
                btn_text = f"{ad_data['title']} (مكافأة {ad_data['reward']} وحدات)"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"show_ad_{ad_id}")])
            
            keyboard.append([InlineKeyboardButton("🏠 الرئيسية", callback_data="start")])
            await query.edit_message_text(
                "📢 اختر إعلانًا للمشاهدة:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif query.data.startswith("show_ad_"):
            try:
                ad_id = int(query.data.split("_")[2])
                ad_data = Config.ADSTERRA_ADS.get(ad_id)
                
                if not ad_data:
                    await query.edit_message_text("⚠️ هذا الإعلان غير متوفر حالياً")
                    return
                
                view_id = db.add_ad_view(user_id, ad_id)
                
                keyboard = [
                    [InlineKeyboardButton("🌐 زيارة الإعلان", url=ad_data['url'])],
                    [InlineKeyboardButton("✅ تأكيد المشاهدة", callback_data=f"confirm_{view_id}")],
                    [InlineKeyboardButton("🏠 الرئيسية", callback_data="start")]
                ]
                
                await query.edit_message_text(
                    f"📌 {ad_data['title']}\n\n"
                    "1. اضغط على زر 'زيارة الإعلان'\n"
                    "2. بعد المشاهدة، عد هنا واضغط 'تأكيد المشاهدة'\n"
                    f"3. ستحصل على {ad_data['reward']} وحدات بعد التأكيد",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            
            except Exception as e:
                logger.error(f"Error showing ad: {str(e)}")
                await query.edit_message_text("⚠️ حدث خطأ في عرض الإعلان")

        elif query.data.startswith("confirm_"):
            try:
                view_id = int(query.data.split("_")[1])
                ad_id = db.get_ad_id_by_view(view_id)
                
                if not ad_id:
                    await query.edit_message_text("⚠️ لم يتم العثور على سجل المشاهدة")
                    return
                
                ad_data = Config.ADSTERRA_ADS.get(ad_id)
                if not ad_data:
                    await query.edit_message_text("⚠️ هذا الإعلان لم يعد موجوداً")
                    return
                
                db.confirm_ad_view(view_id)
                db.update_balance(user_id, ad_data['reward'])
                
                await query.edit_message_text(
                    f"🎉 تمت المكافأة بنجاح!\n"
                    f"لقد حصلت على {ad_data['reward']} وحدات\n\n"
                    f"رصيدك الحالي: {db.get_user_balance(user_id)} وحدة",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 الرئيسية", callback_data="start")]])
                )
            
            except Exception as e:
                logger.error(f"Error confirming ad view: {str(e)}")
                await query.edit_message_text("⚠️ حدث خطأ في تأكيد المشاهدة")

        elif query.data == "cooldown":
            await query.answer("⏳ يمكنك مشاهدة هذا الإعلان مرة واحدة كل 24 ساعة", show_alert=True)

        elif query.data == "invite_friends":
            referral_link = f"https://t.me/{context.bot.username}?start=ref_{user_id}"
            referrals_count = db.get_user_referrals(user_id)
            
            await query.edit_message_text(
                f"👥 دعوة الأصدقاء\n\n"
                f"• لكل صديق تدعوه: 5 وحدات\n"
                f"• عدد المدعوين: {referrals_count}\n\n"
                f"رابط الدعوة الخاص بك:\n{referral_link}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 الرئيسية", callback_data="start")]])
            )

        elif query.data == "start":
            await start(update, context)
        
        else:
            await query.edit_message_text("⚠️ أمر غير معروف، يرجى المحاولة مرة أخرى")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        await query.edit_message_text(
            "⚠️ حدث خطأ غير متوقع\n"
            "تم تسجيل الخطأ وسيتم إصلاحه قريباً\n\n"
            "جرب استخدام /start لإعادة التشغيل",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("إعادة التشغيل", callback_data="start")]])
        )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    balance = db.get_user_balance(user_id)
    await update.message.reply_text(f"💰 رصيدك الحالي: {balance} وحدة")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != Config.ADMIN_ID:
        await update.message.reply_text("⚠️ ليس لديك صلاحية الوصول إلى هذا الأمر.")
        return
    
    if not context.args:
        await update.message.reply_text("""
        🛠 أوامر المدير:
        
        /admin add_ad العنوان - الوصف - الرابط - المكافأة
        /admin toggle_ad ad_id
        /admin user_info user_id
        """)
        return
    
    command = context.args[0].lower()
    
    if command == "add_ad" and len(context.args) >= 5:
        title = context.args[1]
        description = context.args[2]
        url = context.args[3]
        try:
            reward = float(context.args[4])
            with db.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO ads (title, description, url, reward)
                VALUES (?, ?, ?, ?)
                ''', (title, description, url, reward))
                conn.commit()
            await update.message.reply_text(f"✅ تمت إضافة الإعلان: {title}")
        except ValueError:
            await update.message.reply_text("⚠️ المكافأة يجب أن تكون رقمًا.")
    
    elif command == "toggle_ad" and len(context.args) >= 2:
        try:
            ad_id = int(context.args[1])
            with db.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                UPDATE ads 
                SET is_active = NOT is_active 
                WHERE ad_id = ?
                ''', (ad_id,))
                conn.commit()
            await update.message.reply_text(f"✅ تم تغيير حالة الإعلان {ad_id}")
        except ValueError:
            await update.message.reply_text("⚠️ ad_id يجب أن يكون رقمًا.")
    
    elif command == "user_info" and len(context.args) >= 2:
        try:
            target_user_id = int(context.args[1])
            user = db.get_user_info(target_user_id)
            referrals = db.get_user_referrals(target_user_id)
                
            if user:
                message = f"""
                👤 معلومات المستخدم:
                
                🆔: {user['user_id']}
                👤: {user['first_name']} {user['last_name'] or ''}
                📛: @{user['username'] or 'N/A'}
                💰 الرصيد: {user['balance']}
                👥 عدد الدعوات: {referrals}
                """
                await update.message.reply_text(message)
            else:
                await update.message.reply_text("⚠️ المستخدم غير موجود.")
        except ValueError:
            await update.message.reply_text("⚠️ user_id يجب أن يكون رقمًا.")

def main() -> None:
    db.init_db()
    
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    application.run_polling()

if __name__ == "__main__":
    main()
