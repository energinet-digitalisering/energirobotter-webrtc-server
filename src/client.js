let pc = null;
let ws = null;

function log(msg) {
    console.log(msg);
}

function createConnection() {
    const useStun = document.getElementById('use-stun').checked;
    const config = {
        sdpSemantics: 'unified-plan',
        iceServers: useStun ? [{ urls: 'stun:stun.l.google.com:19302' }] : [],
    };

    pc = new RTCPeerConnection(config);

    pc.onicecandidate = (event) => {
        if (event.candidate) {
            ws.send(JSON.stringify({ type: "candidate", candidate: event.candidate }));
        }
    };

    pc.ontrack = (event) => {
        if (event.track.kind === "video") {
            document.getElementById("video").srcObject = event.streams[0];
        } else if (event.track.kind === "audio") {
            document.getElementById("audio").srcObject = event.streams[0];
        }
    };

    ws = new WebSocket(`ws://${location.host}/ws`);

    ws.onmessage = async (event) => {
        const message = JSON.parse(event.data);
        log("Received: " + JSON.stringify(message));

        if (message.type === "offer") {
            await pc.setRemoteDescription(new RTCSessionDescription(message));
            const answer = await pc.createAnswer();
            await pc.setLocalDescription(answer);
            ws.send(JSON.stringify(pc.localDescription));
        } else if (message.type === "answer") {
            await pc.setRemoteDescription(new RTCSessionDescription(message));
        } else if (message.type === "candidate") {
            try {
                await pc.addIceCandidate(message.candidate);
            } catch (e) {
                console.error("Error adding candidate:", e);
            }
        }
    };

    ws.onopen = () => {
        log("WebSocket connected.");
    };
}

function start() {
    document.getElementById("start").style.display = "none";
    document.getElementById("stop").style.display = "inline-block";

    createConnection();

    const localMediaPromise = navigator.mediaDevices.getUserMedia({ video: true, audio: true });

    localMediaPromise.then((stream) => {
        for (const track of stream.getTracks()) {
            pc.addTrack(track, stream);
        }

        document.getElementById("video").srcObject = stream;

        return pc.createOffer();
    }).then((offer) => {
        return pc.setLocalDescription(offer);
    }).then(() => {
        ws.send(JSON.stringify(pc.localDescription));
    }).catch((error) => {
        alert("Error: " + error);
    });
}

function stop() {
    document.getElementById("stop").style.display = "none";

    if (pc) {
        pc.close();
    }

    if (ws) {
        ws.close();
    }

    document.getElementById("start").style.display = "inline-block";
}
