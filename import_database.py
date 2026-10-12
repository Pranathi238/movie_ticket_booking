
import os
import mysql.connector

config = {
    "host": os.environ["DB_HOST"],
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ["DB_USER"],
    "password": os.environ["DB_PASSWORD"],
    "database": os.environ["DB_NAME"],
    "ssl_ca": os.environ.get("DB_SSL_CA") or None,
}

with open("database.sql", "r", encoding="utf-8") as file:
    sql_script = file.read()

connection = mysql.connector.connect(**config)
cursor = connection.cursor()

try:
    for statement in sql_script.split(";"):
        statement = statement.strip()
        if statement and not statement.startswith("--"):
            cursor.execute(statement)

    connection.commit()
    print("Database import completed successfully!")

finally:
    cursor.close()
    connection.close()