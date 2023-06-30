from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from bs4 import BeautifulSoup, SoupStrainer
import requests
import os
from dotenv import load_dotenv
from discord import SyncWebhook

app = Flask(__name__)


# Get environment variables ----------------------------------
load_dotenv(dotenv_path=".\env\.env")
URL = os.getenv("URL")
headers_string = os.getenv("HEADERS")
HEADERS = eval(headers_string)
URL_WEBHOOK = os.getenv("URL_WEBHOOK")
ROLE_ID = os.getenv("ROLE_ID")
# -------------------------------------------------------------


# Setup database ----------------------------------------------
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Matkul(db.Model):
    id_matkul = db.Column(db.Integer, primary_key=True)
    kode = db.Column(db.String(10))
    name = db.Column(db.String(50), nullable=False)
    updated = db.Column(db.Boolean)

    def __init__(self, id_matkul, kode, name, updated):
        self.id_matkul = id_matkul
        self.kode = kode
        self.name = name
        self.updated = updated

    def __repr__(self):
        return f'<Matkul {self.id_matkul}>'


class Checked(db.Model):
    id_checked = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.DateTime(timezone=True))
    found = db.Column(db.Boolean)

    def __init__(self, time, found):
        self.time = time
        self.found = found

    def __repr__(self):
        return f'<Checked {self.time}>'


class Found(db.Model):
    id_found = db.Column(db.Integer, primary_key=True)
    id_checked = db.Column(db.Integer, db.ForeignKey("checked.id_checked"), nullable=False)
    id_matkul = db.Column(db.Integer, db.ForeignKey("matkul.id_matkul"), nullable=False)

    def __init__(self, id_checked, id_matkul):
        self.id_checked = id_checked
        self.id_matkul = id_matkul

    def __repr__(self):
        return f'<Found {self.id_matkul}>'
# -------------------------------------------------------------




@app.route("/", methods=["GET", "POST"])
def index():
    daftar_matkul = Matkul.query.order_by(Matkul.id_matkul).all()
    if request.method == "POST":
        check_update()
        return render_template("index.html", daftar_matkul=daftar_matkul)
    else: 
        return render_template("index.html", daftar_matkul=daftar_matkul)


@app.route("/matkul/<id>", methods=["GET", "POST"])
def show_matkul(id):
    matkul = Matkul.query.filter_by(id_matkul=id).first()
    return render_template("show-matkul.html", matkul=matkul)



# Initializing tabel Matkul if empty --------------------------

def is_table_empty(table):
    row = table.query.first()
    return row is None

def innit_db_matkul():
    list_data = getData()
    for i in range(len(list_data)):
        if "SVPL" in list_data[i]:
            new_matkul = Matkul(int(list_data[i-1]), list_data[i], list_data[i+1], False)
            if list_data[i+5].isdigit() and list_data[i+6].isdigit():
                new_matkul.updated = True
            try:
                db.session.add(new_matkul)
                db.session.commit()
            except Exception as e:
                print(f"Error adding new matkul: {str(e)}")

def getData() -> list:
    global URL, HEADERS
    response = requests.get(URL, headers=HEADERS)
    strainer = SoupStrainer("td")
    soup = BeautifulSoup(response.text, "html.parser", parse_only=strainer)
    list_word = soup.prettify().split("\n")
    list_data = []

    for word in list_word:
        if "<" in word:
            continue
        else:
            list_data.append(word.strip())

    return list_data

# -------------------------------------------------------------



# Check for updates -------------------------------------------
def check_update():
    current_time = datetime.now()
    new_check = Checked(current_time, False)

    try:
        db.session.add(new_check)
        db.session.commit()
    except Exception as e:
        print(f"Error adding new checked: {str(e)}")


    list_data = getData()
    for i in range(len(list_data)):
        # Mengecek apakah nilai sudah keluar di setiap matkul
        if "SVPL" in list_data[i] and status_changed(list_data[i-1:i+7]):
            current_check = Checked.query.filter_by(time=current_time).first()
            current_check.found = True
            db.session.commit()

            new_found = Found(current_check.id_checked, int(list_data[i-1]))
            try:
                db.session.add(new_found)
                db.session.commit()
            except Exception as e:
                print(f"Error adding new found: {str(e)}")

            update_status(list_data[i])
            send_notification(list_data[i+1])


def update_status(kode):
    matkul = Matkul.query.filter_by(kode=kode).first()
    matkul.updated = True
    db.session.commit()

def status_changed(data_matkul):
    matkul = Matkul.query.filter_by(id_matkul=data_matkul[0]).first()
    if data_matkul[6].isdigit() and data_matkul[7].isdigit() and matkul.updated == False:
        return True
    else:
        return False

def send_notification(nama_matkul):
    global URL_WEBHOOK, ROLE_ID
    # Initializing webhook
    webhook = SyncWebhook.from_url(URL_WEBHOOK)
    text = f"📢 📢 Nilai pada **{nama_matkul}** telah ditambah 🔔<@&>🔔"
    # Executing webhook
    webhook.send(content=text) 
# -------------------------------------------------------------



# Main --------------------------------------------------------
with app.app_context():
    db.create_all()
    if is_table_empty(Matkul):
        innit_db_matkul()


if __name__ == "__main__":
    app.run(debug=True)
# -------------------------------------------------------------






# wib = pytz.timezone("Asia/Jakarta")
# a = datetime.now(tz=wib)