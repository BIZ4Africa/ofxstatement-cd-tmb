"""OFXStatement plugin for TMB Congo bank."""

import csv
import re
from decimal import Decimal as D

from ofxstatement import statement
from ofxstatement.parser import CsvStatementParser
from ofxstatement.plugin import Plugin
from ofxstatement.statement import generate_unique_transaction_id


class TmbCdPlugin(Plugin):
    """TMB Congo Plugin"""

    def get_parser(self, filename: str) -> "TmbCdParser":
        f = open(filename, "r", encoding=self.settings.get("charset", "UTF-8"))
        parser = TmbCdParser(f)
        return parser


class TmbCdParser(CsvStatementParser):
    """Parser for TMB Congo bank statements (supports both CSV and PDF exports)"""

    date_format = "%d %b %Y"
    mappings = {"date": 0, "refnum": 3, "memo": 2, "amount": 5, "id": 3}

    unique_id_set = set()
    filetype = None

    def _set_file_type(self):
        """Detect whether the file is CSV or PDF export format"""
        self.filetype = "pdf"
        self.fin.seek(0)  # Reset file pointer
        reader = csv.reader(self.fin, delimiter=",", quotechar='"')
        for line in reader:
            if len(line) != 7:
                if line and line[0] != "Reference Number":
                    self.filetype = "csv"
                break
        self.fin.seek(0)  # Reset file pointer for parsing

        if self.filetype == "pdf":
            self.mappings = {"date": 2, "refnum": 0, "memo": 1, "amount": 4, "id": 0}

    def parse(self):
        """Main entry point for parsers

        super() implementation will call to split_records and parse_record to
        process the file.
        """
        self._set_file_type()
        stmt = super(TmbCdParser, self).parse()

        # Calculate start balance from end balance and transactions only if not already set
        if stmt.lines and not stmt.start_balance:
            total_amount = sum(sl.amount for sl in stmt.lines)
            stmt.start_balance = D(stmt.end_balance) - total_amount
            stmt.start_date = min(sl.date for sl in stmt.lines)
        elif stmt.lines and not stmt.start_date:
            stmt.start_date = min(sl.date for sl in stmt.lines)

        statement.recalculate_balance(stmt)
        return stmt

    def split_records(self):
        """Return iterable object consisting of a line per transaction"""
        reader = csv.reader(self.fin, delimiter=",")
        next(reader, None)  # Skip header
        return reader

    def fix_amount(self, value):
        """Convert amount string with Dr/Cr suffix to signed decimal"""
        dbt_re = r"(.*)(Dr)$"
        cdt_re = r"Cr$"
        dbt_subst = "-\\1"
        cdt_subst = ""
        result = re.sub(dbt_re, dbt_subst, value, 0)
        result = re.sub(cdt_re, cdt_subst, result, 0)

        # Consider "--" as a reversal entry
        reversal_re = r"^--"
        reversal_subst = ""
        return re.sub(reversal_re, reversal_subst, result, 0)

    def _clean_date_field(self, date_str):
        """Clean date field to handle column overlap issues from PDF extraction.

        Extracts valid date pattern from potentially contaminated data.
        Handles formats like:
        - 'e-07 Mar 2025' -> '07 Mar 2025'
        - '(Atm2)6- Aug 2025' -> '6 Aug 2025'
        - '07-Mar-25' -> '07-Mar-25'
        - '07 Mar 2025' -> '07 Mar 2025'
        - '2023-11-08' -> '2023-11-08' (YYYY-MM-DD)

        Args:
            date_str: Potentially contaminated date string

        Returns:
            Cleaned date string
        """
        if not date_str:
            return date_str

        # Pattern 0a: YYYY-MM-DD format (numeric date with dashes)
        match = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", date_str)
        if match:
            return match.group(0)

        # Pattern 0b: YYYY/MM/DD format (numeric date with slashes)
        match = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})", date_str)
        if match:
            return match.group(0)

        # Pattern 1: DD Mon YYYY format with flexible separators (e.g., "6- Aug 2025", "07 Mar 2025")
        # Match digits for day, optional dash/space, month name, optional dash/space, year
        match = re.search(r"(\d{1,2})[-\s]+([A-Za-z]{3})[-\s]+(\d{4})", date_str)
        if match:
            day, month, year = match.groups()
            # Normalize with single spaces
            return f"{day} {month} {year}"

        # Pattern 2: DD-Mon-YY format (e.g., "07-Mar-25")
        match = re.search(r"(\d{1,2})-([A-Za-z]{3})-(\d{2})", date_str)
        if match:
            # Return as-is with dashes
            return match.group(0)

        # If no pattern matches, return original (may still fail but with clear error)
        return date_str.strip()

    def _detect_date_format(self, date_str):
        """Detect the date format from a sample date string.

        Tries to identify common date formats:
        - "%Y-%m-%d" (e.g., "2023-11-08")
        - "%d-%b-%y" (e.g., "08-Nov-23")
        - "%d %b %Y" (e.g., "08 Nov 2023")

        Args:
            date_str: Sample date string to analyze

        Returns:
            Best matching date format string
        """
        date_str = date_str.strip()

        # Pattern: YYYY-MM-DD (numeric only with dashes)
        if re.match(r"^\d{4}-\d{1,2}-\d{1,2}$", date_str):
            return "%Y-%m-%d"

        # Pattern: YYYY/MM/DD (numeric only with slashes)
        if re.match(r"^\d{4}/\d{1,2}/\d{1,2}$", date_str):
            return "%Y/%m/%d"

        # Pattern: DD-Mon-YY (with month abbreviations like Nov, Mar, etc.)
        if re.match(r"^\d{1,2}-[A-Za-z]{3}-\d{2}$", date_str):
            return "%d-%b-%y"

        # Pattern: DD Mon YYYY (with spaces)
        if re.match(r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}$", date_str):
            return "%d %b %Y"

        # Default fallback
        return "%d %b %Y"

    def parse_record(self, line):
        """Parse given transaction line and return StatementLine object"""
        if self.filetype == "pdf":
            return self.parse_record_pdf(line)
        else:
            return self.parse_record_csv(line)

    def parse_record_pdf(self, line):
        """Parse PDF export format"""
        if line[0] == "Reference Number":
            # This is the title line
            return None

        # Handle balance rows injected from PDF text extraction
        if line[0] == "Opening Balance":
            # Parse balance: "566.61USD" or "566.61 USD"
            balance_str = line[1].strip() if len(line) > 1 else ""
            if balance_str:
                # Extract numeric value and currency
                match = re.match(r"^([-\d.,]+)\s*([A-Z]{3})$", balance_str)
                if match:
                    value_str = match.group(1).replace(",", "")
                    currency = match.group(2)
                    try:
                        self.statement.start_balance = D(value_str)
                        if not self.statement.currency:
                            self.statement.currency = currency
                    except (ValueError, IndexError) as e:
                        raise ValueError(
                            f"Failed to parse opening balance from PDF: '{balance_str}' - {e}"
                        ) from e
            return None

        if line[0] == "Closing Balance":
            # Parse balance: "-190.32USD" or "-190.32 USD"
            balance_str = line[1].strip() if len(line) > 1 else ""
            if balance_str:
                # Extract numeric value and currency
                match = re.match(r"^([-\d.,]+)\s*([A-Z]{3})$", balance_str)
                if match:
                    value_str = match.group(1).replace(",", "")
                    currency = match.group(2)
                    try:
                        self.statement.end_balance = D(value_str)
                        if not self.statement.currency:
                            self.statement.currency = currency
                    except (ValueError, IndexError) as e:
                        raise ValueError(
                            f"Failed to parse closing balance from PDF: '{balance_str}' - {e}"
                        ) from e
            return None

        if not self.statement.currency:
            # We are on second line (fallback if balances weren't extracted)
            self.statement.currency = line[6][-3:]
            try:
                self.statement.end_balance = str(line[6][0:-3]).replace(",", "")
            except (ValueError, IndexError) as e:
                raise ValueError(
                    f"Failed to parse end balance from PDF line: '{line[6]}' - {e}"
                ) from e
            self.statement.end_date = line[2]
            # Detect date format from the end_date
            self.date_format = self._detect_date_format(line[2])

        if not line[0] and not line[2]:
            # Continuation of previous line memo
            cur_idx = len(self.statement.lines) - 1
            self.statement.lines[cur_idx].memo = (
                self.statement.lines[cur_idx].memo + " " + line[1]
            )
            return None

        if line[4]:
            tx_type = "CREDIT"
        elif line[5]:
            tx_type = "DEBIT"
        else:
            return None

        amount = line[4][0:-3] if len(line[4]) else "-" + line[5][0:-3]
        line[4] = str(amount).replace(",", "")

        # Clean date field to handle column overlap issues
        # Extract valid date pattern from potentially contaminated data
        line[2] = self._clean_date_field(line[2])

        # Skip rows with empty dates (invalid/corrupted data)
        if not line[2] or not line[2].strip():
            return None

        # Detect and update date format for this specific record
        # This handles mixed date formats in the same file
        self.date_format = self._detect_date_format(line[2])

        try:
            statement_line = super(TmbCdParser, self).parse_record(line)
        except ValueError as e:
            raise ValueError(
                f"Failed to parse PDF record line. "
                f"Amount: '{amount}', Date: '{line[2]}', Memo: '{line[1]}' - {e}"
            ) from e
        statement_line.trntype = tx_type
        statement_line.id = generate_unique_transaction_id(
            statement_line, self.unique_id_set
        )

        return statement_line

    def parse_record_csv(self, line):
        """Parse CSV export format"""
        # Skip header row
        if line[0] == "Transaction Date":
            return None

        # Valuable lines have 9 elements
        if len(line) <= 9:
            if line[0] == "Opening Balance":
                res = line[1].split()
                self.statement.currency = res[0]
                try:
                    self.statement.start_balance = D(res[1])
                except (ValueError, IndexError) as e:
                    raise ValueError(
                        f"Failed to parse opening balance from CSV: '{line[1]}' - {e}"
                    ) from e
                return None
            if line[0] == "Closing Balance":
                res = line[1].split()
                try:
                    self.statement.end_balance = D(res[1])
                except (ValueError, IndexError) as e:
                    raise ValueError(
                        f"Failed to parse closing balance from CSV: '{line[1]}' - {e}"
                    ) from e
                return None
            if line[0] == "Alternate Account Number":
                # Skip alternate account number line
                return None
        elif len(line) < 8:
            return None

        if not line[0]:
            # Continuation of previous line
            if self.statement.lines:
                cur_idx = len(self.statement.lines) - 1
                self.statement.lines[cur_idx].memo = (
                    self.statement.lines[cur_idx].memo + " " + line[2]
                )
            return None

        try:
            line[5] = self.fix_amount(line[5])
        except (ValueError, IndexError) as e:
            amount_str = line[5] if len(line) > 5 else "N/A"
            raise ValueError(
                f"Failed to parse amount from CSV line: '{amount_str}' - {e}"
            ) from e

        # Clean and detect date format for this record
        # This handles mixed date formats in the same file
        if len(line) > 0 and line[0]:
            line[0] = self._clean_date_field(line[0])
            self.date_format = self._detect_date_format(line[0])

        try:
            statement_line = super(TmbCdParser, self).parse_record(line)
        except ValueError as e:
            memo = line[2] if len(line) > 2 else "N/A"
            raise ValueError(
                f"Failed to parse CSV record. "
                f"Date: '{line[0]}', Amount: '{line[5]}', Memo: '{memo}' - {e}"
            ) from e
        statement_line.trntype = "DEBIT" if statement_line.amount < 0 else "CREDIT"
        statement_line.id = generate_unique_transaction_id(
            statement_line, self.unique_id_set
        )

        return statement_line
