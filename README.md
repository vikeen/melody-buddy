# Band Maker

### Depencies

* [Python](http://install.python-guide.org)
* [Postgres](https://devcenter.heroku.com/articles/heroku-postgresql#local-setup)
* Node

```sh
$ npm install
$ npm install -g gulp
$ sudo apt install python3-pip
$ python3.5 -m venv venv
$ source ./venv/bin/activate
$ sudo apt-get install libpq-dev
$ pip3 install -r requirements.txt
```

### Database

```sql
CREATE DATABASE band_maker;
CREATE ROLE band_maker_user with PASSWORD 'password';
ALTER ROLE band_maker_user with LOGIN;
ALTER ROLE band_maker_user WITH CREATEDB;
ALTER DATABASE band_maker OWNER TO band_maker_user;
```

```sh
$ python3 manage.py migrate
$ python3 manage.py collectstatic
```

### Development

* `python3 manage.py runserver` - Server
* `gulp` - Frontend Assets

Your app should now be running on [localhost:8000](http://localhost:8000/).

## Deploying to Heroku

```sh
$ gulp build
$ git push heroku master
$ heroku run python manage.py migrate
$ heroku open
```
or

## Documentation

For more information about using Python on Heroku, see these Dev Center articles:

- [Python on Heroku](https://devcenter.heroku.com/categories/python)
