import asyncio
import logging
import os
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from aiortc import (
    MediaStreamTrack,
    RTCPeerConnection,
    RTCSessionDescription,
    RTCIceCandidate,
)
from aiortc.contrib.media import MediaRelay
from contextlib import asynccontextmanager
import av
import sys

# Configure logging
logger = logging.getLogger("peerConnection")
logger.setLevel(logging.DEBUG)

stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
stderr_handler.setFormatter(formatter)

logger.addHandler(stderr_handler)

# Configure aiortc
peerConnections = dict()
relay = MediaRelay()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI starting...")
    try:
        yield
    finally:
        # Cleanup peer connections on shutdown
        logger.info("Shutting down, cleaning up peer connections...")
        coros = [peerConnection.close() for peerConnection in peerConnections.values()]
        await asyncio.gather(*coros)
        peerConnections.clear()


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


# Custom Audio Stream Track
class Audio(MediaStreamTrack):
    """
    A custom audio track that can forward and process audio frames.
    """

    kind = "audio"

    def __init__(self, source_track):
        super().__init__()
        self.source_track = source_track

    async def recv(self):

        # Receive the incoming audio frame
        frame = await self.source_track.recv()

        self.process_audio_frame(frame)

        return frame

    def process_audio_frame(self, frame):
        """
        Process the audio frame.
        """
        samples = frame.to_ndarray()
        logger.debug(f"Processing audio frame: {frame.pts}, {frame.sample_rate} Hz")


