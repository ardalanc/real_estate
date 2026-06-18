import telebot
import mysql.connector
import re
import logging
import os
from datetime import datetime
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from Texts import texts
from config import BOT_TOKEN, DATABASE_CONFIG, DB_NAME, ADMIN_IDS
from DLL import get_admin_level, get_all_admins, add_admin, deactivate_admin, get_stats
import logging.handlers

# ─── Logging Setup ────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.handlers.RotatingFileHandler("logs/bot.log", maxBytes=5*1024*1024, backupCount=3, encoding="utf-8"),
        logging.StreamHandler()         
    ]
)
logger = logging.getLogger(__name__)
# ──────────────────────────────────────────────────────────────────

telebot.apihelper.API_URL="http://tapi.bale.ai/bot{0}/{1}"

bot = telebot.TeleBot(BOT_TOKEN)
logger.info("Bot instance created.")

# ---------------- DATABASE ----------------

def get_connection():
    return mysql.connector.connect(database=DB_NAME,**DATABASE_CONFIG)

# -- visit request --

def update_user_name(telegram_id, name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET name = %s WHERE telegram_id = %s", (name, telegram_id))
    conn.commit()
    affected = cur.rowcount
    cur.close()
    conn.close()
    return affected > 0

def get_user_visit_requests(user_db_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    query = """
        SELECT vr.id, vr.status, vr.request_time, vr.scheduled_time, vr.admin_message,
               p.title, p.type, p.price, p.deposit, p.rent
        FROM visit_requests vr
        JOIN properties p ON vr.property_id = p.id
        WHERE vr.user_id = %s
        ORDER BY vr.request_time DESC
    """
    cur.execute(query, (user_db_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

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
        KeyboardButton(texts["btn_buy"]),
        KeyboardButton(texts["btn_rent"])
    )
    markup.add(KeyboardButton(texts["btn_more"]))
    return markup

def admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton(texts["btn_add_property"]),
        KeyboardButton(texts["btn_manage_properties"])
    )
    markup.add(
        KeyboardButton(texts["btn_visit_requests"]),
        KeyboardButton(texts["btn_broadcast"])           
    )
    return markup

def superuser_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton(texts["btn_add_property"]),
        KeyboardButton(texts["btn_manage_properties"])
    )
    markup.add(
        KeyboardButton(texts["btn_visit_requests"]),
        KeyboardButton(texts["btn_broadcast"])
    )
    # ردیف اختصاصی سوپر یوزر
    markup.add(
        KeyboardButton(texts["btn_manage_users"]),
        KeyboardButton(texts["btn_manage_admins"])
    )
    markup.add(KeyboardButton(texts["btn_stats"]))
    return markup

def more_menu_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(texts["btn_profile"],    callback_data="profile_show"),
        InlineKeyboardButton(texts["btn_contact_us"], callback_data="contact_us"),
        InlineKeyboardButton(texts["btn_guide"],      callback_data="guide"),
        InlineKeyboardButton(texts["btn_support"],    callback_data="support"),
        InlineKeyboardButton(texts["btn_about_us"],   callback_data="about_us"),
    )
    return markup

def profile_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(texts["btn_edit_phone"], callback_data="profile_edit_phone"),
        InlineKeyboardButton(texts["btn_edit_name"],  callback_data="profile_edit_name"),
        InlineKeyboardButton(texts["btn_my_visits"],  callback_data="profile_my_visits"),
    )
    return markup

def buy_options_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    btn_all    = InlineKeyboardButton(texts["btn_buy_all"],       callback_data="buy_show_all")
    btn_budget = InlineKeyboardButton(texts["btn_buy_by_budget"], callback_data="buy_by_budget")
    markup.add(btn_all, btn_budget)
    return markup

def rent_options_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(texts["btn_rent_all"],        callback_data="rent_all"),
        InlineKeyboardButton(texts["btn_rent_by_deposit"], callback_data="rent_by_deposit"),
        InlineKeyboardButton(texts["btn_rent_by_monthly"], callback_data="rent_by_monthly"),
        InlineKeyboardButton(texts["btn_rent_by_combo"],   callback_data="rent_by_combo")
    )
    return markup

# ---------------- START ----------------

@bot.message_handler(commands=['start'])
def start_handler(message):
    cid = message.chat.id
    level = get_admin_level(cid)
    username = message.from_user.username or "—"
    logger.info(f"[START] user={cid} (@{username}) level={level or 'user'}")

    if level == 'superuser':
        bot.send_message(cid, texts["welcome"], reply_markup=superuser_menu())
        return

    if level == 'admin':
        bot.send_message(cid, texts["welcome"], reply_markup=admin_menu())
        return

    register_user(message)
    bot.send_message(cid, texts["welcome"], reply_markup=main_menu())

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
        logger.info(f"[REGISTER] new user registered: id={cid} username=@{username or '—'} name={first_name or '—'}")
    else:
        logger.debug(f"[REGISTER] existing user: id={cid}")

    cur.close()
    conn.close()

def is_admin(cid):
    return get_admin_level(cid) is not None

def is_superuser(cid):
    return get_admin_level(cid) == 'superuser'

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
# -- more --
@bot.message_handler(func=lambda message: message.text == texts["btn_more"])
def more_handler(message):
    bot.send_message(message.chat.id, texts["more_choose"], reply_markup=more_menu_markup())

# -- buy --
@bot.message_handler(func=lambda message: message.text == texts["btn_buy"])
def buy_handler(message):
    cid = message.chat.id
    bot.send_message(cid, texts["buy_choose_mode"], reply_markup=buy_options_markup())

# ---------------- CALLBACK HANDLER ----------------
# -- buy --

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def buy_callback_handler(call):
    cid = call.message.chat.id
    if call.data == "buy_show_all":
        show_properties(cid, mode='all')
    
    elif call.data == "buy_by_budget":
        msg = bot.send_message(cid, texts["buy_ask_min_budget"])
        bot.register_next_step_handler(msg, process_min_budget)

# -- rent --

@bot.message_handler(func=lambda message: message.text == texts["btn_rent"])
def rent_handler(message):
    bot.send_message(message.chat.id, texts["rent_choose_mode"], reply_markup=rent_options_markup())

@bot.callback_query_handler(func=lambda call: call.data.startswith('rent_'))
def rent_callback_handler(call):
    cid = call.message.chat.id
    if call.data == "rent_all":
        show_rent_properties(cid, mode='all')
    
    elif call.data == "rent_by_deposit":
        msg = bot.send_message(cid, texts["rent_ask_min_deposit"])
        bot.register_next_step_handler(msg, process_deposit_step, "min")

    elif call.data == "rent_by_monthly":
        msg = bot.send_message(cid, texts["rent_ask_min_monthly"])
        bot.register_next_step_handler(msg, process_rent_step, "min")

    elif call.data == "rent_by_combo":
        msg = bot.send_message(cid, texts["rent_combo_start"])
        bot.register_next_step_handler(msg, process_combo_step, {"step": 1})

# -- profile --

STATUS_FA = {
    'pending':  texts["status_pending"],
    'accepted': texts["status_accepted"],
    'rejected': texts["status_rejected"],
}

