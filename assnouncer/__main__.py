from pathlib import Path

from assnouncer.assnouncer import Assnouncer

ass = Assnouncer()
ass.run(Path("token").read_text())
