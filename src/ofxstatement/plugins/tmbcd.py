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
    filetype = None

    def _setFileType(self):
        self.filetype = "pdf"
        with open(self.fin.name, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            for line in reader:
                if len(line) != 7:
                    self.filetype = "csv"
                    break
        if self.filetype == "pdf":
            self.mappings = {
                # 'check_no': 3,
                'date': 2,
                'refnum': 0,
                'memo': 1,
                'amount': 4,
                'id': 0
            }

    def parse(self):
        """Main entry point for parsers

        super() implementation will call to split_records and parse_record to
        process the file.
        """
        self._setFileType()
        stmt = super(TmbCdParser, self).parse()
        total_amount = sum(sl.amount for sl in stmt.lines)
        stmt.start_balance = D(stmt.end_balance) -total_amount
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


        if self.filetype == "pdf":
            return self.parse_record_pdf(line)
        else:
            return self.parse_record_csv(line)


    def parse_record_pdf(self, line):

        if not self.statement.currency:
            # We are on second  line
            self.statement.currency = line[6][-3:]
            self.statement.end_balance = str(line[6][0:-3]).replace(',','')
            self.statement.end_date = line[2]
            if(line[2].find('-') != -1):
                self.date_format = "%d-%b-%y"
            else:
                self.date_format = "%d %b %Y"

        if not len(line[0]) and not len(line[2]):
            #Continuation of previous line memo
            cur_idx = len(self.statement.lines) - 1
            self.statement.line[cur_idx].memo = self.statement.line[cur_idx] + " " + line[1]
            return None

        if (len(line[4])):
            tx_type="CREDIT"
        elif len(line[5]):
            tx_type = "DEBIT"

        amount = line[4][0:-3] if len(line[4]) else "-" + line[5][0:-3]
        line[4] = str(amount).replace(',', '')
        stmtline = super(TmbCdParser, self).parse_record(line)
        stmtline.trntype = tx_type
        stmtline.id = generate_unique_transaction_id(stmtline, self.unique_id_set)

        return stmtline


    def parse_record_csv(self, line):
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
