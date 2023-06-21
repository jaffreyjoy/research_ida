import os
import psycopg2
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Database connection details
db_host = "localhost"
db_port = 5432
db_name = "tpch"
db_user = "jaffrey"
db_password = "jaff"

# Get the folder path from the environment variable
folder_path = os.getenv("DSS_PATH")

# Connect to the PostgreSQL database
conn = psycopg2.connect(
    host=db_host,
    port=db_port,
    database=db_name,
    user=db_user,
    password=db_password
)

# Get a cursor object
cursor = conn.cursor()

# Get a list of .tbl files in the folder
tbl_files = [f for f in os.listdir(folder_path) if f.endswith('.tbl')]

# Iterate over each .tbl file
for tbl_file in tbl_files:
    table_name = os.path.splitext(tbl_file)[0]

    # Prepare the file path
    file_path = os.path.join(folder_path, tbl_file)

    # Remove the last '|' character from each line and write back to the file
    with open(file_path, "r") as file:
        lines = [line.replace("|\n","\n") for line in file]
    with open(file_path, "w") as file:
        file.write("".join(lines))

    # Open the modified file and execute the COPY command
    with open(file_path, "r") as file:
        with conn.cursor() as cursor:
            cursor.copy_from(file, table_name, sep="|", null="")

    print(f"Data imported from {tbl_file} into table {table_name}")

# Commit the changes
conn.commit()

# Close the cursor and database connection
cursor.close()
conn.close()
