import sys
import types

# Create a dummy matplotlib module that raises ImportError or passes
matplotlib = types.ModuleType('matplotlib')
sys.modules['matplotlib'] = matplotlib
