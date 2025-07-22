import psycopg2
import psycopg2.extras

# Connect to PostgreSQL
connect_to_db = psycopg2.connect(
    database="contactdb",
    user="postgres",
    password="1234",
    host="localhost",
    port="5432",
)
current_db_instance = connect_to_db.cursor(cursor_factory=psycopg2.extras.DictCursor)

# current_db_instance.execute("DROP TABLE IF EXISTS contacts")

create_table_query = """
CREATE TABLE IF NOT EXISTS contacts (
    full_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(10) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(20) NOT NULL
)
"""
current_db_instance.execute(create_table_query)

# Input Section

# First name
while True:
    first_name = input("Enter the first name: ").strip()
    
    if not first_name:
        print("First name is required. Please enter your first name.")
    
    elif not first_name.isalpha():
        print("First name must contain only letters.")
    
    elif len(first_name) < 3:
        print("First name must be at least 3 characters long.")
    
    else:
        break  

    


# Middle name (optional)
middle_name = ""
if input("Do you have a middle name? (yes/no): ").strip().lower() == "yes":
    while True:
        middle_name = input("Enter the middle name: ").strip()
        if middle_name.isalpha():
            break
        print("Enter a valid middle name (only letters)")

# Last name (optional)
last_name = ""
if input("Do you want to enter a last name? (yes/no): ").strip().lower() == "yes":
    while True:
        last_name = input("Enter the last name: ").strip()
        if last_name.isalpha():
            break
        print("Enter a valid last name (only letters)")

# Combine full name
full_name = " ".join(filter(None, [first_name, middle_name, last_name])).strip()
print(" Full Name:", full_name)

# Phone number
while True:
    phone_number = input("Enter a 10-digit phone number: ").strip()
    if phone_number.isdigit() and len(phone_number) == 10:
        break
    print("Enter a valid 10-digit phone number")

# Email
while True:
    email = input("Enter your email: ").strip()
    if "@" in email and "." in email and len(email) >= 5:
        break
    print("Enter a valid email")

# Category
valid_categories = ["Work", "Family", "Friends"]
while True:
    category = input("Select category (Work, Friends, Family): ").strip().capitalize()
    if category in valid_categories:
        break
    print("Invalid category. Choose from: Work, Friends, Family")

# insert

insert_query = """
INSERT INTO contacts (full_name, phone_number, email, category)
VALUES (%s, %s, %s, %s)
"""

insert_values = [full_name, phone_number, email, category]

try:
    current_db_instance.execute(insert_query, insert_values)
    connect_to_db.commit()
    print("\n Contact saved successfully.\n")
except psycopg2.Error as e:
    print(" Error inserting contact:", e)
    connect_to_db.rollback()

#  Show All Contacts 

print(" All Contacts in DB:")
current_db_instance.execute("SELECT phone_number FROM contacts where full_name=%s", ('prabhat singh' ,))
contact_list = current_db_instance.fetchall()

for contact in contact_list:
    print(dict(contact)) 

# Close the connection
connect_to_db.close()
