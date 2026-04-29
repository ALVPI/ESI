import psycopg2
from psycopg2 import pool
from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT


def create_connection():
    """
    Creates a single database connection.
    """

    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )


def create_connection_pool(minconn=1, maxconn=5):
    """
    Creates a connection pool.

    minconn = minimum connections
    maxconn = maximum connections
    """

    return pool.SimpleConnectionPool(
        minconn,
        maxconn,
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )


def get_connection(connection_pool):
    """
    Gets a connection from pool.
    """
    return connection_pool.getconn()


def release_connection(connection_pool, connection):
    """
    Returns connection to pool.
    """
    connection_pool.putconn(connection)