import mysql.connector
from mysql.connector import errorcode
from config import DATABASE

def get_connection():
    """
    Establish a connection to the Scouting America MySQL database.

    Returns:
        MySQLConnection: An open database connection.
        None: If the connection attempt fails.
    """
    try:
        return mysql.connector.connect(**DATABASE)

    except mysql.connector.Error as err:

        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Incorrect MySQL username or password.")

        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("The scout_assessment database does not exist.")

        elif err.errno == errorcode.CR_CONN_HOST_ERROR:
            print("Cannot connect to MySQL. Check that the server is running.")

        else:
            print(f"Database connection error: {err}")

        return None
