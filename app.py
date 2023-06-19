from flask import Flask, jsonify, request
import os
from dotenv import load_dotenv
from mysql.connector import Error
import mysql.connector
from rets import Session
import requests
import math

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
    page = request.args.get("page", default=1, type=int)
    limit = request.args.get("limit", default=10, type=int)
    bedrooms = request.args.get("bedrooms")
    bathrooms = request.args.get("bathrooms")
    sale_lease = request.args.get("salelease")
    list_price = request.args.get("price")
    any_price = request.args.get("any_price")
    sqft = request.args.get("sqft")
    prop_type = request.args.get("prop_type")
    style = request.args.get("style")
    address_full = request.args.get("address_full")
    residence_type = request.args.get("residence_type")
    # Construct the SQL query with filters
    query = f"SELECT * FROM {residence_type} WHERE 1=1"
    if address_full:
        query += (
            f" AND Address LIKE '%{address_full}%' OR "
            f"Postal_Code LIKE '%{address_full}%' OR "
            f"Area LIKE '%{address_full}%' OR "
            f"MLS LIKE '%{address_full}%'"
        )
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
    if limit:
        offset = (page - 1) * limit  # Calculate the offset based on the page number
        query += f" LIMIT {limit} OFFSET {offset}"  # Add LIMIT and OFFSET clauses to the query

    cursor.execute(query)
    result = cursor.fetchall()

    obj = []
    for data in result:
        obj_app = {
            "address": data[4],
            "area": data[10],
            "about": data[108],
            "postal_code": data[99],
            "sqft": data[8],
            "price": "{:.2f}".format(float(data[70])),
            "bedrooms": data[17],
            "bathrooms": data[225],
            "image": data[258],
            "extras": data[35],
            "sale/lease": data[189],
            "mls_number": data[78],
            "slug": data[4].replace(" ", "-").lower()
            + "-"
            + data[10].replace(" ", "-").lower()
            + "-"
            + data[99].replace(" ", "-"),
            "address_full": data[4]
            + ", "
            + data[10]
            + " "
            + ("".join(data[99].split(" ")) if len(data[99]) > 2 else data[99]),
        }
        obj.append(obj_app)
    response = jsonify(obj)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@app.route("/residential_count", methods=["GET"])
def residential_count():
    limit = request.args.get("limit", default=10, type=int)
    bedrooms = request.args.get("bedrooms")
    bathrooms = request.args.get("bathrooms")
    sale_lease = request.args.get("salelease")
    list_price = request.args.get("price")
    any_price = request.args.get("any_price")
    sqft = request.args.get("sqft")
    prop_type = request.args.get("prop_type")
    style = request.args.get("style")
    address_full = request.args.get("address_full")
    residence_type = request.args.get("residence_type")
    count_query = f"SELECT COUNT(*) FROM {residence_type} WHERE 1=1"
    if address_full:
        count_query += (
            f" AND Address LIKE '%{address_full}%' OR "
            f"Postal_Code LIKE '%{address_full}%' OR "
            f"Area LIKE '%{address_full}%' OR "
            f"MLS LIKE '%{address_full}%'"
        )
    if bedrooms:
        count_query += f" AND Bedrooms >= '{bedrooms}'"
    if bathrooms:
        count_query += f" AND Washrooms >= '{bathrooms}'"
    if sale_lease:
        count_query += f" AND SaleLease = '{sale_lease}'"
    if list_price:
        count_query += f" AND List_Price <= '{list_price}'"
    if any_price:
        count_query += f" AND List_Price >= '{any_price}'"
    if sqft:
        count_query += f" AND Approx_Square_Footage <= '{sqft}'"
    if prop_type:
        count_query += f" AND Type2 = '{prop_type}'"
    if style:
        count_query += f" AND Style = '{style}'"
    if limit:
        count_query += f" LIMIT {limit}"

    cursor.execute(count_query)
    total_results = cursor.fetchone()[0]
    total_pages = math.ceil(total_results / limit)

    response = jsonify({"total_results": total_results, "total_pages": total_pages})
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@app.route("/autocomplete/address_full", methods=["GET"])
def autocomplete_address():
    query = request.args.get("query")

    sql_query = (
        f"SELECT Address, Postal_Code, Area FROM residential WHERE "
        f"Address LIKE '%{query}%' OR "
        f"Postal_Code LIKE '%{query}%' OR "
        f"Area LIKE '%{query}%' OR "
        f"MLS LIKE '%{query}%'"
        f"LIMIT 10"
    )
    cursor.execute(sql_query)
    result = cursor.fetchall()

    addresses = [
        (
            data[0]
            + ", "
            + ("".join(data[1].split(" ")) if len(data[1]) > 1 else data[1])
            + " "
            + data[2]
        )
        for data in result
    ]

    response = jsonify(addresses)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@app.route("/residential/distinct", methods=["GET"])
def residential_distinct():
    obj = [[], [], []]
    query = "SELECT DISTINCT Area, Type2, Style FROM residential;"
    cursor.execute(query)
    result = cursor.fetchall()
    for data in result:
        if data[0] is None:
            pass
        else:
            obj[0].append(data[0])
        if data[1] is None:
            pass
        else:
            obj[1].append(data[1])
        if data[2] is None:
            pass
        else:
            obj[2].append(data[2])
    for i in range(len(obj)):
        obj[i] = sorted(list(set(obj[i])))
    response = jsonify(obj)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@app.route("/residential/images", methods=["GET"])
def residential_images():
    mls_number = request.args.get("mls")
    query = f"SELECT img_list FROM residential WHERE MLS='{mls_number}';"
    cursor.execute(query)
    result = cursor.fetchall()
    images = result[0][0].replace("[", "").replace("]", "").replace("'", "").split(",")
    images = [image.strip() for image in images]
    response = jsonify(images)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


app.run(host="localhost", port=5000, debug=True)
