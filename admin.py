import datetime

from pony.orm import *
from database import db


class Admin(db.Entity):
    id = PrimaryKey(int, auto=False)
    first_name = Required(str)
    last_name = Optional(str)
    username = Optional(str)
    super_admin = Optional(bool, default=False)
    created = Required(datetime.datetime, default=datetime.datetime.now)
