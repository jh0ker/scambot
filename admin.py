import datetime

from pony.orm import *
from database import db


class Admin(db.Entity):
    id = PrimaryKey(int, auto=False)
    first_name = Required(str)
    last_name = Optional(str)
    username = Optional(str)
    super_admin = Optional(bool, default=False)
    scammers_added = Set("Scammer")
    created = Required(datetime.datetime, default=datetime.datetime.now)

    def __str__(self):
        s = self.first_name
        if self.last_name:
            s += " " + self.last_name

        if self.username:
            s += " (@%s)" % self.username

        return s
