from flask import Flask, jsonify, request
import os
from dotenv import load_dotenv
from mysql.connector import Error
import mysql.connector
from rets import Session
import requests

load_dotenv()

connection = mysql.connector.connect(
    host=os.getenv("HOST"),
    database=os.getenv("DATABASE"),
    user=os.getenv("USER_NAME"),
    password=os.getenv("PASSWORD"),
    ssl_ca="cacert.pem",
)

cursor = connection.cursor()
app = Flask(__name__)


@app.route("/update-db")
def update_db():
    login_url = "http://rets.com/login"
    username = "username"
    password = "password"
    rets_client = Session(login_url, username, password)
    rets_client.login()
    system_data = rets_client.get_system_metadata()


@app.route("/residential/all", methods=["GET"])
def residential_all():
    area = request.args.get("area")
    address = request.args.get("address")
    bedrooms = request.args.get("bedrooms")
    bathrooms = request.args.get("bathrooms")
    sale_lease = request.args.get("salelease")
    list_price = request.args.get("price")
    any_price = request.args.get("any_price")
    sqft = request.args.get("sqft")
    prop_type = request.args.get("prop_type")
    style = request.args.get("style")

    # Construct the SQL query with filters
    query = "SELECT * FROM residential WHERE 1=1"
    if address:
        query += f" AND Address LIKE '%{address}%'"
    if area:
        query += f" AND Area = '{area}'"
    if bedrooms:
        query += f" AND Bedrooms >= '{bedrooms}'"
    if bathrooms:
        query += f" AND Washrooms >= '{bathrooms}'"
    if sale_lease:
        query += f" AND SaleLease = '{sale_lease}'"
    if list_price:
        query += f" AND List_Price <= '{list_price}'"
    if any_price:
        query += f" AND List_Price >= '{any_price}'"
    if sqft:
        query += f" AND Approx_Square_Footage <= '{sqft}'"
    if prop_type:
        query += f" AND Type2 = '{prop_type}'"
    if style:
        query += f" AND Style = '{style}'"
    cursor.execute(query)
    result = cursor.fetchall()

    obj = []
    for data in result:
        obj_app = {
            "id": data[0],
            "address": data[4],
            "area": data[10],
            "price": data[70],
            "bedrooms": data[17],
            "bathrooms": data[225],
            "image": data[258],
            "sale/lease": data[189],
        }
        obj.append(obj_app)
    response = jsonify(obj)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@app.route("/autocomplete/address", methods=["GET"])
def autocomplete_address():
    query = request.args.get("query")

    # Construct the SQL query to fetch autocomplete suggestions
    sql_query = f"SELECT Address FROM residential WHERE Address LIKE '%{query}%'"
    cursor.execute(sql_query)
    result = cursor.fetchall()

    # Extract addresses from the result
    addresses = [data[0] for data in result]

    response = jsonify(addresses)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@app.route("/residential/<int:id>")
def residential(id):
    cursor.execute(
        "SELECT * FROM residential ORDER BY Access_To_Property1 DESC LIMIT %s;", (id,)
    )
    result = cursor.fetchall()
    obj = []
    for data in result:
        obj_app = {
            "id": data[0],
            "address": data[4],
            "area": data[10],
            "price": data[70],
            "bedrooms": data[17],
            "bathrooms": data[225],
            "image": data[258],
            "sale/lease": data[189],
        }
        obj.append(obj_app)
    return jsonify(obj)


app.run(host="localhost", port=5000, debug=True)