@bot.callback_query_handler(func=lambda call: call.data.startswith("profile_"))
def profile_callback_handler(call):
    cid = call.message.chat.id
    telegram_id = call.from_user.id

    if call.data == "profile_show":
        user = get_user_by_telegram_id(telegram_id)
        if not user:
            bot.answer_callback_query(call.id, texts["profile_not_found"])
            return

        name     = user.get('name') or '—'
        username = f"@{user['username']}" if user.get('username') else '—'
        phone    = user.get('phone') or texts["profile_not_registered"]
        joined   = user['created_at'].strftime('%Y/%m/%d') if user.get('created_at') else '—'

        text = texts["profile_text"].format(name=name, username=username, phone=phone, joined=joined)
        bot.send_message(cid, text, parse_mode='Markdown', reply_markup=profile_markup())

    elif call.data == "profile_edit_phone":
        msg = bot.send_message(cid, texts["profile_ask_phone"])
        bot.register_next_step_handler(msg, process_profile_phone_step)

    elif call.data == "profile_edit_name":
        msg = bot.send_message(cid, texts["profile_ask_name"])
        bot.register_next_step_handler(msg, process_profile_name_step)

    elif call.data == "profile_my_visits":
        user_db_id = get_user_id_by_telegram_id(telegram_id)
        if not user_db_id:
            bot.answer_callback_query(call.id, texts["profile_not_found"])
            return

        requests = get_user_visit_requests(user_db_id)

        if not requests:
            bot.send_message(cid, texts["profile_no_visits"])
            return

        bot.send_message(cid, texts["profile_visits_header"].format(count=len(requests)), parse_mode='Markdown')

        for req in requests:
            status_fa = STATUS_FA.get(req['status'], req['status'])
            prop_type = texts["prop_type_buy"] if req['type'] == 'buy' else texts["prop_type_rent"]

            if req['type'] == 'buy':
                price_line = f"💰 قیمت: {req['price']:,} تومان" if req.get('price') else ""
            else:
                price_line = (
                    f"💰 ودیعه: {req['deposit']:,} تومان\n"
                    f"💸 اجاره: {req['rent']:,} تومان"
                ) if req.get('deposit') else ""

            scheduled = ""
            if req.get('scheduled_time'):
                scheduled = texts["profile_visit_scheduled"].format(
                    scheduled_time=req['scheduled_time'].strftime('%Y/%m/%d %H:%M')
                )

            admin_msg = ""
            if req.get('admin_message'):
                admin_msg = texts["profile_visit_admin_msg"].format(admin_message=req['admin_message'])

            text = (
                texts["profile_visit_item"].format(
                    title=req['title'],
                    prop_type=prop_type,
                    price_line=price_line,
                    status_fa=status_fa,
                    request_time=req['request_time'].strftime('%Y/%m/%d')
                ) + scheduled + admin_msg
            )
            bot.send_message(cid, text, parse_mode='Markdown')

# -- profile steps --

def process_profile_phone_step(message):
    cid = message.chat.id
    phone = normalize_phone_number(message.text)
    if not phone:
        msg = bot.send_message(cid, texts["profile_invalid_phone"])
        bot.register_next_step_handler(msg, process_profile_phone_step)
        return
    update_user_phone(message.from_user.id, phone)
    bot.send_message(cid, texts["profile_phone_updated"].format(phone=phone))

def process_profile_name_step(message):
    cid = message.chat.id
    name = message.text.strip()
    if len(name) < 2 or len(name) > 50:
        msg = bot.send_message(cid, texts["profile_invalid_name"])
        bot.register_next_step_handler(msg, process_profile_name_step)
        return
    update_user_name(message.from_user.id, name)
    bot.send_message(cid, texts["profile_name_updated"].format(name=name))

# -- visit request --

@bot.callback_query_handler(func=lambda call: call.data.startswith("visit_"))
def handle_visit_request(call):
    cid = call.message.chat.id
    pid = call.data.split('_')[1] # Property ID
    logger.info(f"[VISIT_REQUEST] user={cid} property_id={pid}")
    
    # چک کردن شماره تلفن در دیتابیس
    user = get_user_by_telegram_id(call.from_user.id) # تابعی که قبلا گفتی داری
    
    if not user or not user.get('phone'):
        logger.info(f"[VISIT_REQUEST] user={cid} has no phone, requesting phone number")
        msg = bot.send_message(cid, texts["visit_ask_phone"])
        bot.register_next_step_handler(msg, process_phone_step, pid)
    else:
        ask_for_confirmation(cid, pid)

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_visit_") or call.data == "cancel_visit")
def handle_visit_confirmation(call):
    cid = call.message.chat.id
    
    if call.data == "cancel_visit":
        logger.info(f"[VISIT_CANCEL] user={cid} cancelled visit request")
        bot.answer_callback_query(call.id, texts["visit_cancelled"])
        bot.delete_message(cid, call.message.message_id)
        return

    pid = int(call.data.split('_')[2])
    user_db_id = get_user_id_by_telegram_id(call.from_user.id)

    if not user_db_id:
        logger.warning(f"[VISIT_CONFIRM] user={cid} not found in DB")
        bot.answer_callback_query(call.id, texts["visit_user_not_found"])
        return

    # چک کردن اینکه آیا درخواست پندینگ قبلی وجود داره یا نه
    if is_visit_request_pending(user_db_id, pid):
        logger.info(f"[VISIT_CONFIRM] user={cid} already has pending request for property={pid}")
        bot.answer_callback_query(call.id, texts["visit_already_pending"])
        bot.send_message(cid, texts["visit_already_pending_msg"])
    else:
        # ثبت در دیتابیس (property_id اول، user_id دوم)
        request_id = create_visit_request(pid, user_db_id)
        logger.info(f"[VISIT_CONFIRM] new visit request created: id={request_id} user={cid} property={pid}")
        bot.answer_callback_query(call.id, texts["visit_success_toast"])
        bot.edit_message_text(texts["visit_success_msg"], cid, call.message.message_id)

# ---------------- FUNCTION ----------------
# -- buy --

def process_min_budget(message):
    cid = message.chat.id
    if not message.text.isdigit():
        msg = bot.send_message(cid, texts["buy_invalid_number"])
        bot.register_next_step_handler(msg, process_min_budget)
        return
    
    min_price = int(message.text)
    msg = bot.send_message(cid, texts["buy_ask_max_budget"].format(min_price=min_price))
    bot.register_next_step_handler(msg, process_max_budget, min_price)

def process_max_budget(message, min_price):
    cid = message.chat.id
    if not message.text.isdigit():
        msg = bot.send_message(cid, texts["buy_invalid_max"])
        bot.register_next_step_handler(msg, process_max_budget, min_price)
        return
    
    max_price = int(message.text)
    bot.send_message(cid, texts["buy_searching"].format(min_price=min_price, max_price=max_price))
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
        bot.send_message(cid, texts["buy_not_found"])
    else:
        for row in rows:
            caption = texts["buy_caption"].format(
                title=row['title'],
                price=row['price'],
                metraj=row['metraj'],
                rooms=row['rooms'],
                description=row['description']
            )
            
            # پیدا کردن عکس‌های ملک از جدول property_images
            cursor.execute("SELECT telegram_file_id FROM property_images WHERE property_id = %s LIMIT 1", (row['id'],))
            img_row = cursor.fetchone()
            
            # دکمه درخواست بازدید
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(texts["btn_visit_request"], callback_data=f"visit_{row['id']}"))
            
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
        msg = bot.send_message(cid, texts["rent_invalid_number"])
        bot.register_next_step_handler(msg, process_deposit_step, type_mode, min_val)
        return

    if type_mode == "min":
        msg = bot.send_message(cid, texts["rent_ask_max_deposit"].format(val=val))
        bot.register_next_step_handler(msg, process_deposit_step, "max", val)
    else:
        show_rent_properties(cid, mode='deposit', filters={'min_dep': min_val, 'max_dep': val})

def process_rent_step(message, type_mode, min_val=None):
    cid = message.chat.id
    val = normalize_number(message.text)
    if val is None:
        msg = bot.send_message(cid, texts["rent_invalid_number"])
        bot.register_next_step_handler(msg, process_rent_step, type_mode, min_val)
        return

    if type_mode == "min":
        msg = bot.send_message(cid, texts["rent_ask_max_monthly"].format(val=val))
        bot.register_next_step_handler(msg, process_rent_step, "max", val)
    else:
        show_rent_properties(cid, mode='rent_val', filters={'min_rent': min_val, 'max_rent': val})

