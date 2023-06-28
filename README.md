# Testing for irrelevant data access in postgres

## Steps to setup postgres and tpc-h:

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

### 9. Run the generated queries
```sh
psql -U jaffrey -d tpch -f op_queries/tpch-stream_s0.1.sql  > op.log
```
> NOTE: The queries generated may not be syntactically correct...so some changes were needed in my case especially the `LIMIT -1` statement...also query no. 20 had to be refactored to run in a finite amount of time...joins over subqueries made this feasible...idk if the subqueries were done on purpose for benchmarking reasons.


---

</br>

## What I tried to get the number blocks accessed by a query:

So there are multiple ways to do this...
### 1. Using [`pg_stat_statements`](https://www.postgresql.org/docs/current/pgstatstatements.html#id-1.11.7.41.6)
One way is to use the `pg_stat_statements` extension and query the same manually and find the stats for the query you want to analyse. The columns that are of interest to us are `shared_blks_hit`, `shared_blks_read`, `local_blks_hit`, `local_blks_read` ... the sum of which could be considered as the total blocks of data read for the query to be serviced.
ALso to enable the extension make the following changes in the `postgres.conf file`
```diff

# - Shared Library Preloading -

#local_preload_libraries = ''
#session_preload_libraries = ''
-# shared_preload_libraries = ''	# (change requires restart)
+shared_preload_libraries = 'pg_stat_statements'	# (change requires restart)
+compute_query_id = on
+pg_stat_statements.max = 10000
+pg_stat_statements.track = all
#jit_provider = 'llvmjit'		# JIT library to use

```
Restart the postgres service using:
```sh
sudo systemctl restart postgresql
```
Then load the extension using the following statements:
```sql
DROP EXTENSION IF EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
SELECT pg_stat_statements_reset();

```
Run a query and then query the `pg_stat_statements` table to view its stats:
```sql
select * from pg_stat_statements where query like "%c_acctbal%"
```
Output:
```
 userid | dbid  | toplevel |       queryid       |                          query                           | plans | total_plan_time | min_plan_time | max_plan_time | mean_plan_time | stddev_plan_time | calls | total_exec_time | min_exec_time | max_exec_time | mean_exec_time | stddev_exec_time  | rows  | shared_blks_hit | shared_blks_read | shared_blks_dirtied | shared_blks_written | local_blks_hit | local_blks_read | local_blks_dirtied | local_blks_written | temp_blks_read | temp_blks_written | blk_read_time | blk_write_time | temp_blk_read_time | temp_blk_write_time | wal_records | wal_fpi | wal_bytes | jit_functions | jit_generation_time | jit_inlining_count | jit_inlining_time | jit_optimization_count | jit_optimization_time | jit_emission_count | jit_emission_time 
--------+-------+----------+---------------------+----------------------------------------------------------+-------+-----------------+---------------+---------------+----------------+------------------+-------+-----------------+---------------+---------------+----------------+-------------------+-------+-----------------+------------------+---------------------+---------------------+----------------+-----------------+--------------------+--------------------+----------------+-------------------+---------------+----------------+--------------------+---------------------+-------------+---------+-----------+---------------+---------------------+--------------------+-------------------+------------------------+-----------------------+--------------------+-------------------
  16388 | 24581 | t        |   79037308312789606 | select * from customer where c_acctbal between $1 and $2 |     0 |               0 |             0 |             0 |              0 |                0 |     2 |       37.036967 |     13.772915 |     23.264052 |     18.5184835 | 4.745568499999999 | 17001 |               0 |              720 |                   0 |                   0 |              0 |               0 |                  0 |                  0 |              0 |                 0 |      7.652201 |              0 |                  0 |                   0 |           0 |       0 |         0 |             0 |                   0 |                  0 |                 0 |                      0 |                     0 |                  0 |                 0
  16388 | 24581 | t        | 5484391910498440363 | select * from customer where c_acctbal > $1              |     0 |               0 |             0 |             0 |              0 |                0 |     1 |       13.135202 |     13.135202 |     13.135202 |      13.135202 |                 0 |  5415 |             360 |                0 |                   0 |                   0 |              0 |               0 |                  0 |                  0 |              0 |                 0 |             0 |              0 |                  0 |                   0 |           0 |       0 |         0 |             0 |                   0 |                  0 |                 0 |                      0 |                     0 |                  0 |                 0
(2 rows)

```
Data relevant to us:
```
 userid | dbid  | toplevel |       queryid       |                          query                           || rows  | shared_blks_hit | shared_blks_read | local_blks_hit | local_blks_read |
--------+-------+----------+---------------------+----------------------------------------------------------++-------+-----------------+------------------+----------------+-----------------+
  16388 | 24581 | t        |   79037308312789606 | select * from customer where c_acctbal between $1 and $2 || 17001 |               0 |              720 |              0 |               0 |
  16388 | 24581 | t        | 5484391910498440363 | select * from customer where c_acctbal > $1              ||  5415 |             360 |                0 |              0 |               0 |
(2 rows)
```

### 2. Using `EXPLAIN`
Query:
```sql
explain (analyze, verbose, buffers)
select * from customer where c_acctbal > 6000;
```
Output:
```
"Seq Scan on public.customer  (cost=0.00..547.50 rows=5408 width=159) (actual time=0.011..12.570 rows=5415 loops=1)"
"  Output: c_custkey, c_name, c_address, c_nationkey, c_phone, c_acctbal, c_mktsegment, c_comment"
"  Filter: (customer.c_acctbal > '6000'::numeric)"
"  Rows Removed by Filter: 9585"
"  Buffers: shared hit=360"
"Query Identifier: 5484391910498440363"
"Planning Time: 0.083 ms"
"Execution Time: 20.486 ms"
```
`"  Buffers: shared hit=360"` is what we are interested in.

### 3. Using [`pg_statio_all_tables`](https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STATIO-ALL-TABLES-VIEW)

This table has to be truncated before running a query and after running it changes in the table can be noted by querying it. Columns that are of interest to us form this table are `heap_blks_read` and `heap_blks_hit`

Query:
```sql
SELECT pg_stat_reset_single_table_counters('customer'::regclass);
select * from customer where c_acctbal > 6000;
select * from pg_statio_all_tables where relname = 'customer';
```
Output:
```
 relid | schemaname | relname  | heap_blks_read | heap_blks_hit | idx_blks_read | idx_blks_hit | toast_blks_read | toast_blks_hit | tidx_blks_read | tidx_blks_hit 
-------+------------+----------+----------------+---------------+---------------+--------------+-----------------+----------------+----------------+---------------
 24597 | public     | customer |              0 |           360 |               |              |                 |                |                |              
(1 row)

```



> What is still hard to figure out is how does one get the blocks that actually contain the data which is relevant to the query i. e. if I have a range set on account balance from 500 to 1000 in the `WHERE` clause of the query... blocks containing rows with data pertaining to account balance < 500 or > 1000 is of no interest to me and hence irrelavant... if these blocks are being read they would be count as bad/irrelevant block access...which is what we need to calculate. Will have to tinker around with the postgres source code to make this happen I think.
