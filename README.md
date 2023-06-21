# Testing for irrelevant data access in postgres

## Steps:

### 1. Install postgres
This is also present as a script file in the root directory named `install_postgres.sh`
```sh
# Create the file repository configuration:
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'

# Import the repository signing key:
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Update the package lists:
sudo apt-get update

# Install the latest version of PostgreSQL.
# If you want a specific version, use 'postgresql-12' or similar instead of 'postgresql':
sudo apt-get -y install postgresql
```

### 2. Get the latest version of the TPC-H zip file from the Dwnloads section of https://www.tpc.org/tpch/ or clone the repo https://github.com/gregrahn/tpch-kit (it contains tpc-h 2.17.3)

If you download the github repo just follow the instructions in it

For the zip file downloaded from the tpc.org website do the following:
1. Extract contents
2. Make the following changes to `tpcd.h` in the `dbgen` dir
```diff
...
/*
 * database portability defines
 */

+// added from https://github.com/gregrahn/tpch-kit/blob/master/dbgen/tpcd.h
+#ifdef POSTGRESQL
+#define GEN_QUERY_PLAN "explain"
+#define START_TRAN "start transaction"
+#define END_TRAN "commit;"
+#define SET_OUTPUT ""
+#define SET_ROWCOUNT "limit %d;\n"
+#define SET_DBASE ""
+#endif /* POSTGRESQL */
+// added from https://github.com/gregrahn/tpch-kit/blob/master/dbgen/tpcd.h

#ifdef VECTORWISE
#define GEN_QUERY_PLAN  "EXPLAIN"
...

```
3. Make a copy of the `makefile.suite` present in the `dbgen` dir and rename it to `Makefile`
4. Make the following changes to it
```diff
...
################
## CHANGE NAME OF ANSI COMPILER HERE
################
-CC      =
+CC      = gcc
# Current values for DATABASE are: INFORMIX, DB2, TDAT (Teradata)
#                                  SQLSERVER, SYBASE, ORACLE, VECTORWISE
# Current values for MACHINE are:  ATT, DOS, HP, IBM, ICL, MVS,
#                                  SGI, SUN, U2200, VMS, LINUX, WIN32
# Current values for WORKLOAD are:  TPCH
-DATABASE =
+DATABASE = POSTGRESQL
-MACHINE =
+MACHINE = LINUX
-WORKLOAD =
+WORKLOAD = TPCH
#
CFLAGS	= -g -DDBNAME=\"dss\" -D$(MACHINE) -D$(DATABASE) -D$(WORKLOAD) -DRNG_TEST -D_FILE_OFFSET_BITS=64
LDFLAGS = -O
...
```

### 3. Run `make` in the `dbgen` dir
```sh
make MACHINE=LINUX DATABASE=POSTGRESQL
```

### 4. Set environment variables and add the `dbgen`/`qgen` utililty path env var to `$PATH`

Add the below to the `.bashrc` file and run `source ~/.bashrc` to use the `dbgen`/`qgen` utility from any path in the system.
```sh

#------------------------------------------------------------------------------
# TPC-H ENV VARS
#------------------------------------------------------------------------------

# export DSS_CONFIG=/.../tpch-kit/dbgen
# export DSS_QUERY=$DSS_CONFIG/queries
# export DSS_PATH=/path-to-dir-for-output-files

export DSS_CONFIG=/home/jaffrey/research/irrelevant_data_access/tpch_3_0_1/dbgen
export DSS_QUERY=$DSS_CONFIG/queries
export DSS_PATH=/home/jaffrey/research/irrelevant_data_access/op_files

PATH=$PATH:$DSS_CONFIG

```


### 5. Run `dbgen` with scaling factor(`-s`) as 0.1 i. e. 100MB or 1 for 1GB so on...
Output will be present in the path assigned to the `$DSS_CONFIG` env var
```sh
dbgen -s 0.1
```


### 6. Run `qgen` with scaling factor(`-s`) as 0.1 i. e. 100MB or 1 for 1GB so on... (use the same as `dbgen`)
```sh
qgen -v -c -d -s 0.1 > tpch-stream_s0.1.sql
```

### 7. Create the "db schema" using the `dss.ddl` file present in the `dbgen` dir
NOTE: Not the literal schema, but the empty tables with their appropriate col data types.
1. Create a database called tpch
    ```sql
    CREATE DATABASE tpch
    ```
2. Run the DDL script to create teh empty tables
    ```sh
    # psql -U username -d database_name -f /path/to/sql_file.sql
    psql -U jaffrey -d tpch -f $DSS_CONFIG/dss.ddl
    ```

### 8. Load the data generated
Install `python-dotenv` and `psycopg2` using `pip` and enter the appropriate username, password and database name in the below script (also present in `import_data.py`) and run it.

```py
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
```

NOTE: If an error occurs installing psycopg2 try running the below script and then try installing the pip package:
```sh
sudo apt-get install libpq-dev python3-dev
```


