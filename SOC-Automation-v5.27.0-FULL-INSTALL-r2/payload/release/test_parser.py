from start_all_services import build_parser
p=build_parser()
a=p.parse_args(['--manual-mode','ACTIVE','--autofp-mode','SHADOW'])
assert a.manual_mode=='ACTIVE' and a.autofp_mode=='SHADOW'
a=p.parse_args(['--manual-mode','SHADOW','--autofp-mode','GLOBAL'])
assert a.manual_mode=='SHADOW' and a.autofp_mode=='GLOBAL'
print('PASS parser mode arguments')
