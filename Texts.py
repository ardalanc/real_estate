# Texts.py

texts = {
    # main menu
    "BUY"            :       "🏠 خرید ملک",
    "RENT"           :       "🏢 اجاره ملک",
    "MORE"           :       "ℹ️ بیشتر",
    "BUDGET_ENTER"   :       "💰 وارد کردن بودجه",
    "SHOW_ALL"       :       "📋 نمایش همه فایل‌ها",
    "BACK"           :       "🔙 بازگشت",
    "NEXT_PAGE": "➡️ صفحه بعد",

    # post type
    "POST_SELL": "فروش",
    "POST_RENT": "اجاره",

    # more menu
    "ABOUT": "📄 درباره ما",
    "SUPPORT": "☎️ پشتیبانی",

    # messages
    "WELCOME": "درود 👋\nبه املاک دورانی خوش آمدید.",
    "ASK_BUDGET": "بودجه خود را به تومان وارد کنید:",
    "ASK_PRICE": "بودجه خود را به تومان وارد کنید:",
    "INVALID_PRICE": "❌ لطفاً فقط عدد وارد کنید",
    "SEARCH_BUY"     : "در حال جستجوی ملک برای خرید تا {price} تومان",
    "SEARCH_RENT"    : "در حال جستجوی ملک برای اجاره تا {price} تومان",
    "ASK_RENT_BUDGET": "بودجه اجاره خود را انتخاب کنید",
    "ASK_RENT_PRICE": "حداکثر اجاره مورد نظر را وارد کنید",
    "PREVIOUS_PAGE": "⬅️ صفحه قبل",
    "PAGE_NAVIGATION": "صفحه نتایج",

    # admin options

    "ACCESS_DENIED": "❌ شما به پنل ادمین دسترسی ندارید.",
    "ADMIN_WELCOME": "به پنل مدیریت خوش آمدید. یک گزینه را انتخاب کنید:",
    "ADMIN_ADD_PROPERTY": "➕ افزودن فایل جدید",
    "ADMIN_LIST_PROPERTIES": "📂 مدیریت فایل‌ها",
    "ADMIN_VISIT_REQUESTS": "📅 درخواست‌های بازدید",
    "ADMIN_BROADCAST": "📢 ارسال پیام به همه کاربران",
    "ASK_PROPERTY_METRAJ": "متراژ ملک را وارد کنید (عدد):",
    "ASK_PROPERTY_ROOMS": "تعداد خواب را وارد کنید (عدد):",
    "INVALID_METRAJ": "متراژ باید عدد باشد.",
    "INVALID_ROOMS": "تعداد خواب باید یک عدد باشد.",
    "ADMIN_MANAGE_PROPERTIES": "مدیریت فایل‌ها",
    "DELETE_PROPERTY": "حذف فایل",
    "EDIT_PROPERTY": "ویرایش فایل",
    "DISABLE_PROPERTY": "غیرفعال کردن",
    "SOLD_PROPERTY": "فروش رفته",
"PROPERTY_DELETED": "✅ فایل حذف شد",

"PROPERTY_DISABLED": "فایل غیرفعال شد",

"PROPERTY_SOLD": "فایل به عنوان فروش رفته ثبت شد",

"PROPERTY_UPDATED": "✅ فایل ویرایش شد",

"ASK_EDIT_TITLE": "عنوان جدید را وارد کنید",

"ASK_EDIT_PRICE": "قیمت جدید را وارد کنید",

"ASK_EDIT_DESC": "توضیح جدید را وارد کنید",

"NO_PROPERTIES": "هیچ فایلی ثبت نشده",
"PROPERTIES_LIST_HEADER": "📋 لیست فایل‌ها:",
"ADMIN_VISIT_REQUESTS": "درخواست‌های بازدید",

"VISIT_LIST_HEADER": "📅 لیست درخواست‌های بازدید:",

"NO_VISIT_REQUESTS": "درخواستی ثبت نشده است",

"VISIT_APPROVE": "✅ تایید",
"VISIT_REJECT": "❌ رد",
"VISIT_CONTACTED": "📞 تماس گرفته شد",
"VISIT_DELETE": "🗑 حذف",

"VISIT_UPDATED": "✅ وضعیت درخواست بروزرسانی شد",
"VISIT_DELETED": "✅ درخواست حذف شد",
"BROADCAST": "ارسال پیام همگانی",

"ASK_BROADCAST": "پیام مورد نظر برای ارسال به همه کاربران را ارسال کنید",

"BROADCAST_STARTED": "ارسال پیام شروع شد...",

"BROADCAST_DONE": "✅ ارسال پیام تمام شد",

"BROADCAST_STATS": "ارسال به کاربران:\n\nموفق: {success}\nناموفق: {failed}",

}












 

