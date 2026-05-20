import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import importlib
m = importlib.import_module('backend.main')
app = m.app
print([r.path for r in app.routes])
for r in app.routes:
    print(r.path)
