import mysql.connector
from config import DATABASE_CONFIG,DB_NAME




def drop_n_create_database():
    conn = mysql.connector.connect(**DATABASE_CONFIG)
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {DB_NAME};")
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME};")
    conn.commit()
    cur.close()
    conn.close()
    print(f'database {DB_NAME} created successfully')

def create_table_user():
    conn = mysql.connector.connect(**DATABASE_CONFIG, database=DB_NAME)
    cur = conn.cursor()
    SQL_Query = """
    CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    first_name VARCHAR(100),
    username VARCHAR(100),
    phone VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_blocked BOOLEAN DEFAULT FALSE
);

    """
    cur.execute(SQL_Query)
    conn.commit()
    cur.close()
    conn.close()
    print("table user created")

def create_table_admins():
    conn = mysql.connector.connect(**DATABASE_CONFIG, database=DB_NAME)
    cur = conn.cursor()
    SQL_Query = """
CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    name VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

    """
    cur.execute(SQL_Query)
    conn.commit()
    cur.close()
    conn.close()
    
    print("table admin created")


def create_table_properties():
    conn = mysql.connector.connect(**DATABASE_CONFIG, database=DB_NAME)
    cur = conn.cursor()
    SQL_Query = """
CREATE TABLE properties (
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    type ENUM('buy','rent') NOT NULL,
    
    price BIGINT NULL,
    deposit BIGINT NULL,
    rent BIGINT NULL,
    
    metr INT,
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
    print("table properties created")


def create_table_property_images():
    conn = mysql.connector.connect(**DATABASE_CONFIG, database=DB_NAME)
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
    print("table property image created")


def create_table_visit_requests():
    conn = mysql.connector.connect(**DATABASE_CONFIG, database=DB_NAME)
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
    
    FOREIGN KEY (property_id) REFERENCES properties(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (admin_id) REFERENCES admins(id)
);


    """
    cur.execute(SQL_Query)
    conn.commit()
    cur.close()
    conn.close()
    print("table visit request created")


if __name__ == "__main__":
    drop_n_create_database()
    create_table_user()
    create_table_admins()
    create_table_properties()
    create_table_property_images()
    create_table_visit_requests()
