import unittest

from dashboard.log_parser import parse_json_log_line


class LogParserTest(unittest.TestCase):
    def test_parse_json_log_line_extracts_group_rows(self) -> None:
        rows = parse_json_log_line(
            '{"GENERAL":{"TIMESTAMP":100},"INTARIAN_PEPPER_ROOT":{"WALL_MID":9999.5}}',
            source_file="sample.log",
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["timestamp"], 100)
        self.assertEqual(rows[0]["product"], "INTARIAN_PEPPER_ROOT")
        self.assertEqual(rows[0]["key"], "WALL_MID")


if __name__ == "__main__":
    unittest.main()
