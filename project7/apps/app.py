import os
import pathlib

import requests
from flask import Flask, session, abort, redirect, request, render_template
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests

#############
from flask_sqlalchemy import SQLAlchemy
from flask import after_this_request

##############

app = Flask("Google Login App")
app.secret_key = "CodeSpecialist.com"


##############
# SQLAlchemy 초기화
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///login_info.db"  # SQLite 데이터베이스를 사용하도록 설정
)
db = SQLAlchemy(app)


# 사용자 모델 정의
class User(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)
    email = db.Column(db.String)


# 데이터베이스 생성 및 초기화
with app.app_context():
    db.create_all()
##############


os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# 유출 조심 / client_secret.json 유출 금지
GOOGLE_CLIENT_ID = (
    # GCP 종료
    "200475201819-kjn35ua9q131d6f7ohru6qpus0h6cbue.apps.googleusercontent.com"
)
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=[
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid",
    ],
    redirect_uri="http://127.0.0.1:5000/callback",
)


def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function()

    return wrapper


@app.route("/")
def index():
    return render_template("home.html")


@app.route("/googlelogin")
def google_login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)


@app.route("/study")
def study():
    return render_template("study.html")


@app.route("/report")
def report():
    return render_template("report.html")


# @app.route("/logout")
# def logout():
#     session.clear()
#     return redirect("/")


# @app.route("/studycam")
# def study_cam():
#     return render_template("cam_page.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token, request=token_request, audience=GOOGLE_CLIENT_ID
    )

    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")

    ###
    # 데이터베이스에 사용자 정보 저장
    existing_user = User.query.filter_by(id=id_info.get("sub")).first()

    if not existing_user:
        # 사용자가 데이터베이스에 없는 경우에만 추가
        user = User(
            id=id_info.get("sub"), name=id_info.get("name"), email=id_info.get("email")
        )
        db.session.add(user)
        db.session.commit()
    ###

    return redirect("/google_protected_area")


@app.route("/google_protected_area")
@login_is_required
def google_protected_area():
    user = User.query.filter_by(id=session["google_id"]).first()
    return render_template("logined_home.html", user=user)


##################
@app.after_request
def add_no_cache_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


##################

if __name__ == "__main__":
    app.run(debug=True)
