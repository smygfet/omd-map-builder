# carry the user's sketch and map settings (rift, look) into a freshly generated map
import json, sys
a = json.load(open(sys.argv[1])); u = json.load(open(sys.argv[2]))
a['sketch'] = u.get('sketch', [])
for k in ('rift', 'env', 'fill', 'fillPits', 'styles', 'rules', 'uid'):
    if k in u: a[k] = u[k]
json.dump(a, open(sys.argv[3], 'w')); print('merged', a['rev'], a['rift'], len(a['sketch']))
