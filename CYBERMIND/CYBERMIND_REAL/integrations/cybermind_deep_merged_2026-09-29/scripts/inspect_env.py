#!/usr/bin/env python
import sys,platform
try:
 import torch
except Exception: torch=None
print('python',platform.python_version()); print('platform',platform.platform())
if torch: print('torch',torch.__version__,'cuda',torch.cuda.is_available(),'devices',torch.cuda.device_count())
try:
 import torch_geometric; print('pyg',torch_geometric.__version__)
except Exception as e: print('pyg', 'NOT INSTALLED', e)
try:
 import pandas as pd; print('pandas',pd.__version__)
except Exception: pass
