"Backend"/API for [Steam PageRank](https://www.steampagerank.com). An example of this project can be found [HERE](https://api.steampagerank.com).Code for the FrontEnd can be found [HERE](https://github.com/TwelfthGhast/SteamPR-Frontend).

## Editing your config ##

Please include your own PostgreSQL details in config.py. If you do not have a database installed yet, follow the instructions in the next section.

## Running the code ##

You are required to have PostgreSQL installed on your computer. A tutorial for Ubuntu 18.04 can be found on [DigitalOcean](https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-on-ubuntu-18-04).

Once you have installed PostgreSQL, create a database. Then extract the files from databases.tar.gz and import them into your database.

```psql -h hostname -d databasename -U username -f file.sql```

It is advised to install dependencies in a virtual environment to sandbox this code.
```
$ sudo apt update
$ sudo apt install python3-pip python3-dev build-essential libssl-dev libffi-dev python3-setuptools
$ sudo apt install python3-venv
$ sudo apt install libpq-dev
```
Then navigate to the project directory.
```
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install wheel
```

You will then need to install the following python modules:
- Flask ```pip install Flask```
- Flask-Caching ```pip install Flask-Caching```
- Psycopg2 ```pip install psycopg2```

You can then run the code
```
$ python3 app.py
```
