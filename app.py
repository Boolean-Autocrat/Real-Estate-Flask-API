from flask import Flask, jsonify, request
import os
from dotenv import load_dotenv
import mysql.connector
import math
from flask_cors import CORS
from functools import wraps
import logging
import re

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

gunicorn_error_logger = logging.getLogger("gunicorn.error")
app.logger.handlers.extend(gunicorn_error_logger.handlers)
app.logger.setLevel(logging.ERROR)


def slugify_char(input_string):
    pattern = r"[^\w-]"
    cleaned_string = re.sub(pattern, "", input_string)
    return cleaned_string


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


@app.route("/listing/all", methods=["GET"])
@require_api_key
def listing_all():
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
    mls_number = request.args.get("mls_number")
    # Construct the SQL query with filters
    cursor.execute("SET workload='olap'")
    if residence_type == "residential" or residence_type == "condo":
        query = "SELECT Addr, Municipality, Ad_text, Zip, Sqft, Lp_dol, Br, Bath_tot, Extras, S_r, Ml_num, Timestamp_sql, Rltr, Latitude, Longitude FROM {0} WHERE Status='A'".format(
            residence_type
        )
    elif residence_type == "commercial":
        query = "SELECT Addr, Municipality, Ad_text, Zip, Tot_area, Lp_dol, Extras, S_r, Ml_num, Timestamp_sql, Rltr, Latitude, Longitude FROM {0} WHERE Status='A'".format(
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
    if sqft and (residence_type == "residential" or residence_type == "condo"):
        query += " AND Sqft >= %s"
        params.append(sqft)
    if sqft and residence_type == "commercial":
        query += " AND Tot_area >= %s"
        params.append(sqft)
    if prop_type:
        query += " AND Type_own1_out = %s"
        params.append(prop_type)
    if style:
        query += " AND Style = %s"
        params.append(style)
    if mls_number:
        if mls_number[-1] != ",":
            mls_number += ","
        query += f" AND Ml_num IN {tuple(mls_number.split(','))}"
    if limit:
        offset = (page - 1) * limit  # Calculate the offset based on the page number
        query += " ORDER BY Timestamp_sql DESC LIMIT %s OFFSET %s"  # Add LIMIT and OFFSET clauses to the query
        params.extend([limit, offset])
    cursor.execute(query, params)
    result = cursor.fetchall()

    obj = []
    if residence_type == "residential" or residence_type == "condo":
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
                "slug": slugify_char(data[0].replace(" ", "-").lower())
                + "-"
                + slugify_char(data[1].replace(" ", "-").lower())
                + "-"
                + data[10].replace(" ", "-")
                if data[0] and data[1]
                else data[10],
                "address_full": data[0]
                + ", "
                + data[1]
                + " "
                + (
                    "".join(data[3].split(" "))
                    if data[3] and len(data[3]) > 2
                    else data[3]
                )
                if data[0] and data[1] and data[3]
                else "",
                "timestamp": data[11],
                "realtor": data[12],
                "latitude": data[13],
                "longitude": data[14],
            }
            obj.append(obj_app)
    elif residence_type == "commercial":
        for data in result:
            obj_app = {
                "address": data[0],
                "area": data[1],
                "about": data[2],
                "postal_code": data[3],
                "sqft": data[4],
                "price": "{:.2f}".format(float(data[5])),
                "extras": data[6],
                "sale/lease": data[7],
                "mls_number": data[8],
                "slug": slugify_char(data[0].replace(" ", "-").lower())
                + "-"
                + slugify_char(data[1].replace(" ", "-").lower())
                + "-"
                + data[8].replace(" ", "-")
                if data[0] and data[1]
                else data[8],
                "address_full": data[0]
                + ", "
                + data[1]
                + " "
                + (
                    "".join(data[3].split(" "))
                    if data[3] and len(data[3]) > 2
                    else data[3]
                )
                if data[0] and data[1] and data[3]
                else "",
                "timestamp": data[9],
                "realtor": data[10],
                "latitude": data[11],
                "longitude": data[12],
            }
            obj.append(obj_app)
    response = jsonify(obj)
    return response


