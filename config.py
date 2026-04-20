from flask import Flask
from models import db, User
import os
from dotenv import load_dotenv
import stripe
load_dotenv()


class Config:
    SECRET_KEY = 'GLH_Task_2_Secret_Key'
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///glh.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STRIPE_PUBLIC_KEY = "pk_test_51TOHtNRpRjKZYQIFx33rUPwiminwg2X1goYOE5bP8CiepvJ1VCdTmlTmfJaJVTPX71s18pJ0D3Qc1I68dnxZxtM900MjQPbmSC"
    STRIPE_SECRET_KEY = "sk_test_51TOHtNRpRjKZYQIFbtCamo9PUDyS7seHHQLYZIuaqy2pniiHb6nTuoVtHqx9CfTEEfQeXmfsPb4FLURjp8VtfFjo00pihN2Yo8"


def get_config(app: Flask):
    app.secret_key = 'GLH_Task_2_Secret_Key'
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///glh.db"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config["STRIPE_PUBLIC_KEY"] = os.environ.get("STRIPE_PUBLIC_KEY")
    db.init_app(app)






