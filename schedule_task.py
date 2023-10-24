from datetime import datetime, timedelta
import schedule
import time
from vericota import Vericota
import os
import sys


def main():
    start_time = datetime.now()

    dt = datetime.now()
    date = dt.strftime('%A')

    vericota = Vericota() 

    schedule.every().day.at('17:00').do(vericota.atualicao_variacao_cota)
    schedule.every().day.at('06:55').do(vericota.atualizacao_britech)

    while True:
        print('Compilando Vericota-Bot')
        time.sleep(1)
        os.system('cls')
        print('Compilando Vericota-Bot.')
        time.sleep(1)
        os.system('cls')
        print('Compilando Vericota-Bot..')
        time.sleep(1)
        os.system('cls')
        print('Compilando Vericota-Bot...')
        time.sleep(1)
        os.system('cls')
        
        if date != "Saturday" and date != "Sunday":
            schedule.run_pending()
        
        if time_to_restart(start_time):
            print("Reiniciando...")
            restart_script()
            

def restart_script():
    python = sys.executable
    os.execl(python, python, *sys.argv)


def time_to_restart(start_time):
    current_time = datetime.now()
    elapsed_time = current_time - start_time
    # Reiniciar a cada x horas (x*3600 segundos)
    if elapsed_time.total_seconds() >= 10800:
        return True
    return False


if __name__ == "__main__":
    main()