@app.route("/listing/similar", methods=["GET"])
def listing_similar():
    limit = request.args.get("limit", type=int)
    postal_code = request.args.get("postal")
    city = request.args.get("city")
    residence_type = request.args.get("residence_type")
    mls_number = request.args.get("mls")
    # Construct the SQL query with filters
    cursor.execute("SET workload='olap'")
    if residence_type == "residential" or residence_type == "condo":
        query = "SELECT Addr, Municipality, Ad_text, Zip, Sqft, Lp_dol, Br, Bath_tot, Extras, S_r, Ml_num, Timestamp_sql, Rltr FROM {0} WHERE Status='A'".format(
            residence_type
        )
    elif residence_type == "commercial":
        query = "SELECT Addr, Municipality, Ad_text, Zip, Tot_area, Lp_dol, Extras, S_r, Ml_num, Timestamp_sql, Rltr FROM {0} WHERE Status='A'".format(
            residence_type
        )
    conditions = []
    params = []
    if mls_number:
        params.append(mls_number)

    if postal_code:
        conditions.append("Zip = %s")
        params.append(postal_code)

    if city:
        conditions.append("Municipality = %s")
        params.append(city)

    query += (
        " AND Ml_num!=%s AND ("
        + " OR ".join(conditions)
        + ") ORDER BY CASE WHEN Zip = %s THEN 1 ELSE 2 END LIMIT %s"
    )
    params.extend([postal_code, limit])
    cursor.execute(query, params)
    result = cursor.fetchall()
    if result is None:
        return jsonify([])

    obj = []
    if residence_type == "residential" or residence_type == "condo":
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
                "slug": slugify_char(data[0].replace(" ", "-").lower())
                + "-"
                + slugify_char(data[1].replace(" ", "-").lower())
                + "-"
                + data[10].replace(" ", "-")
                if data[0] and data[1]
                else data[10],
                "address_full": data[0]
                + ", "
                + data[1]
                + " "
                + (
                    "".join(data[3].split(" "))
                    if data[3] and len(data[3]) > 2
                    else data[3]
                )
                if data[0] and data[1] and data[3]
                else "",
                "timestamp": data[11],
                "realtor": data[12],
            }
            obj.append(obj_app)
    elif residence_type == "commercial":
        for data in result:
            obj_app = {
                "address": data[0],
                "area": data[1],
                "about": data[2],
                "postal_code": data[3],
                "sqft": data[4],
                "price": "{:.2f}".format(float(data[5])),
                "extras": data[6],
                "sale/lease": data[7],
                "mls_number": data[8],
                "slug": slugify_char(data[0].replace(" ", "-").lower())
                + "-"
                + slugify_char(data[1].replace(" ", "-").lower())
                + "-"
                + data[8].replace(" ", "-")
                if data[0] and data[1]
                else data[8],
                "address_full": data[0]
                + ", "
                + data[1]
                + " "
                + (
                    "".join(data[3].split(" "))
                    if data[3] and len(data[3]) > 2
                    else data[3]
                )
                if data[0] and data[1] and data[3]
                else "",
                "timestamp": data[9],
                "realtor": data[10],
            }
            obj.append(obj_app)
    response = jsonify(obj)
    return response


@app.route("/listing_count", methods=["GET"])
@require_api_key
def listing_count():
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
    count_query = "SELECT COUNT(*) FROM {0} WHERE Status='A'".format(residence_type)
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
    residence_type = request.args.get("residence_type")
    sql_query = "SELECT Addr, Zip, Municipality FROM {} WHERE MATCH(Addr, Zip, Municipality, Ml_num) AGAINST(%s) AND Status = 'A' LIMIT 10;".format(
        residence_type
    )
    cursor.execute("SET workload='olap'")
    cursor.execute(sql_query, (query,))
    result = cursor.fetchall()
    if len(result) == 0:
        return jsonify([])

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
def listing_distinct():
    obj = [[], [], []]
    cursor.execute("SET workload='olap'")
    residence_type = request.args.get("residence_type")
    query = "SELECT DISTINCT Type_own1_out FROM {0} WHERE Status='A';".format(
        residence_type
    )
    cursor.execute(query)
    result = cursor.fetchall()
    for data in result:
        if data[0] is None:
            pass
        else:
            obj[0].append(data[0])
    for i in range(len(obj)):
        obj[i] = sorted(list(set(obj[i])))
    response = jsonify(obj)
    return response


