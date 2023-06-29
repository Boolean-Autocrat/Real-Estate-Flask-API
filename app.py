from flask import Flask, jsonify, request
import os
from dotenv import load_dotenv
import mysql.connector
from rets import Session
import math
from flask_cors import CORS
from functools import wraps

load_dotenv()


API_KEY = os.getenv("API_KEY")

connection = mysql.connector.connect(
    host=os.getenv("HOST"),
    database=os.getenv("DATABASE"),
    user=os.getenv("USER_NAME"),
    password=os.getenv("PASSWORD"),
    ssl_ca="cacert.pem",
)

cursor = connection.cursor()
app = Flask(__name__)
CORS(app)


def require_api_key(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        # Get the API key from the request headers or query parameters
        api_key = request.args.get("api_key")

        # Check if the API key is valid
        if api_key == API_KEY:  # Replace with your actual API key
            return func(*args, **kwargs)
        else:
            return jsonify({"error": "Invalid API key"}), 403  # Unauthorized

    return decorated_function


@app.route("/")
@require_api_key
def home():
    return "Hello World!"


@app.route("/switch-workload")
@require_api_key
def switch_workload():
    cursor.execute("SET workload='olap'")
    connection.commit()
    return "Workload switched successfully"


@app.route("/update-db")
@require_api_key
def update_db():
    rets_url = "http://rets.torontomls.net:6103/rets-treb3pv/server/login"
    username = "D23acs"
    password = "F$4w456"
    version = "RETS/1.5"
    rets_client = Session(rets_url, username, password, version)
    rets_client.login()
    resources = rets_client.get_class_metadata(resource="Property")
    residential = []
    condos = []
    commercial = []
    i = 1
    for class_ in resources:
        className = class_["ClassName"]
        filter_ = {}
        result = rets_client.search("Property", className, search_filter=filter_)
        if i == 1:
            residential.extend(result)
        elif i == 2:
            condos.extend(result)
        elif i == 3:
            commercial.extend(result)


@app.route("/listing/all", methods=["GET"])
@require_api_key
def residential_all():
    page = request.args.get("page", default=1, type=int)
    limit = request.args.get("limit", type=int)
    bedrooms = request.args.get("bedrooms")
    bathrooms = request.args.get("bathrooms")
    sale_lease = request.args.get("salelease")
    list_price = request.args.get("price")
    any_price = request.args.get("any_price")
    sqft = request.args.get("sqft")
    prop_type = request.args.get("prop_type")
    style = request.args.get("style")
    address_full = request.args.get("address_full")
    city = request.args.get("city")
    residence_type = request.args.get("residence_type")
    # Construct the SQL query with filters
    cursor.execute("SET workload='olap'")
    query = "SELECT Addr, Municipality, Ad_text, Zip, Sqft, Lp_dol, Br, Bath_tot, Extras, S_r, Ml_num FROM {0} WHERE 1=1".format(
        residence_type
    )
    params = []
    if address_full:
        query += (
            " AND (Addr LIKE %s OR "
            "Zip LIKE %s OR "
            "Municipality LIKE %s OR "
            "Ml_num LIKE %s)"
        )
        params.extend(["%{0}%".format(address_full)] * 4)
    if city:
        query += " AND Municipality = %s"
        params.append(city)
    if bedrooms:
        query += " AND Br >= %s"
        params.append(int(bedrooms))
    if bathrooms:
        query += " AND Bath_tot >= %s"
        params.append(int(bathrooms))
    if sale_lease:
        query += " AND S_r = %s"
        params.append(sale_lease)
    if list_price:
        query += " AND Lp_dol <= %s"
        params.append(float(list_price))
    if any_price:
        query += " AND Lp_dol >= %s"
        params.append(float(any_price))
    if sqft:
        query += " AND Sqft <= %s"
        params.append(sqft)
    if prop_type:
        query += " AND Type_own1_out = %s"
        params.append(prop_type)
    if style:
        query += " AND Style = %s"
        params.append(style)
    if limit:
        offset = (page - 1) * limit  # Calculate the offset based on the page number
        query += " LIMIT %s OFFSET %s"  # Add LIMIT and OFFSET clauses to the query
        params.extend([limit, offset])
    cursor.execute(query, params)
    result = cursor.fetchall()

    obj = []
    for data in result:
        obj_app = {
            "address": data[0],
            "area": data[1],
            "about": data[2],
            "postal_code": data[3],
            "sqft": data[4],
            "price": "{:.2f}".format(float(data[5])),
            "bedrooms": data[6],
            "bathrooms": data[7],
            "extras": data[8],
            "sale/lease": data[9],
            "mls_number": data[10],
            "slug": data[0].replace(" ", "-").lower()
            + "-"
            + data[1].replace(" ", "-").lower()
            + "-"
            + data[10].replace(" ", "-")
            if data[0] and data[1]
            else data[10],
            "address_full": data[0]
            + ", "
            + data[1]
            + " "
            + ("".join(data[3].split(" ")) if data[3] and len(data[3]) > 2 else data[3])
            if data[0] and data[1] and data[3]
            else "",
        }
        obj.append(obj_app)
    response = jsonify(obj)
    return response


@app.route("/listing_count", methods=["GET"])
@require_api_key
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
    city = request.args.get("city")
    residence_type = request.args.get("residence_type")
    cursor.execute("SET workload='olap'")
    count_query = "SELECT COUNT(*) FROM {0} WHERE 1=1".format(residence_type)
    params = []
    if address_full:
        count_query += (
            " AND (Addr LIKE %s OR "
            "Zip LIKE %s OR "
            "Municipality LIKE %s OR "
            "Ml_num LIKE %s)"
        )
        params.extend(["%{0}%".format(address_full)] * 4)
    if city:
        count_query += " AND Municipality = %s"
        params.append(city)
    if bedrooms:
        count_query += " AND Br >= %s"
        params.append(int(bedrooms))
    if bathrooms:
        count_query += " AND Bath_tot >= %s"
        params.append(int(bathrooms))
    if sale_lease:
        count_query += " AND S_r = %s"
        params.append(sale_lease)
    if list_price:
        count_query += " AND Lp_dol <= %s"
        params.append(float(list_price))
    if any_price:
        count_query += " AND Lp_dol >= %s"
        params.append(float(any_price))
    if sqft:
        count_query += " AND Sqft <= %s"
        params.append(sqft)
    if prop_type:
        count_query += " AND Type_own1_out = %s"
        params.append(prop_type)
    if style:
        count_query += " AND Style = %s"
        params.append(style)
    if limit:
        count_query += f" LIMIT {limit}"

    cursor.execute(count_query, params)
    total_results = cursor.fetchone()[0]
    total_pages = math.ceil(total_results / limit)

    response = jsonify({"total_results": total_results, "total_pages": total_pages})
    return response


@app.route("/autocomplete/address_full", methods=["GET"])
@require_api_key
def autocomplete_address():
    query = request.args.get("query")
    params = []
    params.extend(["%{0}%".format(query)] * 4)
    sql_query = (
        "SELECT Addr, Zip, Municipality FROM residential WHERE "
        "Addr LIKE %s OR "
        "Zip LIKE %s OR "
        "Municipality LIKE %s OR "
        "Ml_num LIKE %s"
        "LIMIT 10"
    )
    cursor.execute("SET workload='olap'")
    cursor.execute(sql_query, params)
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
    return response


@app.route("/listing/distinct", methods=["GET"])
@require_api_key
def residential_distinct():
    obj = [[], [], []]
    cursor.execute("SET workload='olap'")
    residence_type = request.args.get("residence_type")
    query = "SELECT DISTINCT Type_own1_out, Style FROM {0};".format(residence_type)
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
    return response


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
