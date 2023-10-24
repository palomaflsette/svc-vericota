from dotenv import load_dotenv
import os

load_dotenv()

USER_SQL_SINQIA = str(os.getenv('USER_SQL_SINQIA'))
PASS_SQL_SINQIA = str(os.getenv('PASS_SQL_SINQIA'))
USER_DB_ATIVA = str(os.getenv('USER_DB_ATIVA'))
PASS_DB_ATIVA = str(os.getenv('PASS_DB_ATIVA'))
DSN = str(os.getenv('DSN'))
SRV_SINQIA = str(os.getenv('SRV_SINQIA'))
PASS_CENTRAL_OP = str(os.getenv('PASS_CENTRAL_OP'))