def process_combo_step(message, data):
    cid = message.chat.id
    val = normalize_number(message.text)
    if val is None:
        msg = bot.send_message(cid, texts["rent_invalid_combo"])
        bot.register_next_step_handler(msg, process_combo_step, data)
        return

    step = data['step']
    if step == 1:
        data.update({'min_dep': val, 'step': 2})
        msg = bot.send_message(cid, texts["rent_combo_ask_max_deposit"])
        bot.register_next_step_handler(msg, process_combo_step, data)
    elif step == 2:
        data.update({'max_dep': val, 'step': 3})
        msg = bot.send_message(cid, texts["rent_combo_ask_min_monthly"])
        bot.register_next_step_handler(msg, process_combo_step, data)
    elif step == 3:
        data.update({'min_rent': val, 'step': 4})
        msg = bot.send_message(cid, texts["rent_combo_ask_max_monthly"])
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
        bot.send_message(cid, texts["rent_not_found"])
    else:
        for row in rows:
            caption = texts["rent_caption"].format(
                title=row['title'],
                deposit=row['deposit'],
                rent=row['rent'],
                metraj=row['metraj'],
                rooms=row['rooms'],
                description=row['description']
            )
            
            # دریافت تصویر اول
            cursor.execute("SELECT telegram_file_id FROM property_images WHERE property_id = %s LIMIT 1", (row['id'],))
            img = cursor.fetchone()
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(texts["btn_visit_request"], callback_data=f"visit_{row['id']}"))

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
        logger.warning(f"[PHONE_STEP] user={cid} entered invalid phone: '{message.text}'")
        msg = bot.send_message(cid, texts["visit_invalid_phone"])
        bot.register_next_step_handler(msg, process_phone_step, pid)
        return
    
    # ذخیره شماره در دیتابیس
    update_user_phone(message.from_user.id, phone)
    logger.info(f"[PHONE_STEP] user={cid} phone saved: {phone}")
    bot.send_message(cid, texts["visit_phone_saved"])
    ask_for_confirmation(cid, pid)

def ask_for_confirmation(cid, pid):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(texts["btn_confirm_visit"], callback_data=f"confirm_visit_{pid}"),
        InlineKeyboardButton(texts["btn_cancel_visit"],  callback_data="cancel_visit")
    )
    bot.send_message(cid, texts["visit_confirm_question"], reply_markup=markup)

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
    
    if not clean_text.isdigit():
        return None
    val = int(clean_text)
    # حداکثر مقدار مجاز: ۹۹۹ میلیارد تومان (در محدوده BIGINT MySQL)
    MAX_VALUE = 999_000_000_000
    if val > MAX_VALUE:
        return None
    return val

# ================ ADMIN PANEL ================

# -- درخواست های بازدید (ادمین) --

@bot.message_handler(func=lambda m: m.text == texts["btn_visit_requests"] and is_admin(m.chat.id))
def admin_visit_requests(message):
    cid = message.chat.id
    logger.info(f"[ADMIN_VISITS] admin={cid} opened visit requests panel")
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT vr.id, vr.status, vr.request_time,
               u.name AS user_name, u.phone AS user_phone, u.telegram_id AS user_tid,
               p.title AS prop_title
        FROM visit_requests vr
        JOIN users u ON vr.user_id = u.id
        JOIN properties p ON vr.property_id = p.id
        WHERE vr.status = 'pending'
        ORDER BY vr.request_time ASC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    logger.info(f"[ADMIN_VISITS] admin={cid} found {len(rows)} pending requests")

    if not rows:
        bot.send_message(cid, texts["admin_no_pending_visits"])
        return

    bot.send_message(cid, texts["admin_pending_visits_header"].format(count=len(rows)), parse_mode='Markdown')
    for req in rows:
        text = texts["admin_visit_item"].format(
            prop_title=req['prop_title'],
            user_name=req['user_name'] or '—',
            user_phone=req['user_phone'] or texts["admin_visit_no_phone"],
            request_time=req['request_time'].strftime('%Y/%m/%d %H:%M')
        )
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton(texts["btn_accept_visit"], callback_data=f"vr_accept_{req['id']}"),
            InlineKeyboardButton(texts["btn_reject_visit"], callback_data=f"vr_reject_{req['id']}"),
        )
        bot.send_message(cid, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("vr_accept_") or c.data.startswith("vr_reject_"))
def admin_handle_visit(call):
    cid = call.message.chat.id
    if not is_admin(cid):
        return
    parts  = call.data.split("_")
    action = parts[1]
    vr_id  = int(parts[2])
    logger.info(f"[ADMIN_VISIT_ACTION] admin={cid} action={action} visit_request_id={vr_id}")

    if action == "accept":
        msg = bot.send_message(cid, texts["admin_ask_visit_time"])
        bot.register_next_step_handler(msg, admin_set_visit_time, vr_id)
    else:
        msg = bot.send_message(cid, texts["admin_ask_reject_reason"])
        bot.register_next_step_handler(msg, admin_reject_visit, vr_id)
    bot.delete_message(cid, call.message.message_id)

def admin_set_visit_time(message, vr_id):
    cid = message.chat.id
    scheduled = message.text.strip()
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT u.telegram_id AS user_tid, p.title
        FROM visit_requests vr
        JOIN users u ON vr.user_id = u.id
        JOIN properties p ON vr.property_id = p.id
        WHERE vr.id = %s
    """, (vr_id,))
    row = cur.fetchone()
    cur.execute("""
        UPDATE visit_requests
        SET status = 'accepted', admin_message = %s,
            admin_id = (SELECT id FROM admins WHERE telegram_id = %s LIMIT 1)
        WHERE id = %s
    """, (texts["admin_visit_accepted_db"].format(scheduled=scheduled), cid, vr_id))
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"[VISIT_ACCEPTED] admin={cid} visit_request_id={vr_id} scheduled='{scheduled}' user_tid={row['user_tid'] if row else '?'}")
    bot.send_message(cid, texts["admin_visit_accepted"].format(scheduled=scheduled))
    if row:
        bot.send_message(
            row['user_tid'],
            texts["admin_visit_accepted_user"].format(title=row['title'], scheduled=scheduled),
            parse_mode='Markdown'
        )


def admin_reject_visit(message, vr_id):
    cid = message.chat.id
    reason = message.text.strip()
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT u.telegram_id AS user_tid, p.title
        FROM visit_requests vr
        JOIN users u ON vr.user_id = u.id
        JOIN properties p ON vr.property_id = p.id
        WHERE vr.id = %s
    """, (vr_id,))
    row = cur.fetchone()
    cur.execute("""
        UPDATE visit_requests
        SET status = 'rejected', admin_message = %s,
            admin_id = (SELECT id FROM admins WHERE telegram_id = %s LIMIT 1)
        WHERE id = %s
    """, (reason if reason != '—' else None, cid, vr_id))
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"[VISIT_REJECTED] admin={cid} visit_request_id={vr_id} reason='{reason}' user_tid={row['user_tid'] if row else '?'}")
    bot.send_message(cid, texts["admin_visit_rejected_admin"])
    if row:
        user_text = texts["admin_visit_rejected_user"].format(title=row['title'])
        if reason != '—':
            user_text += texts["admin_visit_rejected_reason"].format(reason=reason)
        bot.send_message(row['user_tid'], user_text, parse_mode='Markdown')

# ================ افزودن فایل جدید ================

