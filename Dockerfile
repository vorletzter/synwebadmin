FROM python:3

# set the default directory where CMD will execute
RUN mkdir -p /opt/services/djangoapp/
WORKDIR /opt/services/djangoapp/

COPY ./synadmin /opt/services/djangoapp/
# Overwrite settings.py with production settings

# Intall gunicorn and requirements
RUN pip install gunicorn --no-cache-dir
RUN pip install --no-cache-dir -r requirements.txt

COPY ./settings_production.py /opt/services/djangoapp/synadmin/settings.py

EXPOSE 8000

CMD ["gunicorn", "--bind", ":8000", "synadmin.wsgi:application", "--worker-tmp-dir", "/dev/shm"]

## ToDo: Cretae a "first run check" - run the commands below, if a certain directory does not exist....

## static files will be in /opt/services/djangoapp/static/ -> To use a volume see below
## media files will be in /opt/services/djangoapp/media/ -> To use a volume see below
## sqlight files will be in /opt/services/djangoapp/db.sqlite3 -> To use a volume see below

##
## Please run the following command after static or media files have changed!
## touch ./data/db.sqlit3
## docker-compose run djangoapp python manage.py collectstatic --no-input
##
## docker-compose run djangoapp python manage.py makemigrations
## docker-compose run djangoapp python manage.py migrate
## docker-compose run djangoapp python manage.py createsuperuser
