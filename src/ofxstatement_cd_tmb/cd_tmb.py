from typing import Iterable

from ofxstatement.plugin import Plugin
from ofxstatement.parser import CsvStatementParser
from ofxstatement.statement import Statement, StatementLine


class TmbCdPlugin(Plugin):
    """TMB Congo Plugin
    """

    def get_parser(self, filename: str) -> "TmbCdParser":
        return TmbCdParser(filename)
    
class TmbCdCSVParser(CsvStatementParser[str]):
    #TODO #5 - Implement CSV and PDF parsing as two parsers
    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename
        self.date_format = "%d %b %Y"
        self.source_file_type = None
        self._get_source_file_type()
        self._set_mappings()
        
    def _set_mappings(self) -> None:
        self.mappings = {
            "date": 0,
            "refnum": 3,
            "memo": 2,
            "amount": 5,
            "id": 3
        }
        if self.source_file_type == "pdf":
            self.mappings = {
                "date": 2,
                "refnum": 0,
                "memo": 1,
                "amount": 4,
                "id": 0
            }
        
    def _get_source_file_type(self) -> None:
        self.source_file_type = "pdf"
        with open(self.filename, "r") as f:
            for line in f:
                if len(line.split(",")) != 7:
                    if line.split(",")[0] != "Reference Number":
                        self.source_file_type = "csv"
                    break
        
    def parse(self) -> Statement:
        """Main entry point for parsers

        super() implementation will call to split_records and parse_record to
        process the file.
        """
        with open(self.filename, "r") as f:
            return super().parse()
    
    def split_records(self) -> Iterable[str]:
        """Return iterable object consisting of a line per transaction"""
        return []

    def parse_record(self, line: str) -> StatementLine:
        """Parse given transaction line and return StatementLine object"""
        return StatementLine()
    
    def parse_value(self, value: Optional[str], field: str) -> Any:
        value = value.strip() if value else value
        # if field == "amount" and isinstance(value, float):
        #     return Decimal(value)

        # if field == "trntype":
            # Default: Debit card payment
            # return TRANSACTION_TYPES.get(value, "POS")
        if field == "currency":
            return self.parse_currency(value, field)

        return super().parse_value(value, field)