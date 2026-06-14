import telebot
import mysql.connector
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from Texts import texts
from config import BOT_TOKEN, DATABASE_CONFIG, DB_NAME, ADMIN_IDS

telebot.apihelper.API_URL="http://tapi.bale.ai/bot{0}/{1}"

bot = telebot.TeleBot(BOT_TOKEN)

# ---------------- DATABASE ----------------

def get_connection():
    return mysql.connector.connect(database=DB_NAME,**DATABASE_CONFIG)

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
            (telegram_id, username, first_name)
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