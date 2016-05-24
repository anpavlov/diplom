# coding=utf-8
import utils
from flask import request, Blueprint, render_template, redirect, url_for, make_response, abort
import settings

admin = Blueprint('admin', __name__)


@admin.route("/admin/upload", methods=['POST'])
def upload_module():
    archive = request.files['archive']
    if not archive:
        return "Не выбран ZIP архив"
    return utils.upload_module(archive)


@admin.route("/admin/approve", methods=['POST'])
def approve_module():
    try:
        module_id = request.form['module_id']
    except KeyError:
        return "no module id in form"
    return utils.approve_module(module_id)


@admin.route("/admin/enable", methods=['POST'])
def enable_module():
    try:
        module_id = request.form['module_id']
    except KeyError:
        return "no module id in form"
    return utils.switch_mod_able(module_id, True)


@admin.route("/admin/disable", methods=['POST'])
def disable_module():
    try:
        module_id = request.form['module_id']
    except KeyError:
        return "no module id in form"
    return utils.switch_mod_able(module_id, False)


@admin.route("/admin/delete", methods=['POST'])
def delete_module():
    try:
        module_id = request.form['module_id']
    except KeyError:
        return "no module id in form"
    return utils.delete_mod(module_id)


@admin.route("/admin/<module_name>/info")
def module_info(module_name):
    info = utils.get_module_info(module_name)
    if info is None:
        abort(404)
    return render_template("module_info.html", module=info)


@admin.route("/admin/<module_name>/contents")
def module_contents(module_name):
    sources = utils.get_module_contents(module_name)
    if sources is None:
        abort(404)
    return render_template("module_contents.html", **sources)


@admin.route("/admin/<module_name>/settings")
def module_settings(module_name):
    settings = utils.get_settings(module_name)
    if settings is None:
        abort(404)
    return render_template("module_settings.html", **settings)


@admin.route("/admin/<module_name>/settings/update", methods=['POST'])
def module_settings_update(module_name):
    settings = utils.get_settings(module_name)
    new_vals = []
    for setting in settings['settings']:
        try:
            val = request.form[setting['name']]
            if val != setting['value']:
                new_vals.append({
                    'name': setting['name'],
                    'value': val
                })
        except KeyError:
            pass
    if len(new_vals) != 0:
        return utils.set_settings(module_name, new_vals)
    return "ok"


@admin.route("/module/<module_name>")
def module_page(module_name):
    info = utils.get_module_info(module_name)
    if info is None:
        abort(404)
    return render_template("module_page.html", module=info)


@admin.route("/admin")
def admin_page():
    user_id = utils.get_logged_user_id(request)
    if user_id is None:
        return redirect('/login')
    modules_count, new_modules_count, all_modules = utils.get_all_modules()
    ctx = {'modules_count': modules_count, 'all_modules': all_modules, 'new_modules_count': new_modules_count}
    return render_template("modules.html", **ctx)


@admin.route("/login", methods=['GET', 'POST'])
def login():
    error = {'has_error': False}
    if request.method == 'GET':
        user_id = utils.get_logged_user_id(request)
        if user_id is not None:
            return redirect('/admin')
        return render_template("login.html", **error)
    elif request.method == 'POST':
        name = request.form['username']
        password = request.form['password']
        user_id = utils.try_login_admin(name, password)
        if user_id is None:
            error['has_error'] = True
            error['error_text'] = unicode("Неправильные логин и/или пароль",'utf-8')
            return render_template("login.html", **error)
        else:
            redirect_to_admin = redirect('/admin')
            response = make_response(redirect_to_admin)
            utils.set_new_session(user_id, response)
            return response


@admin.route("/logout")
def logout():
    redirect_to_login = redirect('/login')
    response = make_response(redirect_to_login)
    response.set_cookie(settings.SESSION_COOKIE_STRING, value="", expires=0)
    return response
