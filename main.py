import telebot
import mysql.connector
import re
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from Texts import texts
from config import BOT_TOKEN, DATABASE_CONFIG, DB_NAME, ADMIN_IDS

telebot.apihelper.API_URL="http://tapi.bale.ai/bot{0}/{1}"

bot = telebot.TeleBot(BOT_TOKEN)

# ---------------- DATABASE ----------------

def get_connection():
    return mysql.connector.connect(database=DB_NAME,**DATABASE_CONFIG)

# -- visit request --

def update_user_phone(telegram_id, phone):
    conn = mysql.connector.connect(**DATABASE_CONFIG, database=DB_NAME)
    cur = conn.cursor()

    query = """
        UPDATE users
        SET phone = %s
        WHERE telegram_id = %s
    """
    cur.execute(query, (phone, telegram_id))
    conn.commit()

    affected = cur.rowcount

    cur.close()
    conn.close()

    return affected > 0

def create_visit_request(property_id, user_id):
    conn = mysql.connector.connect(**DATABASE_CONFIG, database=DB_NAME)
    cur = conn.cursor()

    query = """
        INSERT INTO visit_requests (
            property_id,
            user_id,
            status,
            admin_id,
            scheduled_time,
            admin_message,
            is_successful_deal
        )
        VALUES (%s, %s, 'pending', NULL, NULL, NULL, FALSE)
    """
    cur.execute(query, (property_id, user_id))
    conn.commit()

    request_id = cur.lastrowid

    cur.close()
    conn.close()

    return request_id

def get_user_id_by_telegram_id(telegram_id):
    conn = mysql.connector.connect(**DATABASE_CONFIG, database=DB_NAME)
    cur = conn.cursor(dictionary=True)

    query = "SELECT id FROM users WHERE telegram_id = %s LIMIT 1"
    cur.execute(query, (telegram_id,))
    user = cur.fetchone()

    cur.close()
    conn.close()

    if user:
        return user['id']
    return None

def get_user_by_telegram_id(telegram_id):
    conn = mysql.connector.connect(**DATABASE_CONFIG, database=DB_NAME)
    cur = conn.cursor(dictionary=True)

    query = "SELECT * FROM users WHERE telegram_id = %s LIMIT 1"
    cur.execute(query, (telegram_id,))
    user = cur.fetchone()

    cur.close()
    conn.close()

    return user

# ---------------- MENUE ----------------

def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton("خرید"),
        KeyboardButton("اجاره")
    )
    markup.add(KeyboardButton("بیشتر"))
    return markup

def admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton("افزودن فایل جدید"),
        KeyboardButton("مدیریت فایل ها")
    )
    markup.add(
        KeyboardButton("درخواست های بازدید"),
        KeyboardButton("ارسال پیام به همه کاربران")           
    )

    return markup

def buy_options_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    btn_all = InlineKeyboardButton("نمایش تمام فایل‌ها 🏠", callback_data="buy_show_all")
    btn_budget = InlineKeyboardButton("جست‌وجو بر اساس بودجه 💰", callback_data="buy_by_budget")
    markup.add(btn_all, btn_budget)
    return markup

def rent_options_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🏘 نمایش تمام فایل‌های اجاره", callback_data="rent_all"),
        InlineKeyboardButton("💰 جست‌وجو بر اساس ودیعه", callback_data="rent_by_deposit"),
        InlineKeyboardButton("💸 جست‌وجو بر اساس اجاره ماهانه", callback_data="rent_by_monthly"),
        InlineKeyboardButton("🎯 جست‌وجو ترکیبی", callback_data="rent_by_combo")
    )
    return markup

# ---------------- START ----------------

@bot.message_handler(commands=['start'])
def start_handler(message):

    cid = message.chat.id

    if is_admin(cid):
        bot.send_message(
        cid,
        "خوش امدید",
        reply_markup=admin_menu()
        )    
        
        return
    
    register_user(message)   

    bot.send_message(
        cid,
        "خوش امدید",
        reply_markup=main_menu()
    )

# ---------------- VERFECATION ----------------

def register_user(message):

    cid = message.chat.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE telegram_id=%s",(cid,))

    user = cur.fetchone()

    if not user:
        cur.execute("""
            INSERT INTO users
            (telegram_id, username, name)
            VALUES (%s,%s,%s)
        """, (
            cid,
            username,
            first_name,
        ))

        conn.commit()

    cur.close()
    conn.close()

def is_admin(cid):
    # return cid in ADMIN_IDS
    return False
    # try:
    #     with get_connection() as conn:
    #         with conn.cursor() as cur:
    #             cur.execute("SELECT 1 FROM admins WHERE telegram_id = %s", (cid,))
    #             result = cur.fetchone()
    #             return result is not None        
    # except Exception:
    #     return False

