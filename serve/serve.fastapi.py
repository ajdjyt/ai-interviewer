from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
from aiortc.mediastreams import MediaStreamError
import uuid


# from aiortc.contrib.media import MediaPlayer, MediaRelay

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# relay = MediaRelay()
peerConnections = {}

@app.post("/api/webrtc/offer")
async def webrtc_offer(request: Request):
    data = await request.json()
    offer = data.get("sdp")

    pc_id = str(uuid.uuid4())
    peerConnection = RTCPeerConnection()
    peerConnections[pc_id] = peerConnection

    
    # Set the remote SDP (offer)
    await peerConnection.setRemoteDescription(
        RTCSessionDescription(sdp=offer, type="offer")
    )

    # Create an SDP answer
    answer = await peerConnection.createAnswer()
    await peerConnection.setLocalDescription(answer)
    
    # Add media processing logic here if needed
    @peerConnection.on("track")
    async def on_track(track):
        print(f"Received track: {track.kind}, ID: {track.id}")
        if track.kind == "audio":
            track_ended = False
            print("Audio track received!")
            try:
                while not track_ended:
                    frame = await track.recv()
                    if frame:
                        print(f"Received frame: {frame}")
                        print(f"Frame samples: {frame.samples}")
                        print(f"Sample rate: {frame.rate}")
                    else:
                        break
                # player = MediaPlayer(track)
                # relay.subscribe(player)
            except MediaStreamError as e:
                track_ended = True
                print(f"Track ended, track:{track.kind}:{track.id}")

            @track.on("ended")
            def on_ended():
                print(f"Track {track.id}:{track.kind} ended, cleaning up resources.")
                track_ended = True

        else:
            print(f"Unhandled track kind: {track.kind}")
        
    @peerConnection.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        print(f"ICE connection state: {peerConnection.iceConnectionState}")
        
    @app.post("/api/webrtc/ice-candidate")
    async def add_ice_candidate(request: Request):
        data = await request.json()
        candidate = data.get("candidate")
        sdpMid = data.get("sdpMid")
        sdpMLineIndex = data.get("sdpMLineIndex")

        if candidate and sdpMid is not None and sdpMLineIndex is not None:
            # ice_candidate = {
            #     "candidate": candidate,
            #     "sdpMid": sdpMid,
            #     "sdpMLineIndex": sdpMLineIndex,
            # }
            ice_candidate = RTCIceCandidate(
                candidate=candidate, sdpMid=sdpMid, sdpMLineIndex=sdpMLineIndex
            )
            await peerConnection.addIceCandidate(ice_candidate)

    return {"answer": peerConnection.localDescription.sdp}





if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
