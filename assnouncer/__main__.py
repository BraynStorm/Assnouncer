import argparse
from pathlib import Path

from assnouncer import config
from assnouncer.assnouncer import Assnouncer

#
# Parse
#
parser = argparse.ArgumentParser(
    prog="assnouncer",
    description="A(ss)nnouncer Discord Bot",
)
parser.add_argument(
    "guild",
    type=int,
    help="The guild (server) ID of the server to connect to.",
    default=config.GUILD_ID,
)
args = parser.parse_args()

#
# Configure
#
config.GUILD_ID = int(args.guild)

#
# Run
#
ass = Assnouncer()
ass.run(Path("token").read_text())
