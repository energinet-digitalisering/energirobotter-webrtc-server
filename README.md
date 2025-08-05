# Energirobotter WebRTC Server

WebRTC Signalling server for the project Energirobotter. Used for connecting the camera stream of a robot and operator for teleoperation.

Its purpose is to run on a publically reachable server with an SSL certificate.

## System Setup

- Ubuntu Server 24.04
- NGINX

### Dependencies

```
sudo apt install python3-pip libglib2.0-dev libsm-dev libxrender-dev libxext-dev -y
```

Create a virtual environment for Python packages:
```bash
# Install if missing
sudo apt install python3-venv

# Create a virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install requirements into this venv
pip install -r requirements.txt
```

## Server Setup

Add you public ssh key to `~/.ssh/authorized_keys` on the server.

### Clone The Reopsitory to the Server

Don't add you git credentials directly on the server. Instead, mount its user directory to you machine, and run your git commands there. 

To let other users (i.e., root or you) access the mount with permissions similar to the remote one, uncomment the line `user_allow_other` in the `/etc/fuse.conf` file. 

Create a directory and set permissions:
```
sudo mkdir /mnt/server/
sudo chmod 777 /mnt/server/
```

Mount the server to that directory (only this line has to be re-run when mounting in the future):
```
sshfs -o allow_other,IdentityFile=~/.ssh/id_ed25519.pub admin@<server_ip>:/home/admin /mnt/server 
```

Got to the folder, and clone the directory:
```
cd /mnt/server
git clone git@github.com:energinet-digitalisering/energirobotter-webrtc-server.git
```



### Start Signaling Server on Startup

Run:

```bash
sudo nano /etc/systemd/system/webrtc-signaling.service
```

Paste this (adjust paths if needed):

```ini
[Unit]
Description=WebRTC Signaling Server
After=network.target

[Service]
User=admin
WorkingDirectory=/home/admin/energirobotter-webrtc-server
ExecStart=/home/admin/energirobotter-webrtc-server/venv/bin/python /home/admin/energirobotter-webrtc-server/src/webrtc_signalling_server.py
Restart=always
RestartSec=3

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Save and exit.

Start and enable the service:

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable webrtc-signaling.service
sudo systemctl start webrtc-signaling.service
```

Check the status:

```bash
systemctl status webrtc-signaling.service
```
