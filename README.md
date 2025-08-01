# Energirobotter WebRTC Server

WebRTC Signalling server for the project Energirobotter. Used for connecting the camera stream of a robot and operator for teleoperation.

Its purpose is to run on a publically reachable server with an SSL certificate.

## System Setup

- Ubuntu Server 24.04
- NGINX

## Dependencies

```
sudo apt install python3-pip libglib2.0-dev libsm-dev libxrender-dev libxext-dev -y
pip install -r requirements.txt
```
