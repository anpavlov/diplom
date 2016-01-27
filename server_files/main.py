# coding=utf-8
import os
import ConfigParser

# from werkzeug.utils import secure_filename

from ext import mysql

from flask import Flask
# from flask import render_template
# from flask import request
from pages.admin import admin
from pages.api import api

app = Flask(__name__)

config = ConfigParser.ConfigParser()
config.read('../conf/server.ini')
database_config_section = 'database'

app.config['DEBUG'] = True
app.config['MYSQL_DATABASE_USER'] = config.get(database_config_section, 'user')
app.config['MYSQL_DATABASE_PASSWORD'] = config.get(database_config_section, 'password')
app.config['MYSQL_DATABASE_DB'] = config.get(database_config_section, 'db')
app.config['MYSQL_DATABASE_HOST'] = config.get(database_config_section, 'host')

mysql.init_app(app)

# открывает файлы в diplom ((?)где запускают uwsgi)
app.register_blueprint(admin)
app.register_blueprint(api, url_prefix='/api')


@app.route("/")
def hello():
    return "Hello World!"


@app.route("/create_test")
def create_test():
    os.makedirs('lua/modules/test/')
    with open('lua/modules/test/sample.lua', 'w') as f:
        f.write('ngx.say("hi from test")')
    return "from create!"

if __name__ == "__main__":
    app.run()
