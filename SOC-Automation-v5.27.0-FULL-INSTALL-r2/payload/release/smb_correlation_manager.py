#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from smb_correlation import correlate
p=argparse.ArgumentParser();p.add_argument("--alert",type=Path,required=True);p.add_argument("--events",type=Path,required=True);a=p.parse_args();alert=json.loads(a.alert.read_text());events=json.loads(a.events.read_text());events=events.get("hits",{}).get("hits",[]) if isinstance(events,dict) else events;print(json.dumps(correlate(alert,events),indent=2))
