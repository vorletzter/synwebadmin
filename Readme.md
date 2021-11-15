## SynWebAdmin
A Django based Frontend for Synapse Admin API Calls, *with the benefit of a **tenancy capability.***
Frontend Users can create Rooms and Accounts. Join their users to their rooms. The General Goal is to make the onboarding process easier by enabling you to pre-create and pre-join Rooms for your Users.

### Run with docker-compose

1) Modify the "setting_production.py" to fit your needs. At least you need to change ALLOWED_HOSTS and SECRET_KEY. A new Secret Key can be generated with
> python -c "import secrets; print(secrets.token_urlsafe())" 
3) Create the databse
> touch ./data/db.sqlite3)
4) Run the Server
> docker-compose up -d
5) Configure and inital Setup
> docker-compose run djangoapp python manage.py makemigrations
> 
> docker-compose run djangoapp python manage.py migrate
> 
> docker-compose run djangoapp python manage.py createsuperuser

### Run a local Development Server
0) Change into synadmin Directory
> cd synwebadmin

1) Create Python venv
> python3 -m venv ./venv

2) Activate
> source venv/bin/activate

3) Prepare
> pip install -r synadmin/requirements.txt
> 
> python synadmin/manage.py migrate
> 
> python synadmin/manage.py createsuperuser

4) Run
> python synadmin/manage.py runserver
