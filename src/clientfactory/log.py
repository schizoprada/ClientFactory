# ~/ClientFactory/src/clientfactory/log.py
import os
from loguru import logger as log


DEBUGVAR = os.getenv("CLIENTFACTORYDEBUG", "0")
DEBUGON = False
try:
    DEBUGON = bool(int(DEBUGVAR))
except:
    pass

if not DEBUGON:
    log.remove()

__all__ = ['log']
