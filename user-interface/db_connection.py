import mysql.connector
from mysql.connector import errorcode
from config import DATABASE

def get_connection():
    '''
    Connect to the MySQL database using the settings in config.py.
    Prints the reason and returns None if the connection fails.

    Returns:
        cnx (mysql connection object) - open database connection,
            or None on failure
    '''
    try:
        # unpack config dict into keyword arguments
        return mysql.connector.connect(**DATABASE)
    # report the most common failure causes in plain language
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
        return None