@bot.message_handler(func=lambda m: m.text == texts["btn_add_property"] and is_admin(m.chat.id))
def admin_add_property_start(message):
    cid = message.chat.id
    logger.info(f"[ADD_PROPERTY] admin={cid} started adding new property")
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(texts["btn_prop_type_buy"],  callback_data="newprop_type_buy"),
        InlineKeyboardButton(texts["btn_prop_type_rent"], callback_data="newprop_type_rent"),
    )
    bot.send_message(cid, texts["admin_choose_prop_type"], reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("newprop_type_"))
def admin_add_property_type(call):
    cid = call.message.chat.id
    if not is_admin(cid):
        return
    prop_type = call.data.split("_")[2]  # buy | rent
    bot.delete_message(cid, call.message.message_id)
    msg = bot.send_message(cid, texts["admin_ask_title"])
    bot.register_next_step_handler(msg, admin_add_property_title, {"type": prop_type})

def admin_add_property_title(message, data):
    cid = message.chat.id
    title = message.text.strip()
    if not title:
        msg = bot.send_message(cid, texts["admin_empty_title"])
        bot.register_next_step_handler(msg, admin_add_property_title, data)
        return
    data['title'] = title
    msg = bot.send_message(cid, texts["admin_ask_description"])
    bot.register_next_step_handler(msg, admin_add_property_description, data)

def admin_add_property_description(message, data):
    cid = message.chat.id
    data['description'] = message.text.strip()
    msg = bot.send_message(cid, texts["admin_ask_metraj"])
    bot.register_next_step_handler(msg, admin_add_property_metraj, data)

def admin_add_property_metraj(message, data):
    cid = message.chat.id
    val = normalize_number(message.text)
    if val is None:
        msg = bot.send_message(cid, texts["admin_invalid_metraj"])
        bot.register_next_step_handler(msg, admin_add_property_metraj, data)
        return
    data['metraj'] = val
    msg = bot.send_message(cid, texts["admin_ask_rooms"])
    bot.register_next_step_handler(msg, admin_add_property_rooms, data)

def admin_add_property_rooms(message, data):
    cid = message.chat.id
    val = normalize_number(message.text)
    if val is None or val < 0:
        msg = bot.send_message(cid, texts["admin_invalid_rooms"])
        bot.register_next_step_handler(msg, admin_add_property_rooms, data)
        return
    data['rooms'] = val

    if data['type'] == 'buy':
        msg = bot.send_message(cid, texts["admin_ask_price"])
        bot.register_next_step_handler(msg, admin_add_property_price, data)
    else:
        msg = bot.send_message(cid, texts["admin_ask_deposit"])
        bot.register_next_step_handler(msg, admin_add_property_deposit, data)

def admin_add_property_price(message, data):
    cid = message.chat.id
    val = normalize_number(message.text)
    if val is None or val <= 0:
        msg = bot.send_message(cid, texts["admin_invalid_price"])
        bot.register_next_step_handler(msg, admin_add_property_price, data)
        return
    data['price'] = val
    data['deposit'] = None
    data['rent'] = None
    data['photos'] = []
    _pending_property_data[cid] = data
    msg = bot.send_message(
        cid,
        texts["admin_ask_photos"],
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton(texts["btn_photos_done"], callback_data="newprop_photos_done")
        )
    )
    bot.register_next_step_handler(msg, admin_add_property_photo, data)

def admin_add_property_deposit(message, data):
    cid = message.chat.id
    val = normalize_number(message.text)
    if val is None or val < 0:
        msg = bot.send_message(cid, texts["admin_invalid_deposit"])
        bot.register_next_step_handler(msg, admin_add_property_deposit, data)
        return
    data['deposit'] = val
    msg = bot.send_message(cid, texts["admin_ask_rent"])
    bot.register_next_step_handler(msg, admin_add_property_rent, data)

def admin_add_property_rent(message, data):
    cid = message.chat.id
    val = normalize_number(message.text)
    if val is None or val < 0:
        msg = bot.send_message(cid, texts["admin_invalid_rent"])
        bot.register_next_step_handler(msg, admin_add_property_rent, data)
        return
    data['rent'] = val
    data['price'] = None
    data['photos'] = []
    _pending_property_data[cid] = data
    msg = bot.send_message(
        cid,
        texts["admin_ask_photos"],
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton(texts["btn_photos_done"], callback_data="newprop_photos_done")
        )
    )
    bot.register_next_step_handler(msg, admin_add_property_photo, data)

_pending_property_data = {}

@bot.callback_query_handler(func=lambda c: c.data == "newprop_photos_done")
def admin_add_property_photos_done(call):
    cid = call.message.chat.id
    if not is_admin(cid):
        return

    # پاک کردن next_step_handler در انتظار تا پیام‌های بعدی (منو و ...) اشتباه پردازش نشوند
    bot.clear_step_handler_by_chat_id(cid)

    # داده‌های این ادمین از next_step جاری قابل دسترس نیست؛ از dict موقت استفاده می‌کنیم
    data = _pending_property_data.get(cid)
    if not data:
        bot.answer_callback_query(call.id, texts["admin_no_pending_data"])
        return

    _save_property_and_notify(cid, call.message.message_id, data)

def admin_add_property_photo(message, data):
    """Override: ثبت عکس‌ها و ذخیره data در dict موقت"""
    cid = message.chat.id

    # اگر کاربر قبلاً «اتمام» را زده و property ذخیره شده، این handler را نادیده بگیر
    if cid not in _pending_property_data:
        return

    _pending_property_data[cid] = data  # همیشه آخرین وضعیت ذخیره شود

    if message.content_type == 'photo':
        file_id = message.photo[-1].file_id
        data['photos'].append(file_id)
        count = len(data['photos'])
        msg = bot.send_message(
            cid,
            texts["admin_photo_received"].format(count=count),
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton(texts["btn_photos_done"], callback_data="newprop_photos_done")
            )
        )
        bot.register_next_step_handler(msg, admin_add_property_photo, data)
    else:
        msg = bot.send_message(
            cid,
            texts["admin_photo_only"],
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton(texts["btn_photos_done"], callback_data="newprop_photos_done")
            )
        )
        bot.register_next_step_handler(msg, admin_add_property_photo, data)

def _save_property_and_notify(cid, msg_id, data):
    conn = get_connection()
    cur = conn.cursor()

    price   = data.get('price')   if data.get('price')   else None
    deposit = data.get('deposit') if data.get('deposit') else None
    rent    = data.get('rent')    if data.get('rent')    else None

    cur.execute("""
        INSERT INTO properties (type, price, deposit, rent, metraj, rooms, title, description, status, admin_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'available',
                (SELECT id FROM admins WHERE telegram_id = %s LIMIT 1))
    """, (
        data['type'], price, deposit, rent,
        data['metraj'], data['rooms'], data['title'], data['description'], cid
    ))
    conn.commit()
    prop_id = cur.lastrowid

    for file_id in data.get('photos', []):
        cur.execute(
            "INSERT INTO property_images (property_id, telegram_file_id) VALUES (%s, %s)",
            (prop_id, file_id)
        )
    conn.commit()
    cur.close()
    conn.close()

    photos_count = len(data.get('photos', []))
    logger.info(f"[PROPERTY_SAVED] admin={cid} property_id={prop_id} type={data['type']} title='{data['title']}' photos={photos_count}")

    _pending_property_data.pop(cid, None)

    type_fa = texts["admin_prop_type_buy_fa"] if data['type'] == 'buy' else texts["admin_prop_type_rent_fa"]
    bot.send_message(
        cid,
        texts["admin_property_saved"].format(
            title=data['title'],
            type_fa=type_fa,
            metraj=data['metraj'],
            rooms=data['rooms'],
            photos_count=photos_count
        ),
        reply_markup=admin_menu() if not is_superuser(cid) else superuser_menu()
    )

# ================ مدیریت فایل‌ها ================

