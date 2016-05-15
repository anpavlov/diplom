# coding=utf-8
from utils import mysql, get_logged_user_id, try_login_admin, set_new_session, get_all_modules
from utils import approve_module as util_approve_module, upload_module as util_upload, switch_mod_able
from flask import request, Blueprint, render_template, redirect, url_for, make_response
from zipfile import ZipFile
import json

admin = Blueprint('admin', __name__)


@admin.route("/admin")
def admin_page():
    return modules()


@admin.route("/admin/approve", methods=['POST'])
def approve_module():
    try:
        module_id = request.form['module_id']
    except KeyError:
        return "no module id in form"
    util_approve_module(module_id)
    return "ok"


@admin.route("/admin/enable", methods=['POST'])
def enable_module():
    try:
        module_id = request.form['module_id']
    except KeyError:
        return "no module id in form"
    return switch_mod_able(module_id, True)


@admin.route("/admin/disable", methods=['POST'])
def disable_module():
    try:
        module_id = request.form['module_id']
    except KeyError:
        return "no module id in form"
    return switch_mod_able(module_id, False)


@admin.route("/admin/upload", methods=['POST'])
def upload_module():
    archive = request.files['archive']
    if not archive:
        return "no zip archive"
    return util_upload(archive)


@admin.route("/modules", methods=['GET', 'POST'])
def modules():
    user_id = get_logged_user_id(request)
    if user_id is None:
        return redirect('/login')
    if request.method == 'POST':
        pass
    modules_count, new_modules_count, all_modules = get_all_modules()
    ctx = {'modules_count': modules_count, 'all_modules': all_modules, 'new_modules_count': new_modules_count}
    return render_template("modules.html", **ctx)


@admin.route("/users")
def users():
    return render_template("admin.html")


@admin.route("/login", methods=['GET', 'POST'])
def login():
    error = {'has_error': False}
    if request.method == 'GET':
        user_id = get_logged_user_id(request)
        if user_id is not None:
            return redirect('/admin')
        return render_template("login.html", **error)
    elif request.method == 'POST':
        name = request.form['username']
        password = request.form['password']
        user_id = try_login_admin(name, password)
        if user_id is None:
            error['has_error'] = True
            error['error_text'] = "Wrong username or password"
            return render_template("login.html", **error)
        else:
            redirect_to_admin = redirect('/admin')
            response = make_response(redirect_to_admin)
            set_new_session(user_id, response)
            return response
