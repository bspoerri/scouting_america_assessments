import mysql.connector
from mysql.connector import Error

try:
    # 1. Establish the connection
    connection = mysql.connector.connect(
        host="localhost",       # Or your server IP address
        user="root",            # Your MySQL username
        password="",
        database="your_database"
    )

    if connection.is_connected():
        # 2. Create a cursor object to run queries
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM your_table;")

        # 3. Fetch and display the results
        rows = cursor.fetchall()
        for row in rows:
            print(row)

except Error as e:
    print(f"Error connecting to MySQL: {e}")

finally:
    # 4. Always close the cursor and connection
    if 'connection' in locals() and connection.is_connected():
        cursor.close()
        connection.close()