@bot.message_handler(func=lambda m: m.text == texts["btn_manage_properties"] and is_admin(m.chat.id))
def admin_manage_properties(message):
    cid = message.chat.id
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(texts["btn_manage_buy"],  callback_data="mgprop_list_buy"),
        InlineKeyboardButton(texts["btn_manage_rent"], callback_data="mgprop_list_rent"),
    )
    markup.add(InlineKeyboardButton(texts["btn_manage_all"], callback_data="mgprop_list_all"))
    bot.send_message(cid, texts["admin_choose_prop_filter"], reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("mgprop_list_"))
def admin_manage_list(call):
    cid = call.message.chat.id
    if not is_admin(cid):
        return
    # mgprop_list_buy → ['mgprop', 'list', 'buy']
    filter_type = call.data.split("_", 2)[2]  # buy | rent | all
    bot.delete_message(cid, call.message.message_id)

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    if filter_type == 'all':
        cur.execute("SELECT id, title, type, status FROM properties ORDER BY created_at DESC LIMIT 40")
    else:
        cur.execute(
            "SELECT id, title, type, status FROM properties WHERE type=%s ORDER BY created_at DESC LIMIT 40",
            (filter_type,)
        )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        bot.send_message(cid, texts["admin_no_properties"])
        return

    markup = InlineKeyboardMarkup(row_width=1)
    STATUS_ICON = {'available': '🟢', 'sold': '🔵', 'inactive': '🔴'}
    TYPE_FA = {'buy': texts["admin_prop_type_buy_fa"], 'rent': texts["admin_prop_type_rent_fa"]}
    for r in rows:
        icon = STATUS_ICON.get(r['status'], '⚪')
        label = f"{icon} [{TYPE_FA.get(r['type'], r['type'])}] {r['title']}"
        markup.add(InlineKeyboardButton(label, callback_data=f"mgprop_detail_{r['id']}"))
    bot.send_message(cid, texts["admin_properties_header"].format(count=len(rows)), reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("mgprop_detail_"))
def admin_manage_detail(call):
    cid = call.message.chat.id
    if not is_admin(cid):
        return
    # mgprop_detail_12 → split("_", 2) = ['mgprop', 'detail', '12']
    parts = call.data.split("_", 2)
    if len(parts) < 3 or not parts[2].isdigit():
        bot.answer_callback_query(call.id, texts["admin_invalid_data"])
        return
    prop_id = int(parts[2])

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM properties WHERE id = %s", (prop_id,))
    p = cur.fetchone()
    cur.execute("SELECT COUNT(*) AS cnt FROM property_images WHERE property_id = %s", (prop_id,))
    img_cnt = cur.fetchone()['cnt']
    cur.close()
    conn.close()

    if not p:
        bot.answer_callback_query(call.id, texts["admin_prop_not_found"])
        return

    STATUS_FA_MAP = {
        'available': texts["admin_prop_status_available"],
        'sold':      texts["admin_prop_status_sold"],
        'inactive':  texts["admin_prop_status_inactive"]
    }
    TYPE_FA_MAP = {
        'buy':  texts["admin_prop_type_buy_fa"],
        'rent': texts["admin_prop_type_rent_fa"]
    }
    type_fa = TYPE_FA_MAP.get(p['type'], p['type'])

    if p['type'] == 'buy':
        price_line = texts["admin_prop_price_line_buy"].format(price=p['price']) if p.get('price') else texts["admin_prop_price_line_buy_empty"]
    else:
        deposit = p.get('deposit') or 0
        rent    = p.get('rent')    or 0
        price_line = texts["admin_prop_price_line_rent"].format(deposit=deposit, rent=rent)

    text = texts["admin_prop_detail"].format(
        title=p['title'],
        type_fa=type_fa,
        price_line=price_line,
        metraj=p['metraj'],
        rooms=p['rooms'],
        status_fa=STATUS_FA_MAP.get(p['status'], p['status']),
        img_cnt=img_cnt,
        description=p['description']
    )

    markup = InlineKeyboardMarkup(row_width=2)
    if p['status'] != 'available':
        markup.add(InlineKeyboardButton(texts["btn_status_available"],  callback_data=f"mgprop_status_{prop_id}_available"))
    if p['status'] != 'sold':
        markup.add(InlineKeyboardButton(texts["btn_status_sold"],       callback_data=f"mgprop_status_{prop_id}_sold"))
    if p['status'] != 'inactive':
        markup.add(InlineKeyboardButton(texts["btn_status_inactive"],   callback_data=f"mgprop_status_{prop_id}_inactive"))
    markup.add(InlineKeyboardButton(texts["btn_edit_title"],            callback_data=f"mgprop_edit_title_{prop_id}"))
    markup.add(InlineKeyboardButton(texts["btn_edit_desc"],             callback_data=f"mgprop_edit_desc_{prop_id}"))
    markup.add(InlineKeyboardButton(texts["btn_edit_price"],            callback_data=f"mgprop_edit_price_{prop_id}"))
    markup.add(InlineKeyboardButton(texts["btn_manage_photos"],         callback_data=f"mgprop_photos_{prop_id}"))
    markup.add(InlineKeyboardButton(texts["btn_delete_property"],       callback_data=f"mgprop_delete_{prop_id}"))

    bot.send_message(cid, text, parse_mode='Markdown', reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("mgprop_edit_price_"))
def admin_edit_price_start(call):
    cid = call.message.chat.id
    if not is_admin(cid):
        return
    # "mgprop_edit_price_12" → split("_", 3) → ['mgprop', 'edit', 'price', '12']
    parts = call.data.split("_", 3)
    if len(parts) < 4 or not parts[3].isdigit():
        bot.answer_callback_query(call.id, texts["admin_invalid_data"])
        return
    prop_id = int(parts[3])

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT type FROM properties WHERE id=%s", (prop_id,))
    p = cur.fetchone()
    cur.close()
    conn.close()

    if not p:
        bot.answer_callback_query(call.id, texts["admin_prop_not_found"])
        return

    if p['type'] == 'buy':
        msg = bot.send_message(cid, texts["admin_ask_new_price"])
        bot.register_next_step_handler(msg, admin_edit_price_save, prop_id, 'buy')
    else:
        msg = bot.send_message(cid, texts["admin_ask_new_deposit"])
        bot.register_next_step_handler(msg, admin_edit_deposit_save, prop_id)


# -- تغییر وضعیت --

@bot.callback_query_handler(func=lambda c: c.data.startswith("mgprop_status_"))
def admin_change_status(call):
    cid = call.message.chat.id
    if not is_admin(cid):
        return
    # "mgprop_status_12_available" → split("_", 3) → ['mgprop', 'status', '12', 'available']
    parts = call.data.split("_", 3)
    if len(parts) < 4:
        bot.answer_callback_query(call.id, texts["admin_invalid_data"])
        return
    if not parts[2].isdigit():
        bot.answer_callback_query(call.id, texts["admin_invalid_prop_id"])
        return
    prop_id    = int(parts[2])
    new_status = parts[3]
    VALID_STATUSES = ('available', 'sold', 'inactive')
    if new_status not in VALID_STATUSES:
        bot.answer_callback_query(call.id, texts["admin_invalid_status"])
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE properties SET status=%s WHERE id=%s", (new_status, prop_id))
    conn.commit()
    cur.close()
    conn.close()

    STATUS_FA_MAP = {
        'available': texts["admin_prop_status_available"],
        'sold':      texts["admin_prop_status_sold"],
        'inactive':  texts["admin_prop_status_inactive"]
    }
    logger.info(f"[CHANGE_STATUS] prop_id={prop_id} new_status={new_status}")
    bot.answer_callback_query(call.id, texts["admin_status_changed"].format(status_fa=STATUS_FA_MAP.get(new_status)))
    bot.delete_message(cid, call.message.message_id)


# -- ویرایش عنوان --

