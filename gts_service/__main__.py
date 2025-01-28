import subprocess
from time import sleep


def main():
    try:
        process = subprocess.Popen(
            args="gunicorn --workers 1 --threads 8 gts_service.wsgi", shell=True
        )
        while process.poll() is None:
            pass
    except KeyboardInterrupt:
        sleep(1)  # just for nicer shutdown in console


if __name__ == "__main__":
    main()
