let socket;
let peerConnection;
let dc = null;

function createConnection() {
    const wsUrl = 'wss://' + window.location.host + '/ws';
    console.log('Connecting to WebSocket:', wsUrl);
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        console.log('WebSocket connected');
    };

    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    socket.onclose = () => {
        console.log('WebSocket closed');
    };

    socket.onmessage = async (event) => {
        const message = JSON.parse(event.data);
        console.log('Received message:', message);

        if (message.sdp) {
            try {
                await peerConnection.setRemoteDescription(new RTCSessionDescription(message));
                if (message.type === 'offer') {
                    const answer = await peerConnection.createAnswer();
                    await peerConnection.setLocalDescription(answer);
                    console.log('Sending SDP answer');
                    socket.send(JSON.stringify(peerConnection.localDescription));
                }
            } catch (e) {
                console.error('SDP error:', e);
            }
        } else if (message.candidate) {
            try {
                await peerConnection.addIceCandidate(new RTCIceCandidate(message.candidate));
            } catch (e) {
                console.error('ICE candidate error:', e);
            }
        }
    };
}

function start() {
    const useStun = document.getElementById('use-stun').checked;
    const config = useStun ? { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] } : {};
    console.log('Starting WebRTC with config:', config);

    peerConnection = new RTCPeerConnection(config);
    const videoElement = document.getElementById('video');

    peerConnection.onicecandidate = (event) => {
        if (event.candidate) {
            console.log('Sending ICE candidate:', event.candidate);
            socket.send(JSON.stringify({ candidate: event.candidate }));
        }
    };

    peerConnection.ontrack = (event) => {
        console.log('Received track:', event.track);
        if (event.streams && event.streams[0]) {
            videoElement.srcObject = event.streams[0];
            videoElement.play().catch(e => console.error('Video play error:', e));
        }
    };

    peerConnection.ondatachannel = (event) => {
        dc = event.channel;
        dc.onmessage = (e) => console.log('Data channel message:', e.data);
    };

    createConnection();

    document.getElementById('start').style.display = 'none';
    document.getElementById('stop').style.display = '';
}

function stop() {
    if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
    }
    if (socket) {
        socket.close();
        socket = null;
    }
    document.getElementById('video').srcObject = null;
    document.getElementById('start').style.display = '';
    document.getElementById('stop').style.display = 'none';
}
