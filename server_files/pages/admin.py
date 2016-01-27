# coding=utf-8
from ext import mysql
from flask import request, Blueprint, render_template, redirect, url_for
from zipfile import ZipFile
import json

admin = Blueprint('admin', __name__)


@admin.route("/admin")
def admin_page():
    return modules()
    # return "asdasd"
    # return redirect(url_for('.modules'))


@admin.route("/modules")
def modules():
    # context = {'new_modules': []}
    #
    # connection = mysql.connect()
    # cursor = connection.cursor()
    #
    # cursor.execute("SELECT * FROM Module WHERE approved = 0")
    # for module_id, name, version, approved in cursor.fetchall():
    #     context['new_modules'].append({'id': module_id, 'name': name, 'version': version})
    return render_template("modules.html")


@admin.route("/users")
def users():
    return render_template("admin.html")