# WebRTC signaling handler
@app.post("/webrtc/offer")
async def offer(request: Request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    logger.debug(f"Received offer SDP: {offer.sdp}")

    peerConnection = RTCPeerConnection()
    peerConnectionId = "PeerConnection(%s)" % uuid.uuid4()
    peerConnections[peerConnectionId] = peerConnection

    def logInfo(msg, *args):
        logger.info(peerConnectionId + ": " + msg, *args)

    logInfo(f"Created for {request.client.host}")

    @peerConnection.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        logInfo(f"ICE connection state: {peerConnection.iceConnectionState}")

    @peerConnection.on("connectionstatechange")
    async def on_connectionstatechange():
        logInfo(f"Connection state: {peerConnection.connectionState}")
        if peerConnection.connectionState == "failed":
            await peerConnection.close()
            peerConnections.pop(peerConnectionId)

    @peerConnection.on("track")
    def on_track(track):
        logInfo(f"TrackID: {track.id} {track.kind} Track received")

        if track.kind == "audio":
            processedAudio = Audio(source_track=relay.subscribe(track))
            peerConnection.addTrack(processedAudio)

        @track.on("ended")
        async def on_ended():
            logInfo(f"TrackID: {track.id} {track.kind} Track ended")
            await peerConnection.close()
            peerConnections.pop(peerConnectionId)

    # Handle the WebRTC offer and create an answer
    await peerConnection.setRemoteDescription(offer)
    answer = await peerConnection.createAnswer()
    await peerConnection.setLocalDescription(answer)

    return JSONResponse(
        content={
            "sdp": peerConnection.localDescription.sdp,
            "type": peerConnection.localDescription.type,
            "peerConnectionId": peerConnectionId,
        }
    )


import asyncio
import logging
import os
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from aiortc import (
    MediaStreamTrack,
    RTCPeerConnection,
    RTCSessionDescription,
    RTCIceCandidate,
)
from aiortc.contrib.media import MediaRelay
from contextlib import asynccontextmanager
import av

# Configure logging
logger = logging.getLogger("peerConnection")
peerConnections = dict()
relay = MediaRelay()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Shutting down, cleaning up peer connections...")
    try:
        yield
    finally:
        # Cleanup peer connections on shutdown
        logger.info("Shutting down, cleaning up peer connections...")
        coros = [peerConnection.close() for peerConnection in peerConnections.values()]
        await asyncio.gather(*coros)
        peerConnections.clear()


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


# Custom Audio Stream Track
class Audio(MediaStreamTrack):
    """
    A custom audio track that can forward and process audio frames.
    """

    kind = "audio"

    def __init__(self, source_track):
        super().__init__()
        self.source_track = source_track

    async def recv(self):

        # Receive the incoming audio frame
        frame = await self.source_track.recv()

        self.process_audio_frame(frame)

        return frame

    def process_audio_frame(self, frame):
        """
        Process the audio frame.
        """
        samples = frame.to_ndarray()
        logger.debug(f"Processing audio frame: {frame.pts}, {frame.sample_rate} Hz")


# WebRTC signaling handler
@app.post("/webrtc/offer")
async def offer(request: Request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    peerConnection = RTCPeerConnection()
    peerConnectionId = "PeerConnection(%s)" % uuid.uuid4()
    peerConnections[peerConnectionId] = peerConnection

    def logInfo(msg, *args):
        logger.info(peerConnectionId + ": " + msg, *args)

    logInfo(f"Created for {request.client.host}")

    @peerConnection.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        logInfo(f"ICE connection state: {peerConnection.iceConnectionState}")

    @peerConnection.on("connectionstatechange")
    async def on_connectionstatechange():
        logInfo(f"Connection state: {peerConnection.connectionState}")
        if peerConnection.connectionState == "failed":
            await peerConnection.close()
            peerConnections.pop(peerConnectionId)

    @peerConnection.on("track")
    def on_track(track):
        logInfo(f"TrackID: {track.id} {track.kind} Track received")

        if track.kind == "audio":
            processedAudio = Audio(source_track=relay.subscribe(track))
            peerConnection.addTrack(processedAudio)

        @track.on("ended")
        async def on_ended():
            logInfo(f"TrackID: {track.id} {track.kind} Track ended")
            await peerConnection.close()
            peerConnections.pop(peerConnectionId)

    # Handle the WebRTC offer and create an answer
    await peerConnection.setRemoteDescription(offer)
    answer = await peerConnection.createAnswer()
    logger.info(f"Created answer: {answer.sdp}") 
    await peerConnection.setLocalDescription(answer)

    return JSONResponse(
        content={
            "answer": peerConnection.localDescription.sdp,
            "type": peerConnection.localDescription.type,
            "peerConnectionId": peerConnectionId,
        }
    )


# ICE candidate handler
@app.post("/webrtc/ice-candidate")
async def add_ice_candidate(request: Request):
    logger.info("Adding ICE candidate")
    data = await request.json()
    peerConnectionId = data.get("peerConnectionId")
    candidate = data.get("candidate")
    sdpMid = data.get("sdpMid")
    sdpMLineIndex = data.get("sdpMLineIndex")

    peerConnection = peerConnections.get(peerConnectionId)
    if not peerConnection:
        return {"status": "failure", "message": "Peer connection not found"}
    if candidate and sdpMid is not None and sdpMLineIndex is not None:
        ice_candidate = RTCIceCandidate(
            candidate=candidate, sdpMid=sdpMid, sdpMLineIndex=sdpMLineIndex
        )
        await peerConnection.addIceCandidate(ice_candidate)
        logger.info(f"ICE candidate added: {candidate}")
        return {"status": "success", "answer": peerConnection.localDescription.sdp}
    return {
        "status": "failure",
        "message": "Invalid candidate data",
    }


# ICE candidate handler
@app.post("/webrtc/ice-candidate")
async def add_ice_candidate(request: Request):
    logger.info("Adding ICE candidate")
    data = await request.json()
    peerConnectionId = data.get("peerConnectionId")
    candidate = data.get("candidate")
    sdpMid = data.get("sdpMid")
    sdpMLineIndex = data.get("sdpMLineIndex")

    peerConnection = peerConnections.get(peerConnectionId)
    if not peerConnection:
        return {"status": "failure", "message": "Peer connection not found"}
    if candidate and sdpMid is not None and sdpMLineIndex is not None:
        ice_candidate = RTCIceCandidate(
            candidate=candidate, sdpMid=sdpMid, sdpMLineIndex=sdpMLineIndex
        )
        await peerConnection.addIceCandidate(ice_candidate)
        logger.info(f"ICE candidate added: {candidate}")
        return {
            "status": "success",
            "answer": peerConnection.localDescription.sdp,
            "peerConnectionId": peerConnectionId,
        }
    return {
        "status": "failure",
        "message": "Invalid candidate data",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