def normalize_phone_number(phone_text):
    # ۱. تبدیل اعداد فارسی به انگلیسی
    trans = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    clean = phone_text.translate(trans).strip()
    
    # ۲. حذف کاراکترهای غیر عددی و فضای خالی
    clean = re.sub(r'\D', '', clean)
    
    # ۳. هندل کردن پیش‌شماره‌ها
    if clean.startswith('98') and len(clean) == 12:
        clean = '0' + clean[2:]
    elif clean.startswith('0098') and len(clean) == 14:
        clean = '0' + clean[4:]
    elif len(clean) == 10 and clean.startswith('9'):
        clean = '0' + clean
    
    # ۴. اعتبارسنجی نهایی با regex
    if re.match(r'^09\d{9}$', clean):
        return clean
    return None

# ---------------- MESSAGE HANDLER ----------------
# -- buy --
@bot.message_handler(func=lambda message: message.text == "خرید")
def buy_handler(message):
    cid = message.chat.id
    bot.send_message(cid, "لطفاً نحوه نمایش فایل‌های خرید را انتخاب کنید:", reply_markup=buy_options_markup())

# ---------------- CALLBACK HANDLER ----------------
# -- buy --

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def buy_callback_handler(call):
    cid = call.message.chat.id
    if call.data == "buy_show_all":
        show_properties(cid, mode='all')
    
    elif call.data == "buy_by_budget":
        msg = bot.send_message(cid, "لطفاً **حداقل** بودجه خود را به تومان وارد کنید:\n(مثال: 500000000)")
        bot.register_next_step_handler(msg, process_min_budget)

# -- rent --

@bot.message_handler(func=lambda message: message.text == "اجاره")
def rent_handler(message):
    bot.send_message(message.chat.id, "لطفاً روش جستجو را انتخاب کنید:", reply_markup=rent_options_markup())

@bot.callback_query_handler(func=lambda call: call.data.startswith('rent_'))
def rent_callback_handler(call):
    cid = call.message.chat.id
    if call.data == "rent_all":
        show_rent_properties(cid, mode='all')
    
    elif call.data == "rent_by_deposit":
        msg = bot.send_message(cid, "حداقل **ودیعه (رهن)** مورد نظر را وارد کنید:")
        bot.register_next_step_handler(msg, process_deposit_step, "min")

    elif call.data == "rent_by_monthly":
        msg = bot.send_message(cid, "حداقل **اجاره ماهانه** مورد نظر را وارد کنید:")
        bot.register_next_step_handler(msg, process_rent_step, "min")

    elif call.data == "rent_by_combo":
        msg = bot.send_message(cid, "شروع جستجوی ترکیبی.\nحداقل **ودیعه** را وارد کنید:")
        bot.register_next_step_handler(msg, process_combo_step, {"step": 1})

# -- visit request --

@bot.callback_query_handler(func=lambda call: call.data.startswith("visit_"))
def handle_visit_request(call):
    cid = call.message.chat.id
    pid = call.data.split('_')[1] # Property ID
    
    # چک کردن شماره تلفن در دیتابیس
    user = get_user_by_telegram_id(call.from_user.id) # تابعی که قبلا گفتی داری
    
    if not user or not user.get('phone'):
        msg = bot.send_message(cid, "برای ثبت درخواست بازدید، لطفاً شماره موبایل خود را وارد کنید (مثال: 0912xxxxxxx):")
        bot.register_next_step_handler(msg, process_phone_step, pid)
    else:
        ask_for_confirmation(cid, pid)

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_visit_") or call.data == "cancel_visit")
def handle_visit_confirmation(call):
    cid = call.message.chat.id
    
    if call.data == "cancel_visit":
        bot.answer_callback_query(call.id, "درخواست لغو شد.")
        bot.delete_message(cid, call.message.message_id)
        return

    pid = int(call.data.split('_')[2])
    user_db_id = get_user_id_by_telegram_id(call.from_user.id)

    if not user_db_id:
        bot.answer_callback_query(call.id, "خطا: کاربر یافت نشد.")
        return

    # چک کردن اینکه آیا درخواست پندینگ قبلی وجود داره یا نه
    if is_visit_request_pending(user_db_id, pid):
        bot.answer_callback_query(call.id, "شما قبلاً برای این ملک درخواست داده‌اید.")
        bot.send_message(cid, "⚠️ درخواست شما قبلاً ثبت شده و در حال بررسی است.")
    else:
        # ثبت در دیتابیس (property_id اول، user_id دوم)
        create_visit_request(pid, user_db_id)
        bot.answer_callback_query(call.id, "موفقیت‌آمیز!")
        bot.edit_message_text("✅ درخواست شما با موفقیت ثبت شد. مشاور به‌زودی با شما تماس می‌گیرد.", cid, call.message.message_id)