@app.route("/listing/details", methods=["GET"])
@require_api_key
def listing_details():
    mls_num = request.args.get("mls")
    residence_type = request.args.get("residence_type")
    cursor.execute("SET workload='olap'")
    if residence_type == "residential":
        query = "SELECT Type_own1_out, Style, Bath_tot, Front_ft, Depth, Water, Park_spcs, Fpl_num, Fuel, Cross_st, Bsmt1_out, Occ, Taxes, S_r, Br, Br_plus, Tot_park_spcs, A_c, gar_spaces, Drive, Heating, Pool, Constr1_out, Comp_pts, Front_ft, Level1, Level2, Level3, Level4, Level5, Level6, Level7, Level8, Level9, Level10, Level11, Level12, Rm1_out, Rm1_len, Rm1_wth, Rm1_dc1_out, Rm1_dc2_out, Rm1_dc3_out, Rm2_out, Rm2_len, Rm2_wth, Rm2_dc1_out, Rm2_dc2_out, Rm2_dc3_out, Rm3_out, Rm3_len, Rm3_wth, Rm3_dc1_out, Rm3_dc2_out, Rm3_dc3_out, Rm4_out, Rm4_len, Rm4_wth, Rm4_dc1_out, Rm4_dc2_out, Rm4_dc3_out, Rm5_out, Rm5_len, Rm5_wth, Rm5_dc1_out, Rm5_dc2_out, Rm5_dc3_out, Rm6_out, Rm6_len, Rm6_wth, Rm6_dc1_out, Rm6_dc2_out, Rm6_dc3_out, Rm7_out, Rm7_len, Rm7_wth, Rm7_dc1_out, Rm7_dc2_out, Rm7_dc3_out, Rm8_out, Rm8_len, Rm8_wth, Rm8_dc1_out, Rm8_dc2_out, Rm8_dc3_out, Rm9_out, Rm9_len, Rm9_wth, Rm9_dc1_out, Rm9_dc2_out, Rm9_dc3_out, Rm10_out, Rm10_len, Rm10_wth, Rm10_dc1_out, Rm10_dc2_out, Rm10_dc3_out, Rm11_out, Rm11_len, Rm11_wth, Rm11_dc1_out, Rm11_dc2_out, Rm11_dc3_out, Rm12_out, Rm12_len, Rm12_wth, Rm12_dc1_out, Rm12_dc2_out, Rm12_dc3_out, Rltr, Lp_dol, Timestamp_sql, Tour_url, Addr FROM {0} WHERE Ml_num = %s AND Status='A';".format(
            residence_type
        )
    elif residence_type == "condo":
        query = "SELECT Type_own1_out, Style, Bath_tot, Locker_num, Maint, Water_inc, Park_spcs, Fpl_num, Fuel, Cross_st, Pets, Occ, Taxes, S_r, Br, Br_plus, Tot_park_spcs, A_c, Gar_type, Park_desig, Heating, Constr1_out, Locker, Addr, Park_fac, Level1, Level2, Level3, Level4, Level5, Level6, Level7, Level8, Level9, Level10, Level11, Level12, Rm1_out, Rm1_len, Rm1_wth, Rm1_dc1_out, Rm1_dc2_out, Rm1_dc3_out, Rm2_out, Rm2_len, Rm2_wth, Rm2_dc1_out, Rm2_dc2_out, Rm2_dc3_out, Rm3_out, Rm3_len, Rm3_wth, Rm3_dc1_out, Rm3_dc2_out, Rm3_dc3_out, Rm4_out, Rm4_len, Rm4_wth, Rm4_dc1_out, Rm4_dc2_out, Rm4_dc3_out, Rm5_out, Rm5_len, Rm5_wth, Rm5_dc1_out, Rm5_dc2_out, Rm5_dc3_out, Rm6_out, Rm6_len, Rm6_wth, Rm6_dc1_out, Rm6_dc2_out, Rm6_dc3_out, Rm7_out, Rm7_len, Rm7_wth, Rm7_dc1_out, Rm7_dc2_out, Rm7_dc3_out, Rm8_out, Rm8_len, Rm8_wth, Rm8_dc1_out, Rm8_dc2_out, Rm8_dc3_out, Rm9_out, Rm9_len, Rm9_wth, Rm9_dc1_out, Rm9_dc2_out, Rm9_dc3_out, Rm10_out, Rm10_len, Rm10_wth, Rm10_dc1_out, Rm10_dc2_out, Rm10_dc3_out, Rm11_out, Rm11_len, Rm11_wth, Rm11_dc1_out, Rm11_dc2_out, Rm11_dc3_out, Rm12_out, Rm12_len, Rm12_wth, Rm12_dc1_out, Rm12_dc2_out, Rm12_dc3_out, Rltr, Lp_dol, Timestamp_sql, Tour_url, Bldg_amen1_out, Bldg_amen2_out, Bldg_amen3_out, Bldg_amen4_out, Bldg_amen5_out, Bldg_amen6_out FROM {0} WHERE Ml_num = %s AND Status='A';".format(
            residence_type
        )
    elif residence_type == "commercial":
        query = "SELECT Prop_type, Front_ft, Depth, Gar_type, Heating, Freestandg, S_r, Taxes, Water, Bus_type, Cross_st, Rltr, Lp_dol, Timestamp_sql, Addr, Community FROM {0} WHERE Ml_num = %s AND Status='A';".format(
            residence_type
        )
    cursor.execute(query, (mls_num,))
    result = cursor.fetchone()
    if residence_type == "residential":
        obj = {
            "property_type": result[0],
            "house_style": result[1],
            "bathrooms": result[2],
            "land_size": str(result[3]) + " x " + str(result[4]) + " FT",
            "water": result[5],
            "parking_places": result[6],
            "fireplace": result[7],
            "heating_fuel": result[8],
            "cross_street": result[9],
            "basement": result[10],
            "possession_date": result[11],
            "property_tax": result[12],
            "sale_lease": result[13],
            "bedrooms": str(result[14]) + " + " + str(result[15]),
            "total_parking": result[16],
            "central_ac": result[17],
            "garage_spaces": result[18],
            "driveway": result[19],
            "heating_type": result[20],
            "pool_type": result[21],
            "exterior": result[22],
            "fronting_on": result[23],
            "front_footage": result[24],
            "levels": [
                result[25],
                result[26],
                result[27],
                result[28],
                result[29],
                result[30],
                result[31],
                result[32],
                result[33],
                result[34],
                result[35],
                result[36],
            ],
            "rooms": [
                [
                    result[37],
                    str(result[38]) + "m x " + str(result[39]) + "m",
                    result[40],
                    result[41],
                    result[42],
                ],
                [
                    result[43],
                    str(result[44]) + "m x " + str(result[45]) + "m",
                    result[46],
                    result[47],
                    result[48],
                ],
                [
                    result[49],
                    str(result[50]) + "m x " + str(result[51]) + "m",
                    result[52],
                    result[53],
                    result[54],
                ],
                [
                    result[55],
                    str(result[56]) + "m x " + str(result[57]) + "m",
                    result[58],
                    result[59],
                    result[60],
                ],
                [
                    result[61],
                    str(result[62]) + "m x " + str(result[63]) + "m",
                    result[64],
                    result[65],
                    result[66],
                ],
                [
                    result[67],
                    str(result[68]) + "m x " + str(result[69]) + "m",
                    result[70],
                    result[71],
                    result[72],
                ],
                [
                    result[73],
                    str(result[74]) + "m x " + str(result[75]) + "m",
                    result[76],
                    result[77],
                    result[78],
                ],
                [
                    result[79],
                    str(result[80]) + "m x " + str(result[81]) + "m",
                    result[82],
                    result[83],
                    result[84],
                ],
                [
                    result[85],
                    str(result[86]) + "m x " + str(result[87]) + "m",
                    result[88],
                    result[89],
                    result[90],
                ],
                [
                    result[91],
                    str(result[92]) + "m x " + str(result[93]) + "m",
                    result[94],
                    result[95],
                    result[96],
                ],
                [
                    result[97],
                    str(result[98]) + "m x " + str(result[99]) + "m",
                    result[100],
                    result[101],
                    result[102],
                ],
                [
                    result[103],
                    str(result[104]) + "m x " + str(result[105]) + "m",
                    result[106],
                    result[107],
                    result[108],
                ],
            ],
            "realtor": result[109],
            "price": result[110],
            "date": result[111],
            "tour_url": result[112],
            "address": result[113],
        }
    elif residence_type == "condo":
        obj = {
            "property_type": result[0],
            "house_style": result[1],
            "bathrooms": result[2],
            "locker_num": result[3],
            "maintenance": result[4],
            "water": result[5],
            "parking_places": result[6],
            "fireplace": result[7],
            "heating_fuel": result[8],
            "cross_street": result[9],
            "pets": result[10],
            "possession_date": result[11],
            "property_tax": result[12],
            "sale_lease": result[13],
            "bedrooms": str(result[14]) + " + " + str(result[15]),
            "total_parking": result[16],
            "central_ac": result[17],
            "garage_type": result[18],
            "parking_type": result[19],
            "heating_type": result[20],
            "exterior": result[21],
            "locker": result[22],
            "address": result[23],
            "parking_drive": result[24],
            "levels": [
                result[25],
                result[26],
                result[27],
                result[28],
                result[29],
                result[30],
                result[31],
                result[32],
                result[33],
                result[34],
                result[35],
                result[36],
            ],
            "rooms": [
                [
                    result[37],
                    str(result[38]) + "m x " + str(result[39]) + "m",
                    result[40],
                    result[41],
                    result[42],
                ],
                [
                    result[43],
                    str(result[44]) + "m x " + str(result[45]) + "m",
                    result[46],
                    result[47],
                    result[48],
                ],
                [
                    result[49],
                    str(result[50]) + "m x " + str(result[51]) + "m",
                    result[52],
                    result[53],
                    result[54],
                ],
                [
                    result[55],
                    str(result[56]) + "m x " + str(result[57]) + "m",
                    result[58],
                    result[59],
                    result[60],
                ],
                [
                    result[61],
                    str(result[62]) + "m x " + str(result[63]) + "m",
                    result[64],
                    result[65],
                    result[66],
                ],
                [
                    result[67],
                    str(result[68]) + "m x " + str(result[69]) + "m",
                    result[70],
                    result[71],
                    result[72],
                ],
                [
                    result[73],
                    str(result[74]) + "m x " + str(result[75]) + "m",
                    result[76],
                    result[77],
                    result[78],
                ],
                [
                    result[79],
                    str(result[80]) + "m x " + str(result[81]) + "m",
                    result[82],
                    result[83],
                    result[84],
                ],
                [
                    result[85],
                    str(result[86]) + "m x " + str(result[87]) + "m",
                    result[88],
                    result[89],
                    result[90],
                ],
                [
                    result[91],
                    str(result[92]) + "m x " + str(result[93]) + "m",
                    result[94],
                    result[95],
                    result[96],
                ],
                [
                    result[97],
                    str(result[98]) + "m x " + str(result[99]) + "m",
                    result[100],
                    result[101],
                    result[102],
                ],
                [
                    result[103],
                    str(result[104]) + "m x " + str(result[105]) + "m",
                    result[106],
                    result[107],
                    result[108],
                ],
            ],
            "realtor": result[109],
            "price": result[110],
            "date": result[111],
            "tour_url": result[112],
            "building_amenities": ("" if result[113] == None else str(result[113]))
            + ("" if result[114] == None else ", " + str(result[114]))
            + ("" if result[115] == None else ", " + str(result[115]))
            + ("" if result[116] == None else ", " + str(result[116]))
            + ("" if result[117] == None else ", " + str(result[117])),
        }
    elif residence_type == "commercial":
        obj = {
            "property_type": result[0],
            "land_size": str(result[1]) + " x " + str(result[2]) + " FT",
            "garage_type": result[3],
            "heating_type": result[4],
            "freestanding": result[5],
            "sale_lease": result[6],
            "property_tax": result[7],
            "water": result[8],
            "use": result[9],
            "cross_street": result[10],
            "realtor": result[11],
            "price": result[12],
            "date": result[13],
            "address": result[14],
            "community": result[15],
        }
    response = jsonify(obj)
    return response


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
