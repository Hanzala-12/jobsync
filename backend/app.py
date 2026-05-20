import os
import sys
import types


# When deploying backend/ as the project root on Vercel, modules import paths like
# "backend.main" and "backend.routers.*" would fail because no real "backend"
# package exists above this folder. Expose this folder as a synthetic package.
package_name = "backend"
package_root = os.path.dirname(__file__)
if package_name not in sys.modules:
    package = types.ModuleType(package_name)
    package.__path__ = [package_root]
    sys.modules[package_name] = package

from backend.main import app
