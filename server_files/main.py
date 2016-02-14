# coding=utf-8
import os
import ConfigParser
import settings

# from werkzeug.utils import secure_filename

from utils import mysql

from flask import Flask
# from flask import render_template
# from flask import request
from pages.admin import admin
from pages.api import api

app = Flask(__name__)

app.config['DEBUG'] = True
app.config.from_object(settings)

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
