import sys
from pathlib import Path

from ..base_bot_test import BaseBotTest

sys.path.append(str(Path(Path(__file__).parent.parent.parent.parent / "src")))


class TestMaschbauBot(BaseBotTest):
    """Test class for the MaschBau Bot grouping tests together."""

    def setup_method(self):
        """Setup the bot for testing."""
        self.base_route = "pa"