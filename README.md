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
```sh

```

