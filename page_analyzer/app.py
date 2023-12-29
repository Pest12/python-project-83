import psycopg2
import validators
import os
import requests
from flask import Flask, render_template, request, flash, redirect, url_for, get_flashed_messages
from dotenv import load_dotenv
from urllib.parse import urlparse
from datetime import date
from psycopg2.extras import NamedTupleCursor
from contextlib import contextmanager
from bs4 import BeautifulSoup


load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')
app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


@contextmanager
def connect_database(url):
    try:
        connection = psycopg2.connect(url)
        yield connection
    except Exception:
        if connection:
            connection.rollback()
        raise
    else:
        if connection:
            connection.commit()
    finally:
        if connection:
            connection.close()


def create_url(connection, name):
    current_date = date.today()
    with connection.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
           """INSERT INTO urls (name, created_at)
              VALUES (%s, %s) RETURNING id;
              """, (name, current_date)
        )
        return cursor.fetchone()[0]


def get_all_urls(connection):
    with connection.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            """SELECT id, name, created_at
               FROM urls
               ORDER BY id DESC;"""
        )
        return cursor.fetchall()


def get_url_by_name(connection, name):
    with connection.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            """SELECT * FROM urls
               WHERE name = %s;
               """, (name,))
        return cursor.fetchone()


def get_url_by_id(connection, id):
    with connection.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            """SELECT * FROM urls
               WHERE id = %s;
               """, (id,))
        return cursor.fetchone()


def create_check(connection, id, status_code, h1, title, description):
    current_date = date.today()
    with connection.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            """INSERT INTO url_checks (
            url_id, status_code, h1, title, description, created_at)
            VALUES (%s, %s, %s, %s, %s, %s);
            """, (id, status_code, h1, title, description, current_date,))


def get_last_check(connection):
    with connection.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            """SELECT DISTINCT ON (url_id)
            id, url_id, status_code, h1, title, description, created_at
            FROM url_checks
            ORDER BY url_id, created_at DESC;
            """)
        return cursor.fetchall()


def get_all_checks(connection, id):
    with connection.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            """SELECT * FROM url_checks
            WHERE url_id = %s
            ORDER BY id DESC;
            """, (id,))
        return cursor.fetchall()

def get_seo(html):
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.string
    if soup.h1:
        h1 = soup.h1.string
    else:
        h1 = ''
    description_content = soup.find('meta', attrs={'name': 'description'})
    if description_content:
        description = description_content.get('content')
    else:
        description = ''
    return title, h1, description

@app.errorhandler(404)
def not_found(error):
    return 'Oops!', 404


@app.route("/")
def index():
    return render_template('index.html')


def validate(url):
    errors = []
    if not url:
        errors.append("URL обязателен")
    elif not validators.url(url):
        errors.append("Некорректный URL")
    elif len(url) > 255:
        errors.append("URL превышает 255 символов")
    return errors


@app.route("/urls")
def urls():
    with connect_database(DATABASE_URL) as conn:
        urls = get_all_urls(conn)
        url_checks = {
            item.url_id: item for item in get_last_check(conn)
        }
    return render_template(
        '/urls.html',
        urls=urls,
        url_checks=url_checks
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
    parsed_url = urlparse(url_name)
    normalized_url = f'{parsed_url.scheme}://{parsed_url.netloc}'
    with connect_database(DATABASE_URL) as conn:
        check_url = get_url_by_name(conn, normalized_url)
        if check_url:
            flash('Страница уже существует', 'info')
            return redirect(url_for('url_info', id=check_url[0]))
        url_id = create_url(conn, normalized_url)
    flash('Страница успешно добавлена', 'success')
    return redirect(url_for('url_info', id=url_id))


@app.route("/urls/<int:id>")
def url_info(id):
    with connect_database(DATABASE_URL) as conn:
        url = get_url_by_id(conn, id)
        url_checks = get_all_checks(conn, id)
    return render_template(
        'url_id.html',
        url=url,
        checks=url_checks,
    )


@app.post("/urls/<int:id>/checks")
def url_check(id):
    with connect_database(DATABASE_URL) as conn:
        url = get_url_by_id(conn, id)
        try:
            request = requests.get(url.name)
            request.raise_for_status()
        except requests.ConnectionError:
            flash('Произошла ошибка при проверке', 'error')
            return redirect(url_for('url_info', id=id))
        status_code = request.status_code
        title, h1, description = get_seo(request.text)
        create_check(conn, id, status_code, h1, title, description)
    flash('Страница успешно проверена', 'success')
    return redirect(url_for('url_info', id=id))
