"""
Unit test for web server handler logic without requiring open network sockets.
"""

import unittest
from web.server import RouteOptimizerHandler
from cli import load_shipments


class TestWebHandlerLogic(unittest.TestCase):

    def test_shipments_summary(self):
        summary = RouteOptimizerHandler.get_shipments_summary()
        self.assertGreater(len(summary), 0)
        first = summary[0]
        self.assertIn("shipment_id", first)
        self.assertIn("corridor", first)
        self.assertIn("route_count", first)


if __name__ == "__main__":
    unittest.main()