@bot.callback_query_handler(func=lambda c: c.data.startswith("mgprop_edit_title_"))
def admin_edit_title_start(call):
    cid = call.message.chat.id
    if not is_admin(cid):
        return
    # "mgprop_edit_title_12" → split("_", 3) → ['mgprop', 'edit', 'title', '12']
    parts = call.data.split("_", 3)
    if len(parts) < 4 or not parts[3].isdigit():
        bot.answer_callback_query(call.id, texts["admin_invalid_data"])
        return
    prop_id = int(parts[3])
    msg = bot.send_message(cid, texts["admin_ask_new_title"])
    bot.register_next_step_handler(msg, admin_edit_title_save, prop_id)

def admin_edit_title_save(message, prop_id):
    cid = message.chat.id
    new_title = message.text.strip()
    if not new_title:
        msg = bot.send_message(cid, texts["admin_empty_new_title"])
        bot.register_next_step_handler(msg, admin_edit_title_save, prop_id)
        return
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE properties SET title=%s WHERE id=%s", (new_title, prop_id))
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"[EDIT_TITLE] prop_id={prop_id} new_title='{new_title}'")
    bot.send_message(cid, texts["admin_title_updated"].format(new_title=new_title))

# -- ویرایش توضیحات --

@bot.callback_query_handler(func=lambda c: c.data.startswith("mgprop_edit_desc_"))
def admin_edit_desc_start(call):
    cid = call.message.chat.id
    if not is_admin(cid):
        return
    # "mgprop_edit_desc_12" → split("_", 3) → ['mgprop', 'edit', 'desc', '12']
    parts = call.data.split("_", 3)
    if len(parts) < 4 or not parts[3].isdigit():
        bot.answer_callback_query(call.id, texts["admin_invalid_data"])
        return
    prop_id = int(parts[3])
    msg = bot.send_message(cid, texts["admin_ask_new_desc"])
    bot.register_next_step_handler(msg, admin_edit_desc_save, prop_id)



def admin_edit_desc_save(message, prop_id):
    cid = message.chat.id
    new_desc = message.text.strip()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE properties SET description=%s WHERE id=%s", (new_desc, prop_id))
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"[EDIT_DESC] prop_id={prop_id}")
    bot.send_message(cid, texts["admin_desc_updated"])

# -- ویرایش قیمت --

@bot.callback_query_handler(func=lambda call: call.data.startswith("visit_"))
def handle_visit_request(call):
    cid = call.message.chat.id
    # ✅ FIX: pid را به int تبدیل کن تا در confirm_visit_{pid} عدد درست ساخته شود
    pid = int(call.data.split('_')[1])
    logger.info(f"[VISIT_REQUEST] user={cid} property_id={pid}")

    user = get_user_by_telegram_id(call.from_user.id)

    if not user or not user.get('phone'):
        logger.info(f"[VISIT_REQUEST] user={cid} has no phone, requesting phone number")
        msg = bot.send_message(cid, texts["visit_ask_phone"])
        bot.register_next_step_handler(msg, process_phone_step, pid)
    else:
        ask_for_confirmation(cid, pid)


def admin_edit_price_save(message, prop_id, prop_type):
    cid = message.chat.id
    val = normalize_number(message.text)
    if val is None or val <= 0:
        msg = bot.send_message(cid, texts["admin_invalid_new_price"])
        bot.register_next_step_handler(msg, admin_edit_price_save, prop_id, prop_type)
        return
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE properties SET price=%s WHERE id=%s", (val, prop_id))
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"[EDIT_PRICE] prop_id={prop_id} new_price={val}")
    bot.send_message(cid, texts["admin_price_updated"].format(val=val))

def admin_edit_deposit_save(message, prop_id):
    cid = message.chat.id
    val = normalize_number(message.text)
    if val is None or val < 0:
        msg = bot.send_message(cid, texts["admin_invalid_new_price"])
        bot.register_next_step_handler(msg, admin_edit_deposit_save, prop_id)
        return
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE properties SET deposit=%s WHERE id=%s", (val, prop_id))
    conn.commit()
    cur.close()
    conn.close()
    msg = bot.send_message(cid, texts["admin_deposit_saved"].format(val=val))
    bot.register_next_step_handler(msg, admin_edit_rent_save, prop_id)

def admin_edit_rent_save(message, prop_id):
    cid = message.chat.id
    val = normalize_number(message.text)
    if val is None or val < 0:
        msg = bot.send_message(cid, texts["admin_invalid_new_price"])
        bot.register_next_step_handler(msg, admin_edit_rent_save, prop_id)
        return
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE properties SET rent=%s WHERE id=%s", (val, prop_id))
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"[EDIT_RENT] prop_id={prop_id} new_rent={val}")
    bot.send_message(cid, texts["admin_rent_updated"].format(val=val))


# -- مدیریت عکس‌ها --

@bot.callback_query_handler(func=lambda c: c.data.startswith("mgprop_photos_"))
def admin_manage_photos(call):
    cid = call.message.chat.id
    if not is_admin(cid):
        return
    parts = call.data.split("_", 2)
    if len(parts) < 3 or not parts[2].isdigit():
        bot.answer_callback_query(call.id, texts["admin_invalid_data"])
        return
    prop_id = int(parts[2])

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, telegram_file_id FROM property_images WHERE property_id=%s ORDER BY id", (prop_id,))
    imgs = cur.fetchall()
    cur.close()
    conn.close()

    if not imgs:
        markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton(texts["btn_add_photo"], callback_data=f"mgprop_addphoto_{prop_id}")
        )
        bot.send_message(cid, texts["admin_no_photos"], reply_markup=markup)
        return

    bot.send_message(cid, texts["admin_photos_header"].format(count=len(imgs)), parse_mode='Markdown')
    for img in imgs:
        markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton(texts["btn_delete_photo"], callback_data=f"mgprop_delphoto_{img['id']}_{prop_id}")
        )
        try:
            bot.send_photo(cid, img['telegram_file_id'], reply_markup=markup)
        except Exception:
            bot.send_message(cid, texts["admin_photo_not_displayable"].format(img_id=img['id']), reply_markup=markup)

    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton(texts["btn_add_new_photo"], callback_data=f"mgprop_addphoto_{prop_id}")
    )
    bot.send_message(cid, texts["admin_add_photo_prompt"], reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("mgprop_delphoto_"))
def admin_delete_photo(call):
    cid = call.message.chat.id
    if not is_admin(cid):
        return
    # "mgprop_delphoto_5_12" → split("_", 3) → ['mgprop', 'delphoto', '5', '12']
    parts = call.data.split("_", 3)
    if len(parts) < 4 or not parts[2].isdigit() or not parts[3].isdigit():
        bot.answer_callback_query(call.id, texts["admin_invalid_data"])
        return
    img_id  = int(parts[2])
    prop_id = int(parts[3])

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM property_images WHERE id=%s", (img_id,))
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"[DELETE_PHOTO] img_id={img_id} prop_id={prop_id} by admin={cid}")
    bot.answer_callback_query(call.id, texts["admin_photo_deleted"])
    bot.delete_message(cid, call.message.message_id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("mgprop_addphoto_"))
def admin_add_photo_start(call):
    cid = call.message.chat.id
    if not is_admin(cid):
        return
    parts = call.data.split("_", 2)
    if len(parts) < 3 or not parts[2].isdigit():
        bot.answer_callback_query(call.id, texts["admin_invalid_data"])
        return
    prop_id = int(parts[2])
    msg = bot.send_message(cid, texts["admin_ask_new_photo"])
    bot.register_next_step_handler(msg, admin_add_photo_save, prop_id)


