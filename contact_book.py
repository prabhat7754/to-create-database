import os
import re
import datetime
import psycopg2
from getpass import getpass

# --- Configuration ---
DB_CONFIG = {
    "dbname": "contact",
    "user": "postgres",
    "password": "",  # leave blank to prompt
    "host": "localhost",
    "port": "5432",
}

# --- DB Connection ---
def connect_db():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None

# --- Setup password ---
def setup_database_password():
    if not DB_CONFIG['password']:
        DB_CONFIG['password'] = getpass("Enter PostgreSQL password: ")

# --- Create DB & Table ---
def create_database():
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            host=DB_CONFIG["host"]
        )
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_CONFIG["dbname"],))
        if not cur.fetchone():
            cur.execute(f"CREATE DATABASE {DB_CONFIG['dbname']}")
            print(f"✅ Database '{DB_CONFIG['dbname']}' created.")
        else:
            print(f"✅ Database '{DB_CONFIG['dbname']}' exists.")

        cur.close()
        conn.close()

        # Connect to the new DB and create table
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                phone VARCHAR(20) NOT NULL UNIQUE,
                email VARCHAR(100),
                category VARCHAR(50) CHECK (category IN ('friend', 'family', 'work', 'other')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_contacted DATE
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_name ON contacts (name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_phone ON contacts (phone)")
        conn.commit()
        print("✅ Table 'contacts' is ready.")
    except Exception as e:
        print(f"❌ DB Setup Error: {e}")
    finally:
        if cur: cur.close()
        if conn: conn.close()

# --- Validators ---
def validate_phone(phone):
    return re.match(r"^\+?[0-9]{7,15}$", phone)

def validate_email(email):
    if not email:
        return True
    return re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email)

# --- Add Contact ---
def add_contact():
    print("\n--- ➕ Add New Contact ---")
    name = input("Name: ").strip()
    while not name:
        name = input("Name cannot be empty. Enter Name: ").strip()

    phone = input("Phone: ").strip()
    while not validate_phone(phone):
        phone = input("Invalid phone. Enter again: ").strip()

    email = input("Email (optional): ").strip()
    while email and not validate_email(email):
        email = input("Invalid email. Enter again: ").strip()

    print("Categories: friend, family, work, other")
    category = input("Category: ").strip().lower()
    while category not in ["friend", "family", "work", "other"]:
        category = input("Choose valid category: ").strip().lower()

    last_contacted = None
    if input("Add last contacted date? (y/n): ").lower() == 'y':
        try:
            last_contacted = datetime.datetime.strptime(input("Enter (YYYY-MM-DD): "), "%Y-%m-%d").date()
        except ValueError:
            print("❌ Invalid date format.")

    conn = connect_db()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO contacts (name, phone, email, category, last_contacted)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, phone, email, category, last_contacted))
        conn.commit()
        print(f"✅ Contact '{name}' added.")
    except psycopg2.errors.UniqueViolation:
        print("❌ Contact with this phone already exists.")
        conn.rollback()
    except Exception as e:
        print(f"❌ Failed to add: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

# --- View Contacts ---
def view_contacts():
    print("\n--- 📖 View Contacts ---")
    print("1. Name A-Z\n2. Name Z-A\n3. Newest First\n4. Oldest First\n5. Category")
    order = input("Sort by (1-5): ").strip() or "1"

    ordering = {
        "1": "name ASC",
        "2": "name DESC",
        "3": "created_at DESC",
        "4": "created_at ASC",
        "5": "category, name"
    }.get(order, "name ASC")

    conn = connect_db()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT id, name, phone, email, category, last_contacted
            FROM contacts ORDER BY {ordering}
        """)
        contacts = cur.fetchall()
        if not contacts:
            print("📭 No contacts found.")
        else:
            print(f"{'ID':<4} {'Name':<20} {'Phone':<15} {'Email':<25} {'Category':<10} {'Last Contacted'}")
            print("-" * 90)
            for c in contacts:
                print(f"{c[0]:<4} {c[1]:<20} {c[2]:<15} {c[3] or '':<25} {c[4]:<10} {c[5] or 'Never'}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        cur.close()
        conn.close()

# --- Search ---
def search_contact():
    print("\n--- 🔍 Search Contacts ---")
    term = input("Enter name or phone: ").strip()
    if not term:
        print("❌ Search term cannot be empty.")
        return

    conn = connect_db()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, phone, email, category FROM contacts
            WHERE name ILIKE %s OR phone ILIKE %s
        """, (f"%{term}%", f"%{term}%"))
        results = cur.fetchall()
        if not results:
            print("📭 No results.")
        else:
            for c in results:
                print(f"ID: {c[0]}, Name: {c[1]}, Phone: {c[2]}, Email: {c[3] or ''}, Category: {c[4]}")
    except Exception as e:
        print(f"❌ Search error: {e}")
    finally:
        cur.close()
        conn.close()

# --- Delete ---
def delete_contact():
    print("\n--- 🗑 Delete Contact ---")
    view_contacts()
    try:
        cid = int(input("Enter ID to delete (0 to cancel): "))
        if cid == 0:
            return
    except ValueError:
        print("❌ Invalid number.")
        return

    conn = connect_db()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM contacts WHERE id = %s", (cid,))
        row = cur.fetchone()
        if not row:
            print("❌ No contact with that ID.")
            return
        if input(f"Delete '{row[0]}'? (y/n): ").lower() != 'y':
            return
        cur.execute("DELETE FROM contacts WHERE id = %s", (cid,))
        conn.commit()
        print(f"✅ Deleted '{row[0]}'")
    except Exception as e:
        print(f"❌ Deletion error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

# --- Statistics ---
def get_stats():
    print("\n📊 Contact Stats")
    conn = connect_db()
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM contacts")
        print("📁 Total:", cur.fetchone()[0])

        cur.execute("SELECT category, COUNT(*) FROM contacts GROUP BY category")
        for row in cur.fetchall():
            print(f"  {row[0].capitalize()}: {row[1]}")

        cur.execute("SELECT name, created_at FROM contacts ORDER BY created_at DESC LIMIT 5")
        print("\n🆕 Recently added:")
        for name, created in cur.fetchall():
            print(f"  {name} - {created.strftime('%Y-%m-%d')}")

        cur.execute("""
            SELECT name, last_contacted FROM contacts
            WHERE last_contacted IS NULL OR last_contacted < CURRENT_DATE - INTERVAL '6 months'
        """)
        neglected = cur.fetchall()
        print("\n📌 Need follow-up:")
        for name, date in neglected:
            print(f"  {name} - {date.strftime('%Y-%m-%d') if date else 'Never'}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        cur.close()
        conn.close()

# --- Main Menu ---
def main_menu():
    while True:
        print("\n" + "=" * 50)
        print("📒 CONTACT BOOK APPLICATION")
        print("=" * 50)
        print("1. Add New Contact")
        print("2. View All Contacts")
        print("3. Search Contacts")
        print("4. Delete Contact")
        print("5. View Statistics")
        print("6. Exit")

        choice = input("Choose (1-6): ").strip()
        if choice == '1': add_contact()
        elif choice == '2': view_contacts()
        elif choice == '3': search_contact()
        elif choice == '4': delete_contact()
        elif choice == '5': get_stats()
        elif choice == '6':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice.")

# --- Entry Point ---
if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    print("🔧 Initializing Contact Book...")
    setup_database_password()
    create_database()
    main_menu()
