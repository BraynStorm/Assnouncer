@echo off
call .venv\scripts\activate
title Assnouncer Stats
pushd assnouncer_stats
python -m flask run --no-reload --no-debugger --host 0.0.0.0 --port 8010
popd