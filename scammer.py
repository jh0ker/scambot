import datetime

from pony.orm import *
from database import db


class Scammer(db.Entity):
    id = PrimaryKey(int, auto=False)
    first_name = Required(str)
    last_name = Optional(str)
    username = Optional(str)
    created = Required(datetime.datetime, default=datetime.datetime.now)