# ---------------- FUNCTION ----------------
# -- buy --

def process_min_budget(message):
    cid = message.chat.id
    if not message.text.isdigit():
        msg = bot.send_message(cid, "لطفاً فقط عدد وارد کنید. دوباره حداقل بودجه را ارسال کنید:")
        bot.register_next_step_handler(msg, process_min_budget)
        return
    
    min_price = int(message.text)
    msg = bot.send_message(cid, f"حداقل بودجه: {min_price:,} تومان\nحالا **حداکثر** بودجه را وارد کنید:")
    bot.register_next_step_handler(msg, process_max_budget, min_price)

def process_max_budget(message, min_price):
    cid = message.chat.id
    if not message.text.isdigit():
        msg = bot.send_message(cid, "لطفاً فقط عدد وارد کنید. حداکثر بودجه را ارسال کنید:")
        bot.register_next_step_handler(msg, process_max_budget, min_price)
        return
    
    max_price = int(message.text)
    bot.send_message(cid, f"در حال جست‌وجو برای بازه {min_price:,} تا {max_price:,} تومان...")
    show_properties(cid, mode='budget', min_p=min_price, max_p=max_price)

def show_properties(cid, mode='all', min_p=0, max_p=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    if mode == 'all':
        query = "SELECT * FROM properties WHERE type='buy' AND status='available' ORDER BY created_at DESC"
        params = ()
    else:
        query = "SELECT * FROM properties WHERE type='buy' AND status='available' AND price BETWEEN %s AND %s ORDER BY price ASC"
        params = (min_p, max_p)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    if not rows:
        bot.send_message(cid, "متأسفانه موردی یافت نشد. 😕")
    else:
        for row in rows:
            # قالب‌بندی متن مشابه عکسی که فرستادی
            caption = (
                f"🏠 عنوان: {row['title']}\n\n"
                f"💰 قیمت: {row['price']:,} تومان\n"
                f"📐 متراژ: {row['metraj']} متر\n"
                f"🛏 خواب: {row['rooms']}\n\n"
                f"📝 توضیحات:\n{row['description']}"
            )
            
            # پیدا کردن عکس‌های ملک از جدول property_images
            cursor.execute("SELECT telegram_file_id FROM property_images WHERE property_id = %s LIMIT 1", (row['id'],))
            img_row = cursor.fetchone()
            
            # دکمه درخواست بازدید
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📅 درخواست بازدید", callback_data=f"visit_{row['id']}"))
            
            if img_row:
                bot.send_photo(cid, img_row['telegram_file_id'], caption=caption, reply_markup=markup)
            else:
                bot.send_message(cid, caption, reply_markup=markup)
                
    cursor.close()
    conn.close()

# -- rent --

def process_deposit_step(message, type_mode, min_val=None):
    cid = message.chat.id
    val = normalize_number(message.text)
    if val is None:
        msg = bot.send_message(cid, "لطفاً عدد معتبری وارد کنید:")
        bot.register_next_step_handler(msg, process_deposit_step, type_mode, min_val)
        return

    if type_mode == "min":
        msg = bot.send_message(cid, f"حداقل ودیعه: {val:,}\nحالا **حداکثر ودیعه** را وارد کنید:")
        bot.register_next_step_handler(msg, process_deposit_step, "max", val)
    else:
        show_rent_properties(cid, mode='deposit', filters={'min_dep': min_val, 'max_dep': val})

def process_rent_step(message, type_mode, min_val=None):
    cid = message.chat.id
    val = normalize_number(message.text)
    if val is None:
        msg = bot.send_message(cid, "لطفاً عدد معتبری وارد کنید:")
        bot.register_next_step_handler(msg, process_rent_step, type_mode, min_val)
        return

    if type_mode == "min":
        msg = bot.send_message(cid, f"حداقل اجاره: {val:,}\nحالا **حداکثر اجاره** را وارد کنید:")
        bot.register_next_step_handler(msg, process_rent_step, "max", val)
    else:
        show_rent_properties(cid, mode='rent_val', filters={'min_rent': min_val, 'max_rent': val})

def process_combo_step(message, data):
    cid = message.chat.id
    val = normalize_number(message.text)
    if val is None:
        msg = bot.send_message(cid, "ورودی نامعتبر. دوباره وارد کنید:")
        bot.register_next_step_handler(msg, process_combo_step, data)
        return

    step = data['step']
    if step == 1:
        data.update({'min_dep': val, 'step': 2})
        msg = bot.send_message(cid, "حداکثر **ودیعه**؟")
        bot.register_next_step_handler(msg, process_combo_step, data)
    elif step == 2:
        data.update({'max_dep': val, 'step': 3})
        msg = bot.send_message(cid, "حداقل **اجاره ماهانه**؟")
        bot.register_next_step_handler(msg, process_combo_step, data)
    elif step == 3:
        data.update({'min_rent': val, 'step': 4})
        msg = bot.send_message(cid, "حداکثر **اجاره ماهانه**؟")
        bot.register_next_step_handler(msg, process_combo_step, data)
    elif step == 4:
        data['max_rent'] = val
        show_rent_properties(cid, mode='combo', filters=data)

def show_rent_properties(cid, mode='all', filters=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM properties WHERE type='rent' AND status='available' "
    params = []

    if mode == 'deposit':
        query += "AND deposit BETWEEN %s AND %s"
        params = [filters['min_dep'], filters['max_dep']]
    elif mode == 'rent_val':
        query += "AND rent BETWEEN %s AND %s"
        params = [filters['min_rent'], filters['max_rent']]
    elif mode == 'combo':
        query += "AND deposit BETWEEN %s AND %s AND rent BETWEEN %s AND %s"
        params = [filters['min_dep'], filters['max_dep'], filters['min_rent'], filters['max_rent']]

    cursor.execute(query, params)
    rows = cursor.fetchall()

    if not rows:
        bot.send_message(cid, "موردی با این مشخصات پیدا نشد. 📍")
    else:
        for row in rows:
            caption = (
                f"🏠 عنوان: {row['title']}\n\n"
                f"💰 ودیعه: {row['deposit']:,} تومان\n"
                f"💸 اجاره: {row['rent']:,} تومان\n"
                f"📐 متراژ: {row['metraj']} متر\n"
                f"🛏 خواب: {row['rooms']}\n\n"
                f"📝 توضیحات:\n{row['description']}"
            )
            
            # دریافت تصویر اول
            cursor.execute("SELECT telegram_file_id FROM property_images WHERE property_id = %s LIMIT 1", (row['id'],))
            img = cursor.fetchone()
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📅 درخواست بازدید", callback_data=f"visit_{row['id']}"))

            if img:
                bot.send_photo(cid, img['telegram_file_id'], caption=caption, reply_markup=markup)
            else:
                bot.send_message(cid, caption, reply_markup=markup)

    cursor.close()
    conn.close()

# -- visit request --

def process_phone_step(message, pid):
    cid = message.chat.id
    phone = normalize_phone_number(message.text)
    
    if not phone:
        msg = bot.send_message(cid, "❌ شماره نامعتبر است. لطفاً شماره موبایل را دقیقاً با فرمت 09xxxxxxxxx وارد کنید:")
        bot.register_next_step_handler(msg, process_phone_step, pid)
        return
    
    # ذخیره شماره در دیتابیس
    update_user_phone(message.from_user.id, phone)
    bot.send_message(cid, "✅ شماره شما با موفقیت ثبت شد.")
    ask_for_confirmation(cid, pid)

def ask_for_confirmation(cid, pid):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ بله، درخواست ثبت شود", callback_data=f"confirm_visit_{pid}"),
        InlineKeyboardButton("❌ انصراف", callback_data="cancel_visit")
    )
    bot.send_message(cid, "آیا از درخواست بازدید برای این ملک اطمینان دارید؟ مشاور با شما تماس خواهد گرفت.", reply_markup=markup)

# تابع کمکی برای چک کردن درخواست تکراری (در DLL.py اضافه کن)
def is_visit_request_pending(user_id, pid):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM visit_requests WHERE user_id = %s AND property_id = %s AND status = 'pending' LIMIT 1",
        (user_id, pid)
    )
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result is not None

# ---------------- HELPERS ----------------

def normalize_number(text):
    # تبدیل اعداد فارسی/عربی به انگلیسی
    persian_numbers = '۰۱۲۳۴۵۶۷۸۹'
    arabic_numbers = '٠١٢٣٤٥٦٧٨٩'
    english_numbers = '0123456789'
    
    translation_table = str.maketrans(persian_numbers + arabic_numbers, english_numbers * 2)
    clean_text = text.translate(translation_table).replace(',', '').replace('،', '').strip()
    
    return int(clean_text) if clean_text.isdigit() else None


# ---------------- LISTENER ----------------

def info_listener(messages):
    for message in messages:
        user_id = message.chat.id
        username = message.chat.username or "No Username"
        text = message.text or f"[{message.content_type}]"
        
        print(f"\n--- [New Message] ---")
        print(f"👤 User: {username} ({user_id})")
        print(f"💬 Content: {text}")
        print(f"----------------------\n")
bot.set_update_listener(info_listener)

# ---------------- RUN BOT ----------------

print("robot is runing")
bot.infinity_polling()