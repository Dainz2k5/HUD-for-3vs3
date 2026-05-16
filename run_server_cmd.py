import subprocess
import sys
import os
import time
import traceback

ROOT = os.path.dirname(__file__)
APP_PY = os.path.join(ROOT, 'app.py')
LOG = os.path.join(ROOT, 'server_start.log')

def write_log(data: str):
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(data + "\n")
    except Exception:
        pass

if __name__ == '__main__':
    write_log('Launching app.py as background process')
    try:
        python = sys.executable or 'python'
        proc = subprocess.Popen([python, APP_PY], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        write_log(f'Launched pid={proc.pid}')
        # give it a moment and capture any immediate output
        time.sleep(1)
        try:
            out, err = proc.communicate(timeout=1)
            if out:
                write_log('STDOUT: ' + out.decode('utf-8', errors='replace'))
            if err:
                write_log('STDERR: ' + err.decode('utf-8', errors='replace'))
        except subprocess.TimeoutExpired:
            write_log('Server appears to be running (no immediate exit)')
    except Exception:
        write_log('Exception during launch:')
        write_log(traceback.format_exc())
