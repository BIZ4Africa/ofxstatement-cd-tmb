import csv
import re
import random

from decimal import Decimal as D

from ofxstatement import statement
from ofxstatement.statement import generate_transaction_id
from ofxstatement.statement import generate_unique_transaction_id

from ofxstatement.parser import CsvStatementParser
from ofxstatement.plugin import Plugin


class TmbCdPlugin(Plugin):
    """TMB Congo Plugin
    """

    def get_parser(self, filename):
        f = open(filename, 'r', encoding=self.settings.get("charset", "UTF-8"))
        parser = TmbCdParser(f)
        return parser

class TmbCdParser(CsvStatementParser):

    date_format = "%d %b %Y"
    mappings = {
        # 'check_no': 3,
        'date': 0,
        'refnum': 3,
        'memo': 2,
        'amount': 5,
        'id': 3
    }

    unique_id_set = set()
    def parse(self):
        """Main entry point for parsers

        super() implementation will call to split_records and parse_record to
        process the file.
        """
        stmt = super(TmbCdParser, self).parse()
        statement.recalculate_balance(stmt)
        return stmt

    def split_records(self):
        """Return iterable object consisting of a line per transaction
        """
        
        reader = csv.reader(self.fin, delimiter=',')
        next(reader, None)
        return reader

    def fix_amount(self, value):
        dbt_re = r"(.*)(Dr)$"
        cdt_re = r"Cr$"
        dbt_subst = "-\\1"
        cdt_subst = ""
        result = re.sub(dbt_re, dbt_subst, value, 0)
        result = re.sub(cdt_re, cdt_subst, result, 0)

        #Consider "--" as a reversal entry
        reversal_re = r"^--"
        reversal_subst = ""
        return re.sub(reversal_re, reversal_subst, result, 0)


    def parse_record(self, line):
        """Parse given transaction line and return StatementLine object
        """

        #Valuable lines has 9 elements
        if len(line) <=9:
            if line[0] == "Opening Balance":
                res = line[1].split();
                self.statement.currency=res[0]
                self.statement.start_balance=D(res[1])
                return None
        elif len(line) < 8:
            return None


        if (self.statement.currency and  (len(line) < 4 or not (line[4] ==  self.statement.currency))):
            return None


        date = line[0]
        date_value = line[1]
        description = line[2]
        transaction_id = line[3]
        currency = line[4]
        amount = self.fix_amount(line[5])
        line[5] = amount
        if(date.find('-') != -1):
            self.date_format = "%d-%b-%y"
        else:
            self.date_format = "%d %b %Y"

        stmtline = super(TmbCdParser, self).parse_record(line)
        stmtline.trntype = 'DEBIT' if stmtline.amount < 0 else 'CREDIT'
        stmtline.id = generate_unique_transaction_id(stmtline, self.unique_id_set)

        return stmtline
