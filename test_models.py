import unittest
from models import MarketSignal

class TestMarketSignalModel(unittest.TestCase):
    def test_valid_signal(self):
        signal = MarketSignal(
            ticker="AAPL",
            company_name="Apple Inc.",
            signal_type="Tailwind",
            summary="Strong iPhone sales",
            impact_score=0.8,
            source_info={"url": "https://example.com", "title": "Apple Q3 Earnings"}
        )
        self.assertEqual(signal.ticker, "AAPL")
        self.assertEqual(signal.company_name, "Apple Inc.")
        self.assertEqual(signal.signal_type, "Tailwind")

    def test_invalid_signal_type(self):
        try:
            MarketSignal(
                ticker="AAPL",
                company_name="Apple Inc.",
                signal_type="Neutral", # Invalid Literal
                summary="Some news",
                impact_score=0.0,
                source_info={"url": "url", "title": "title"}
            )
            self.fail("Should have raised ValueError")
        except ValueError:
            pass

if __name__ == "__main__":
    unittest.main()
