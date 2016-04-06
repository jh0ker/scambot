import datetime

from pony.orm import *
from database import db


class Scammer(db.Entity):
    phone_nr = Optional(str)
    account_nr = Optional(str)
    bank_name = Optional(str)
    remark = Optional(str)
    reported_by = Set("Reporter")
    added_by = Required("Admin")
    created = Required(datetime.datetime, default=datetime.datetime.now)

    def __str__(self):
        reported_count = len(self.reported_by)
        reported_list = ', '.join(
            [str(reporter) for reporter in self.reported_by][:3]) + (
                ' and %d others' % (reported_count - 3)
                if reported_count > 3
                else '')

        s = "<b>Report #{id}</b>\n" \
            "Phone Nr.: {phone_nr}\n" \
            "Bank Account Nr.: {account_nr}\n" \
            "Bank Account Name: {bank_name}\n" \
            "Admin remark: {remark}\n" \
            "Reported by: {reported_by}\n" \
            "Added by: {added_by}\n" \
            "Confirm report: /confirm_{id}".format(
                id=self.id,
                phone_nr=self.phone_nr,
                account_nr=self.account_nr,
                bank_name=self.bank_name,
                remark=self.remark,
                reported_by=reported_list,
                added_by=str(self.added_by)
        )

        return s

    def __repr__(self):
        return str(self)
