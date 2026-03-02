"""Unit tests for TMB Congo ofxstatement plugin"""

import os
from decimal import Decimal as D
from io import StringIO

import pytest

from ofxstatement_cd_tmb.cd_tmb import TmbCdPlugin, TmbCdParser


def get_sample_file_path(filename):
    """Get path to sample file in examples directory"""
    current_dir = os.path.dirname(__file__)
    return os.path.join(
        current_dir, "..", "src", "ofxstatement_cd_tmb", "examples", filename
    )


class TestTmbCdPlugin:
    """Test TMB Congo plugin class"""

    def test_plugin_instantiation(self):
        """Test plugin can be instantiated"""
        plugin = TmbCdPlugin(None, {})
        assert plugin is not None

    def test_get_parser_csv(self):
        """Test plugin returns a parser for CSV files"""
        plugin = TmbCdPlugin(None, {})
        sample_file = get_sample_file_path("sample.csv")
        parser = plugin.get_parser(sample_file)
        assert isinstance(parser, TmbCdParser)


class TestTmbCdParserCSV:
    """Test TMB Congo parser with CSV format"""

    def test_parse_csv_format(self):
        """Test parsing a sample CSV export file"""
        plugin = TmbCdPlugin(None, {})
        sample_file = get_sample_file_path("sample.csv")
        parser = plugin.get_parser(sample_file)
        statement = parser.parse()

        # Check basic statement properties
        assert statement is not None
        assert statement.currency == "USD"
        assert statement.start_balance == D("51348.89")
        assert statement.end_balance == D("51383.09")

        # Check we parsed transactions
        assert len(statement.lines) == 4

        # Check first transaction
        first_line = statement.lines[0]
        assert first_line.amount == D("-0.80")  # Dr means debit (negative)
        assert first_line.memo == "TVA COLLECTEE"
        assert first_line.trntype in ("DEBIT", "CREDIT")

    def test_file_type_detection_csv(self):
        """Test that CSV format is correctly detected"""
        plugin = TmbCdPlugin(None, {})
        sample_file = get_sample_file_path("sample.csv")
        parser = plugin.get_parser(sample_file)
        parser._set_file_type()
        assert parser.filetype == "csv"

    def test_fix_amount_debit(self):
        """Test amount conversion for debit entries"""
        plugin = TmbCdPlugin(None, {})
        sample_file = get_sample_file_path("sample.csv")
        parser = plugin.get_parser(sample_file)

        result = parser.fix_amount("100.50Dr")
        assert result == "-100.50"

    def test_fix_amount_credit(self):
        """Test amount conversion for credit entries"""
        plugin = TmbCdPlugin(None, {})
        sample_file = get_sample_file_path("sample.csv")
        parser = plugin.get_parser(sample_file)

        result = parser.fix_amount("200.75Cr")
        assert result == "200.75"


class TestTmbCdParserPDF:
    """Test TMB Congo parser with PDF export format"""

    def test_parse_pdf_format(self):
        """Test parsing a sample PDF export file"""
        plugin = TmbCdPlugin(None, {})
        sample_file = get_sample_file_path("231231.csv")
        parser = plugin.get_parser(sample_file)
        statement = parser.parse()

        # Check basic statement properties
        assert statement is not None
        assert statement.currency == "USD"
        assert statement.end_balance is not None

        # Check we parsed transactions
        assert len(statement.lines) > 0

        # Check transactions have proper fields
        for line in statement.lines:
            assert line.amount is not None
            assert line.trntype in ("DEBIT", "CREDIT")

    def test_file_type_detection_pdf(self):
        """Test that PDF export format is correctly detected"""
        plugin = TmbCdPlugin(None, {})
        sample_file = get_sample_file_path("231231.csv")
        parser = plugin.get_parser(sample_file)
        parser._set_file_type()
        assert parser.filetype == "pdf"

    def test_pdf_mappings(self):
        """Test that PDF format uses correct field mappings"""
        plugin = TmbCdPlugin(None, {})
        sample_file = get_sample_file_path("231231.csv")
        parser = plugin.get_parser(sample_file)
        parser._set_file_type()

        # PDF format should have these mappings
        assert parser.mappings["date"] == 2
        assert parser.mappings["refnum"] == 0
        assert parser.mappings["memo"] == 1
        assert parser.mappings["amount"] == 4
        assert parser.mappings["id"] == 0


class TestTmbCdParserEdgeCases:
    """Test edge cases and error handling"""

    def test_multiline_memo_csv(self):
        """Test handling of multi-line memos in CSV format"""
        # This would require creating a specific test CSV with multi-line memos
        pass

    def test_balance_calculation(self):
        """Test that start balance is correctly calculated"""
        plugin = TmbCdPlugin(None, {})
        sample_file = get_sample_file_path("sample.csv")
        parser = plugin.get_parser(sample_file)
        statement = parser.parse()

        # Start balance + sum of transactions should equal end balance
        total_amount = sum(line.amount for line in statement.lines)
        calculated_end = statement.start_balance + total_amount
        assert abs(calculated_end - statement.end_balance) < D("0.01")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