def admin_add_photo_save(message, prop_id):
    cid = message.chat.id
    if message.content_type != 'photo':
        msg = bot.send_message(cid, texts["admin_photo_only_error"])
        bot.register_next_step_handler(msg, admin_add_photo_save, prop_id)
        return
    file_id = message.photo[-1].file_id
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO property_images (property_id, telegram_file_id) VALUES (%s, %s)",
        (prop_id, file_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"[ADD_PHOTO] prop_id={prop_id} by admin={cid}")
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton(texts["btn_add_another_photo"], callback_data=f"mgprop_addphoto_{prop_id}")
    )
    bot.send_message(cid, texts["admin_photo_added"], reply_markup=markup)

# -- حذف فایل --

@bot.callback_query_handler(func=lambda c: c.data.startswith("mgprop_delete_") and not c.data.startswith("mgprop_confirmdelete_"))
def admin_delete_property_confirm(call):
    cid = call.message.chat.id
    if not is_admin(cid):
        return
    parts = call.data.split("_", 2)
    if len(parts) < 3 or not parts[2].isdigit():
        bot.answer_callback_query(call.id, texts["admin_invalid_data"])
        return
    prop_id = int(parts[2])
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(texts["btn_confirm_delete"], callback_data=f"mgprop_confirmdelete_{prop_id}"),
        InlineKeyboardButton(texts["btn_cancel_delete"],  callback_data="mgprop_canceldelete"),
    )
    bot.send_message(cid, texts["admin_delete_confirm"], reply_markup=markup)



@bot.callback_query_handler(func=lambda c: c.data.startswith("mgprop_confirmdelete_"))
def admin_delete_property_execute(call):
    cid = call.message.chat.id
    if not is_admin(cid):
        return
    parts = call.data.split("_", 2)
    if len(parts) < 3 or not parts[2].isdigit():
        bot.answer_callback_query(call.id, texts["admin_invalid_data"])
        return
    prop_id = int(parts[2])
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM properties WHERE id=%s", (prop_id,))
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"[DELETE_PROPERTY] prop_id={prop_id} by admin={cid}")
    bot.answer_callback_query(call.id, texts["admin_delete_done_toast"])
    bot.edit_message_text(texts["admin_delete_done_msg"], cid, call.message.message_id)


@bot.callback_query_handler(func=lambda c: c.data == "mgprop_canceldelete")
def admin_cancel_delete(call):
    bot.answer_callback_query(call.id, texts["admin_delete_cancelled"])
    bot.delete_message(call.message.chat.id, call.message.message_id)


# -- ارسال پیام به همه کاربران --

@bot.message_handler(func=lambda m: m.text == texts["btn_broadcast"] and is_admin(m.chat.id))
def admin_broadcast_start(message):
    cid = message.chat.id
    msg = bot.send_message(cid, texts["admin_broadcast_ask"])
    bot.register_next_step_handler(msg, admin_broadcast_send)

def admin_broadcast_send(message):
    cid = message.chat.id
    text = message.text.strip()
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT telegram_id FROM users WHERE is_blocked = FALSE")
    users = cur.fetchall()
    cur.close()
    conn.close()
    sent, failed = 0, 0
    for u in users:
        try:
            bot.send_message(u['telegram_id'], texts["admin_broadcast_template"].format(text=text), parse_mode='Markdown')
            sent += 1
        except Exception:
            failed += 1
    logger.info(f"[BROADCAST] admin={cid} total={len(users)} sent={sent} failed={failed}")
    bot.send_message(cid, texts["admin_broadcast_done"].format(sent=sent, failed=failed))

# ================ SUPERUSER PANEL ================

# -- مدیریت کاربران --

@bot.message_handler(func=lambda m: m.text == texts["btn_manage_users"] and is_superuser(m.chat.id))
def superuser_users(message):
    cid = message.chat.id
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, telegram_id, name, username, phone, is_blocked FROM users ORDER BY created_at DESC LIMIT 30")
    users = cur.fetchall()
    cur.close()
    conn.close()

    if not users:
        bot.send_message(cid, texts["su_no_users"])
        return

    markup = InlineKeyboardMarkup(row_width=1)
    for u in users:
        blocked = "🔴" if u['is_blocked'] else "🟢"
        label   = u['name'] or u['username'] or str(u['telegram_id'])
        markup.add(InlineKeyboardButton(f"{blocked} {label}", callback_data=f"suuser_{u['id']}"))
    bot.send_message(cid, texts["su_users_header"].format(count=len(users)), parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("suuser_"))
def superuser_user_detail(call):
    cid = call.message.chat.id
    if not is_superuser(cid):
        return
    user_id = int(call.data.split("_")[1])
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    u = cur.fetchone()
    cur.execute("SELECT COUNT(*) AS cnt FROM visit_requests WHERE user_id = %s", (user_id,))
    visit_cnt = cur.fetchone()['cnt']
    cur.close()
    conn.close()
    if not u:
        bot.answer_callback_query(call.id, texts["su_user_not_found_cb"])
        return
    status = texts["su_user_status_blocked"] if u['is_blocked'] else texts["su_user_status_active"]
    text = texts["su_user_detail"].format(
        name=u['name'] or '—',
        username=u['username'] or '—',
        phone=u['phone'] or texts["su_user_not_found_phone"],
        telegram_id=u['telegram_id'],
        visit_cnt=visit_cnt,
        status=status
    )
    action_btn = (
        InlineKeyboardButton(texts["btn_unblock"], callback_data=f"unblock_{user_id}")
        if u['is_blocked'] else
        InlineKeyboardButton(texts["btn_block"],   callback_data=f"block_{user_id}")
    )
    markup = InlineKeyboardMarkup()
    markup.add(action_btn)
    bot.send_message(cid, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("block_") or c.data.startswith("unblock_"))
def superuser_toggle_block(call):
    cid = call.message.chat.id
    if not is_superuser(cid):
        return
    action  = "block" if call.data.startswith("block_") else "unblock"
    user_id = int(call.data.split("_")[1])
    new_val = True if action == "block" else False
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_blocked = %s WHERE id = %s", (new_val, user_id))
    conn.commit()
    cur.close()
    conn.close()
    label = texts["su_blocked_toast"] if new_val else texts["su_unblocked_toast"]
    logger.info(f"[USER_BLOCK] superuser={cid} action={action} user_db_id={user_id}")
    bot.answer_callback_query(call.id, label)
    bot.delete_message(cid, call.message.message_id)

# -- مدیریت ادمین ها --

@bot.message_handler(func=lambda m: m.text == texts["btn_manage_admins"] and is_superuser(m.chat.id))
def superuser_admins(message):
    cid = message.chat.id
    admins = get_all_admins()
    markup = InlineKeyboardMarkup(row_width=1)
    for a in admins:
        crown  = "👑" if a['is_superuser'] else "🔧"
        active = "✅" if a['is_active']    else "🔴"
        markup.add(InlineKeyboardButton(
            f"{crown} {a['name'] or a['telegram_id']} {active}",
            callback_data=f"suadmin_{a['id']}"
        ))
    markup.add(InlineKeyboardButton(texts["btn_add_admin"], callback_data="suadmin_add"))
    bot.send_message(cid, texts["su_admins_header"].format(count=len(admins)), parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "suadmin_add")
def superuser_add_admin_start(call):
    cid = call.message.chat.id
    if not is_superuser(cid):
        return
    msg = bot.send_message(cid, texts["su_ask_admin_tid"])
    bot.register_next_step_handler(msg, superuser_add_admin_step2)

def superuser_add_admin_step2(message):
    cid = message.chat.id
    if not message.text.strip().isdigit():
        bot.send_message(cid, texts["su_invalid_admin_tid"])
        return
    tid = int(message.text.strip())
    msg = bot.send_message(cid, texts["su_ask_admin_name"])
    bot.register_next_step_handler(msg, superuser_add_admin_step3, tid)

