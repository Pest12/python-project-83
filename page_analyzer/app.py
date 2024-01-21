import psycopg2
import os
import requests
from flask import Flask, render_template, request, flash, redirect, url_for
from dotenv import load_dotenv
from contextlib import contextmanager
from page_analyzer.html import get_seo_content
from page_analyzer import database
from page_analyzer.urls import validate, get_normalized_url


load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')
app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


@contextmanager
def connect_database(url):
    try:
        connection = psycopg2.connect(url)
        yield connection
    except Exception as _ex:
        print("[INFO] Error while working with PostgreSQL", _ex)
    else:
        if connection:
            connection.commit()
    finally:
        if connection:
            connection.close()


@app.errorhandler(404)
def not_found(error):
    return 'Oops!', 404


@app.route("/")
def index():
    return render_template('index.html')


@app.route("/urls")
def urls():
    with connect_database(DATABASE_URL) as conn:
        data = database.get_all_urls_and_last_check(conn)
        return render_template(
            '/urls.html',
            data=data,
        )


@app.post("/urls")
def add_url():
    url_name = request.form.get('url')
    errors = validate(url_name)
    if errors:
        for error in errors:
            flash(error, 'error')
        return render_template(
            'index.html',
        ), 422
    normalized_url = get_normalized_url(url_name)
    with connect_database(DATABASE_URL) as conn:
        check_url = database.get_url_by_name(conn, normalized_url)
        if check_url:
            flash('Страница уже существует', 'info')
            return redirect(url_for('url_info', id=check_url[0]))
        url_id = database.create_url(conn, normalized_url)
        flash('Страница успешно добавлена', 'success')
        return redirect(url_for('url_info', id=url_id))


@app.route("/urls/<int:id>")
def url_info(id):
    with connect_database(DATABASE_URL) as conn:
        url = database.get_url_by_id(conn, id)
        url_checks = database.get_all_checks(conn, id)
        return render_template(
            'url_id.html',
            url=url,
            checks=url_checks,
        )


@app.post("/urls/<int:id>/checks")
def url_check(id):
    with connect_database(DATABASE_URL) as conn:
        url = database.get_url_by_id(conn, id)
        try:
            request = requests.get(url.name)
            request.raise_for_status()
            status_code = request.status_code
            title, header_title, description = get_seo_content(request.text)
            database.create_check(conn, id, status_code,
                                  header_title, title, description)
            flash('Страница успешно проверена', 'success')
            return redirect(url_for('url_info', id=id))
        except requests.RequestException:
            flash('Произошла ошибка при проверке', 'error')
            return redirect(url_for('url_info', id=id))
