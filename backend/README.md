# Backend Set Up Instructions

## VM Access Setup (One-Time Per Developer)
### generate an SSH key on your laptop:
<ssh-keygen -t ed25519 -C "your-name-fieldsight" -f ~/.ssh/fieldsight_key>
share your public key (~/.ssh/fieldsight_key.pub) with the VM admin
VM admin adds your public key to:
/home/opc/.ssh/authorized_keys
connect to VM:
<ssh -i ~/.ssh/fieldsight_key opc@64.181.240.74>

### ssh into the VM
go to the project root:
<cd /opt/fieldsight>

## pull latest backend code:
<git checkout main>
<git pull --ff-only origin main>

## install Python dependencies:
</opt/fieldsight/.venv/bin/pip install -r /opt/fieldsight/requirements.txt>

## configure backend environment variables in:
/etc/fieldsight.env

## initialize database tables by running schema.sql once when setting up a new database

## run syntax checks before restart:
</opt/fieldsight/.venv/bin/python -m py_compile /opt/fieldsight/backend/app/main.py /opt/fieldsight/backend/app/routes/*.py /opt/fieldsight/backend/app/services/*.py>

## restart backend:
<sudo systemctl restart fieldsight.service>
verify backend status:
<sudo systemctl status fieldsight.service --no-pager -l>
<curl -i http://127.0.0.1:8000/health>
<curl -i https://api.fieldsightproject.com/health>

## MQTT Broker (Mosquitto)
### start broker:
<sudo systemctl start mosquitto>

### enable broker on reboot:
<sudo systemctl enable mosquitto>

### verify broker:
<sudo systemctl status mosquitto --no-pager>
<sudo journalctl -u mosquitto -n 80 --no-pager>
