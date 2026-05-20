import importlib, sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
importlib.invalidate_caches()
m = importlib.import_module('backend.routers.profile')
print('module_loaded', m.__name__)
print('has_router', hasattr(m, 'router'))
print('router_prefix', getattr(m, 'router').prefix if hasattr(m,'router') else None)
print('router_routes', [r.path for r in getattr(m,'router').routes] if hasattr(m,'router') else None)