def superuser_add_admin_step3(message, tid):
    cid = message.chat.id
    name = message.text.strip()
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(texts["btn_role_superuser"], callback_data=f"addadmin_{tid}_{name}_super"),
        InlineKeyboardButton(texts["btn_role_admin"],     callback_data=f"addadmin_{tid}_{name}_normal"),
    )
    bot.send_message(cid, texts["su_choose_admin_role"].format(name=name), parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("addadmin_"))
def superuser_confirm_add_admin(call):
    cid = call.message.chat.id
    if not is_superuser(cid):
        return
    # addadmin_{tid}_{name}_{super|normal}
    parts = call.data.split("_", 3)
    tid   = int(parts[1])
    name  = parts[2]
    level = parts[3]
    add_admin(tid, name, is_superuser_flag=(level == "super"))
    label = texts["su_admin_role_superuser"] if level == "super" else texts["su_admin_role_normal"]
    logger.info(f"[ADMIN_ADDED] superuser={cid} new_admin_tid={tid} name='{name}' level={level}")
    bot.answer_callback_query(call.id, texts["su_admin_added_toast"])
    bot.edit_message_text(texts["su_admin_added_msg"].format(name=name, label=label), cid, call.message.message_id, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda c: c.data.startswith("suadmin_") and c.data != "suadmin_add")
def superuser_admin_detail(call):
    cid = call.message.chat.id
    if not is_superuser(cid):
        return
    admin_id = int(call.data.split("_")[1])
    admins = get_all_admins()
    a = next((x for x in admins if x['id'] == admin_id), None)
    if not a:
        bot.answer_callback_query(call.id, texts["su_admin_not_found"])
        return
    crown  = texts["su_admin_role_superuser"] if a['is_superuser'] else texts["su_admin_role_normal"]
    active = texts["su_admin_status_active"]   if a['is_active']   else texts["su_admin_status_inactive"]
    text = texts["su_admin_detail"].format(
        name=a['name'] or '—',
        telegram_id=a['telegram_id'],
        crown=crown,
        active=active
    )
    markup = InlineKeyboardMarkup()
    if a['is_active']:
        markup.add(InlineKeyboardButton(texts["btn_deactivate_admin"], callback_data=f"deactivateadmin_{a['telegram_id']}"))
    bot.send_message(cid, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("deactivateadmin_"))
def superuser_deactivate_admin(call):
    cid = call.message.chat.id
    if not is_superuser(cid):
        return
    tid = int(call.data.split("_")[1])
    deactivate_admin(tid)
    logger.info(f"[ADMIN_DEACTIVATED] superuser={cid} deactivated_admin_tid={tid}")
    bot.answer_callback_query(call.id, texts["su_admin_deactivated_toast"])
    bot.delete_message(cid, call.message.message_id)

# -- آمار و گزارش --

@bot.message_handler(func=lambda m: m.text == texts["btn_stats"] and is_superuser(m.chat.id))
def superuser_stats(message):
    cid = message.chat.id
    s = get_stats()
    text = texts["su_stats"].format(
        total_users=s['total_users'],
        blocked_users=s['blocked_users'],
        new_users_30d=s['new_users_30d'],
        available_props=s['available_props'],
        sold_props=s['sold_props'],
        pending_visits=s['pending_visits'],
        successful_deals=s['successful_deals']
    )
    bot.send_message(cid, text, parse_mode='Markdown')

# ================ ارتباط با ما / راهنما / پشتیبانی / درباره ما ================

# -- تابع کمکی: پیدا کردن سوپریوزر --

def get_superuser_telegram_ids():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT telegram_id FROM admins WHERE is_superuser = TRUE AND is_active = TRUE")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [r['telegram_id'] for r in rows]

# -- callback handler برای چهار بخش --

@bot.callback_query_handler(func=lambda call: call.data in ("contact_us", "guide", "support", "about_us"))
def more_sections_callback(call):
    cid = call.message.chat.id
    telegram_id = call.from_user.id

    # ─── درباره ما ───
    if call.data == "about_us":
        bot.answer_callback_query(call.id)
        bot.send_message(cid, texts["about_us"], parse_mode='Markdown')
        return

    # ─── راهنما ───
    if call.data == "guide":
        bot.answer_callback_query(call.id)
        bot.send_message(cid, texts["guide"], parse_mode='Markdown')
        return

    # ─── پشتیبانی ───
    if call.data == "support":
        bot.answer_callback_query(call.id)
        bot.send_message(cid, texts["support"], parse_mode='Markdown')
        return

    # ─── ارتباط با ما ───
    if call.data == "contact_us":
        bot.answer_callback_query(call.id)
        user = get_user_by_telegram_id(telegram_id)

        if user and user.get('phone'):
            # کاربر شماره دارد: تاییدیه نمایش داده می‌شود
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton(texts["btn_contact_confirm"], callback_data="contact_confirm"),
                InlineKeyboardButton(texts["btn_contact_cancel"],  callback_data="contact_cancel"),
            )
            bot.send_message(
                cid,
                texts["contact_confirm_text"],
                parse_mode='Markdown',
                reply_markup=markup
            )
        else:
            # کاربر شماره ندارد: ابتدا شماره گرفته می‌شود
            msg = bot.send_message(cid, texts["contact_ask_phone"])
            bot.register_next_step_handler(msg, contact_us_phone_step)

def contact_us_phone_step(message):
    cid = message.chat.id
    phone = normalize_phone_number(message.text)
    if not phone:
        msg = bot.send_message(cid, texts["contact_invalid_phone"])
        bot.register_next_step_handler(msg, contact_us_phone_step)
        return
    update_user_phone(message.from_user.id, phone)
    logger.info(f"[CONTACT_US] user={cid} phone saved for contact: {phone}")
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(texts["btn_contact_confirm"], callback_data="contact_confirm"),
        InlineKeyboardButton(texts["btn_contact_cancel"],  callback_data="contact_cancel"),
    )
    bot.send_message(
        cid,
        texts["contact_phone_saved_prefix"] + texts["contact_confirm_text"],
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data in ("contact_confirm", "contact_cancel"))
def contact_us_confirm_callback(call):
    cid = call.message.chat.id
    telegram_id = call.from_user.id

    if call.data == "contact_cancel":
        bot.answer_callback_query(call.id, texts["contact_cancelled"])
        bot.delete_message(cid, call.message.message_id)
        return

    # تأیید شد: اطلاع‌رسانی به کاربر
    bot.answer_callback_query(call.id, texts["contact_request_sent_toast"])
    bot.edit_message_text(
        texts["contact_request_sent_msg"],
        cid,
        call.message.message_id,
        parse_mode='Markdown'
    )

    # ارسال پیام به سوپریوزرها
    user = get_user_by_telegram_id(telegram_id)
    name     = (user.get('name') or '—') if user else '—'
    phone    = (user.get('phone') or texts["contact_not_registered"]) if user else texts["contact_not_registered"]
    username = f"@{user['username']}" if user and user.get('username') else '—'

    notify_text = texts["contact_notify_superuser"].format(
        name=name,
        username=username,
        phone=phone,
        telegram_id=telegram_id
    )

    superuser_ids = get_superuser_telegram_ids()
    logger.info(f"[CONTACT_US] user={cid} phone={phone} notifying {len(superuser_ids)} superuser(s)")
    for su_id in superuser_ids:
        try:
            bot.send_message(su_id, notify_text, parse_mode='Markdown')
        except Exception as e:
            logger.warning(f"[CONTACT_US] failed to notify superuser={su_id}: {e}")

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
        logger.debug(f"[MSG] user={user_id} (@{username}) content={text[:80]}")
bot.set_update_listener(info_listener)

# ---------------- RUN BOT ----------------

print("robot is runing")
logger.info("Bot polling started.")
bot.infinity_polling()