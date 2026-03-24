from db_connection import create_connection
from scheduler import run_scheduler


def main():
    """
    Entry point of the monitoring system.
    """

    conn = None

    try:
        print("Starting system monitor...")

        # Create database connection
        conn = create_connection()

        print("Database connection established.")

        # Start scheduler loop
        run_scheduler(conn)

    except Exception as e:
        print(f"[FATAL ERROR] {e}")

    finally:
        # Ensure connection is closed properly
        if conn:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    main()
