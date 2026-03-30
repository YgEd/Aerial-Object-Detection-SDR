
# Instructions on setting up the project

Set-up the Docker container for the Eclipse Mosquitto:

## Create the directory for Eclipse Mosquitto:
```bash
mkdir -p mosquitto/{config,data,log}
cd mosquitto
```

## Create the config file (Linux/macOS)
```bash
touch config/mosquitto.conf
```

### Add basic configuration to config/mosquitto.conf using a text editor. Example content for development/testing (allows anonymous connections)
```bash
echo "persistence true" >> config/mosquitto.conf
echo "persistence_location /mosquitto/data/" >> config/mosquitto.conf
echo "log_dest file /mosquitto/log/mosquitto.log" >> config/mosquitto.conf
echo "listener 1883" >> config/mosquitto.conf
echo "allow_anonymous true" >> config/mosquitto.conf
```

### Add WebSockets listener
```bash
echo "listener 9001" >> config/mosquitto.conf
echo "protocol websockets" >> config/mosquitto.conf
touch docker-compose.yml
nano docker-compose.yml 
sudo docker compose up -d
```

## Add Docker's official GPG key:
```bash
sudo apt update
sudo apt install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

## Add the repository to Apt sources:
```bash
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
```

## Start Docker container
```bash
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl start docker
```

## Install UV for python
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv --version
```

## Start the Python venv
```bash
uv venv --python 3.12 --seed
source .venv/bin/activate
python --version
```

## Install the required python packages
```bash
pip install opencv-python ultralytics paho-mqtt numpy
python caliberate.py 
python sender.py
python receiver.py
```
