from smb_correlation import correlate
a={"kibana.alert.rule.name":"Rare SMB Connection to the Internet","host":{"id":"h"},"process":{"pid":4,"entity_id":"p"},"destination":{"ip":"104.26.11.44","port":445}}
e={"host":{"id":"h"},"process":{"entity_id":"p"},"destination":{"ip":"104.26.11.44","port":445},"event":{"action":["connection_attempted"],"outcome":"unknown"}}
assert correlate(a,[e])["assessment"]=="ATTEMPT_ONLY"
e["event"]={"action":["connection_established"],"outcome":"success"};assert correlate(a,[e])["assessment"]=="SUCCESSFUL"
e["network"]={"bytes":100};assert correlate(a,[e])["assessment"]=="SUCCESSFUL"
assert correlate(a,[])["assessment"]=="UNKNOWN_AFTER_CORRELATION"
print("PASS test_smb_correlation")
