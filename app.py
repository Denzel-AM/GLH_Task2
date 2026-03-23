from flask import Flask, render_template, request, redirect, url_for, flash , session
from datetime import datetime, date
import os
import re
import shutil
import json
from datetime import date, datetime
from models import db
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from config import get_config


app = Flask(__name__)
get_config(app)

with app.app_context():
    db.create_all()
    


if __name__ == "__main__":
    app.run(debug=True)