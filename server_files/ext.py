# coding=utf-8
from flaskext.mysql import MySQL
# from flask import request

mysql = MySQL()


def logged_as_admin(req, db):
    cookie = req.cookies.get('sid')
    if cookie == '':
        return None
    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM Session WHERE cookie = %s", (cookie,))
    row = cursor.fetchone()
    if row is None:
        return None
    else:
        return row[0]
