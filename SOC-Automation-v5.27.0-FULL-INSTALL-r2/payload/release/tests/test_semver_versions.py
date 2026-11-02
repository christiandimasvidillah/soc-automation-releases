from local_release_manager import safe_version, version_tuple, ReleaseError
assert safe_version('4.11.0-rc1') == '4.11.0-rc1'
assert safe_version('v4.11.0-rc.2+termux') == '4.11.0-rc.2+termux'
assert version_tuple('4.11.0-rc1') > version_tuple('4.10.2')
assert version_tuple('4.11.0') > version_tuple('4.11.0-rc1')
assert version_tuple('4.11.0-rc.10') > version_tuple('4.11.0-rc.2')
try: safe_version('../bad')
except ReleaseError: pass
else: raise AssertionError('unsafe version accepted')
print('Semantic version parser tests: OK')
