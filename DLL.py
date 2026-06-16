import mysql.connector
from config import DATABASE_CONFIG, DB_NAME


def drop_n_create_database(DB_NAME):
    conn = mysql.connector.connect(**DATABASE_CONFIG)
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {DB_NAME};")
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME};")
    conn.commit()
    cur.close()
    conn.close()
    print(f'database {DB_NAME} created successfully')

def create_table_user(database_name):
    conn = mysql.connector.connect(**DATABASE_CONFIG, database=database_name)
    cur = conn.cursor()
    SQL_Query = """
    CREATE TABLE USERS (
    id INT AUTO_INCREMENT PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    name VARCHAR(100),
    username VARCHAR(100),
    phone VARCHAR(20),
    is_blocked BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

    """
    cur.execute(SQL_Query)
    conn.commit()
    cur.close()
    conn.close()

def create_table_admin(database_name):
    conn = mysql.connector.connect(**DATABASE_CONFIG, database=database_name)
    cur = conn.cursor()
    SQL_Query = """
CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    name VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE
);

    """
    cur.execute(SQL_Query)
    conn.commit()
    cur.close()
    conn.close()

def create_table_properties(database_name):
    conn = mysql.connector.connect(**DATABASE_CONFIG, database=database_name)
    cur = conn.cursor()
    SQL_Query = """
CREATE TABLE properties (
    id INT AUTO_INCREMENT PRIMARY KEY,
    type ENUM('buy','rent') NOT NULL,
    price BIGINT NULL,
    deposit BIGINT NULL,
    rent BIGINT NULL,
    metraj INT,
    rooms INT,
    title VARCHAR(255),
    description TEXT,
    status ENUM('available','sold','inactive') DEFAULT 'available',
    admin_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES admins(id)
);


    """
    cur.execute(SQL_Query)
    conn.commit()
    cur.close()
    conn.close()

def create_table_property_images(database_name):
    conn = mysql.connector.connect(**DATABASE_CONFIG, database=database_name)
    cur = conn.cursor()
    SQL_Query = """
CREATE TABLE property_images (
    id INT AUTO_INCREMENT PRIMARY KEY,
    property_id INT NOT NULL,
    telegram_file_id VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);


    """
    cur.execute(SQL_Query)
    conn.commit()
    cur.close()
    conn.close()

def create_table_visit_requests(database_name):
    conn = mysql.connector.connect(**DATABASE_CONFIG, database=database_name)
    cur = conn.cursor()
    SQL_Query = """
    CREATE TABLE visit_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    property_id INT NOT NULL,
    user_id INT NOT NULL,
    request_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('pending','accepted','rejected') DEFAULT 'pending',
    admin_id INT NULL,
    scheduled_time DATETIME NULL,
    admin_message TEXT NULL,
    is_successful_deal BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (property_id) REFERENCES properties(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (admin_id) REFERENCES admins(id)
);
    """
    cur.execute(SQL_Query)
    conn.commit()
    cur.close()
    conn.close()

# ─── Admin helper functions ───────────────────────────────────────

def get_connection():
    return mysql.connector.connect(**DATABASE_CONFIG, database=DB_NAME)

def get_admin_level(telegram_id):
    """
    Returns: 'superuser' | 'admin' | None
    """
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT is_superuser FROM admins WHERE telegram_id = %s AND is_active = TRUE LIMIT 1",
        (telegram_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return 'superuser' if row['is_superuser'] else 'admin'

def get_all_admins():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, telegram_id, name, is_active, is_superuser, created_at FROM admins ORDER BY created_at")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def add_admin(telegram_id, name, is_superuser_flag=False):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO admins (telegram_id, name, is_superuser)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            name         = VALUES(name),
            is_active    = TRUE,
            is_superuser = VALUES(is_superuser)
        """,
        (telegram_id, name, is_superuser_flag)
    )
    conn.commit()
    cur.close()
    conn.close()

def deactivate_admin(telegram_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE admins SET is_active = FALSE WHERE telegram_id = %s", (telegram_id,))
    conn.commit()
    affected = cur.rowcount
    cur.close()
    conn.close()
    return affected > 0

def get_stats():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    stats = {}
    cur.execute("SELECT COUNT(*) AS c FROM users")
    stats['total_users'] = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM users WHERE is_blocked = TRUE")
    stats['blocked_users'] = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM users WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)")
    stats['new_users_30d'] = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM properties WHERE status = 'available'")
    stats['available_props'] = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM properties WHERE status = 'sold'")
    stats['sold_props'] = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM visit_requests WHERE status = 'pending'")
    stats['pending_visits'] = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM visit_requests WHERE is_successful_deal = TRUE")
    stats['successful_deals'] = cur.fetchone()['c']
    cur.close()
    conn.close()
    return stats

if __name__ == "__main__":
    drop_n_create_database(DB_NAME)
    create_table_user(DB_NAME)
    create_table_admin(DB_NAME)
    create_table_properties(DB_NAME)
    create_table_property_images(DB_NAME)
    create_table_visit_requests(DB_NAME)