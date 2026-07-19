import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# so tests can `import wobbly` and `import run_blind / build_receipts`
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
