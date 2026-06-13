import mysql.connector




def create_database():
    conn = mysql.connector.connect(**database_config, database=database_name)
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE real_estate_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
                  USE real_estate_bot;")

    conn.commit()
    cur.close()
    conn.close()
    print (f"database {db_name} created")


def create_table_user():
    conn = mysql.connector.connect(**database_config, database=database_name)
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



def create_table_user():
    conn = mysql.connector.connect(**database_config, database=database_name)
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




def create_table_user():
    conn = mysql.connector.connect(**database_config, database=database_name)
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











def create_table_user():
    conn = mysql.connector.connect(**database_config, database=database_name)
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





def create_table_user():
    conn = mysql.connector.connect(**database_config, database=database_name)
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



