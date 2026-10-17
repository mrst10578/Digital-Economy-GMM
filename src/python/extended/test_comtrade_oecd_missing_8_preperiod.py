"""Offline safety and schema tests for Phase-2 multi-source Comtrade collector."""
import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).with_name("pilot_comtrade_oecd_missing_8_all_partners_preperiod.py")
SPEC = importlib.util.spec_from_file_location("phase2_comtrade_preperiod", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def row(partner, value, year=2005, hs="8471", reporter=417):
    return {"reporterCode": reporter, "period": year, "flowCode": "M",
            "cmdCode": hs, "partnerCode": partner, "primaryValue": value}


class Guardrails(unittest.TestCase):
    def setUp(self):
        self.origin = {0: "", 156: "CHN", 40: "AUT"}

    def check(self, rows):
        return MOD.inspect(rows, 417, "KGZ", 2005, "8471", self.origin)

    def test_valid_keeps_world_separate(self):
        status, rows, world, subset = self.check([row(0, 120), row(156, 45), row(40, 12)])
        self.assertEqual(status, "VALID_PREVIEW")
        self.assertEqual(len(rows), 3)
        self.assertEqual(world, 120.0)
        self.assertEqual(subset, 57.0)
        self.assertTrue(rows[0]["is_world_aggregate"])

    def test_missing_is_not_zero(self):
        status, records, world, subset = self.check([])
        self.assertEqual(status, "EMPTY_UNREPORTED_NOT_ZERO")
        self.assertEqual(records, [])
        self.assertIsNone(world)

    def test_missing_world_rejects_slice(self):
        self.assertEqual(self.check([row(156, 45)])[0], "WORLD_AGGREGATE_UNAVAILABLE")

    def test_duplicate_partner_rejects_slice(self):
        self.assertEqual(self.check([row(0, 120), row(156, 45), row(156, 46)])[0],
                         "BAD_OR_DUPLICATE_VALUE")

    def test_bad_metadata_rejects_slice(self):
        self.assertEqual(self.check([row(0, 120), row(156, 45, year=2006)])[0],
                         "BAD_METADATA")

    def test_bad_value_rejects_slice(self):
        self.assertEqual(self.check([row(0, 120), row(156, -1)])[0],
                         "BAD_OR_DUPLICATE_VALUE")

    def test_api_failure_is_not_missing_trade(self):
        self.assertEqual(self.check(None)[0], "API_ERROR")

    def test_truncation_is_not_accepted(self):
        huge = [row(0, 1)] * MOD.LIMIT
        self.assertEqual(self.check(huge)[0], "CAPPED_NOT_USABLE")


if __name__ == "__main__":
    unittest.main()
