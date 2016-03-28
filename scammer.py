import datetime

from pony.orm import *
from database import db


class Scammer(db.Entity):
    id = PrimaryKey(int, auto=False)
    first_name = Required(str)
    last_name = Optional(str)
    username = Optional(str)
    phone_nr = Optional(str)
    account_nr = Optional(str)
    bank_name = Optional(str)
    remark = Optional(str)
    created = Required(datetime.datetime, default=datetime.datetime.now)

    def __str__(self):
        s = "Telegram account info (last known)\n" \
            "First name: {first_name}\n" \
            "Last name: {last_name}\n" \
            "Username: {username}\n\n" \
            "Other info\n" \
            "Phone Nr.: {phone_nr}\n" \
            "Bank Account Nr.: {account_nr}\n" \
            "Bank Account Name: {bank_name}\n" \
            "Admin remark: {remark}".format(
                first_name=self.first_name,
                last_name=self.last_name,
                username=self.username,
                phone_nr=self.phone_nr,
                account_nr=self.account_nr,
                bank_name=self.bank_name,
                remark=self.remark
            )

        return s

    def __repr__(self):
        return str(self)