# import telebot
# from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton
# from telebot.util import antiflood
# import os
# import time
# from Texts import texts






# def create_database():
#     conn = mysql.connector.connect(**database_config, database=database_name)
#     cur = conn.cursor()
#     cur.execute(f"DROP DATABASE IF EXISTS {db_name}")
#     cur.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
#     conn.commit()
#     cur.close()
#     conn.close()
#     print (f"database {db_name} created")


# def create_table_user():
#     conn = mysql.connector.connect(**database_config, database=database_name)
#     cur = conn.cursor()
#     SQL_Query = """
#     CREATE TABLE `USER` (
#     ID INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
#     TEL_ID VARCHAR(100) NOT NULL UNIQUE,
#     COIN INT UNSIGNED NOT NULL DEFAULT 0,
#     IS_BANN BOOLEAN NOT NULL DEFAULT 0,
#     REGISTER_DATE DATETIME DEFAULT CURRENT_TIMESTAMP, 
#     LAST_TIME_UPDATE DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP   
#     );
#     """
#     cur.execute(SQL_Query)
#     conn.commit()
#     cur.close()
#     conn.close()














# user_steps = dict()


# def listener(messages):
#     """
#     When new messages arrive TeleBot will call this function.
#     """
#     for m in messages:
#         # print(m)
#         if m.content_type == 'text':
#             print(f"{m.chat.first_name} [{str(m.chat.id)}]: {m.text}")

#         elif m.content_type == 'photo':
#             print(f"{m.chat.first_name} [{str(m.chat.id)}]: New photo recieved")

#         elif m.content_type == 'contact':
#             print(f"{m.chat.first_name} [{str(m.chat.id)}]: New contact recieved")

#         elif m.content_type == 'location':
#             print(f"{m.chat.first_name} [{str(m.chat.id)}]: New location recieved")



# bot.set_update_listener(listener) 








# @bot.callback_query_handler(func=lambda call: True)
# def callback_handler(call):
#     call_id = call.id
#     cid = call.message.chat.id
#     mid = call.message.message_id
#     data = call.data
    
#     if data == "set_sell_obj":
#         pass
#     elif data == "set_sell_obj":
#         pass











# @bot.message_handler(commands=["start"])
# def command_start_handler(message):
#     cid = message.chat.id

#     keyboard = ReplyKeyboardMarkup()

#     keyboard.add(texts["button 1"] , texts["botton 2"])
#     keyboard.add(texts["button 3"] , texts["botton 4"])

#     bot.send_message(cid, "درود.به املاک دورانی خوش امدید.", reply_markup = keyboard)
    
    
# @bot.message_handler(commands=['help'])
# def command_help_handler(message):
#     cid = message.chat.id
#     bot.send_message(cid ,"ما در اینجا به دنبال بهترین تجربه برای شما هستیم.")


# @bot.message_handler(func = lambda message = texts["button 1"])
# def buy_req_handler(message):
#     cid = message.chat.id

#     bot.send_message(cid , "بودجه شما چقدر است؟ (به تومان وارد کنید)")

#     user_steps = {cid : "show_buy_by_price"}



# @bot.message_handler(func = lambda message = texts["button 2"])
# def rent_req_handler(message):
#     cid = message.chat.id
    
#     bot.send_message(cid , "بودجه شما چقدر است؟ (به تومان وارد کنید)")

#     user_steps = {cid : "show_rent_by_price"}



# @bot.message_handler(func = lambda message = texts["button 3"])
# def set_obj_handler(message):
#     cid = message.chat.id

#     markup = InlineKeyboardMarkup()
#     markup.add(InlineKeyboardButton(texts["button 5"], callback_data="set_sell_obj") ,
#                InlineKeyboardButton(texts["button 6"], callback_data="set_rent_obj") )

#     bot.send_message(cid ,"نوع آگهی خود را وارد کنید.")




# @bot.message_handler(func = lambda message = texts["button 4"])
# def more_button_handler(message):
#     cid = message.chat.id

#     keyboard = ReplyKeyboardMarkup()

#     keyboard.add(texts["button 7"] , texts["botton 9"])
#     keyboard.add(texts["button 8"] , texts["botton 10"])

#     bot.send_message(cid, "دسترسی های بیشتر", reply_markup = keyboard)
    






# @bot.message_handler(func = lambda message = texts["button 7"])
# def more_button_handler(message):







# @bot.message_handler(func= lambda message: user_steps.get(message.chat.id) == "show_rent_by_price")
# def step_show_by_price_handler(message):
#     cid = message.chat.id


# @bot.message_handler(func= lambda message: user_steps.get(message.chat.id) == "show_buy_by_price")
# def step_show_by_price_handler(message):
#     cid = message.chat.id








# bot.infinity_polling()






