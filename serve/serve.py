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
    RTCDataChannel,
)
from aiortc.contrib.media import MediaRelay
from contextlib import asynccontextmanager
import av
import sys
import numpy as np
import time
import tempfile
from lib import groqWhisper, applyVAD

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
dataChannel = None

BUFFER_DURATION = 1.0


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


def sendToFrontend(text: str):
    if dataChannel and dataChannel.readyState == "open":
        dataChannel.send(text)
        logger.info(f"Sent text to frontend: {text}")
    else:
        logger.warning("Data channel is not open, text not sent")


# Custom Audio Stream Track
class Audio(MediaStreamTrack):
    """
    A custom audio track that can forward and process audio frames.
    """

    kind = "audio"

    def __init__(self, sourceTrack: MediaStreamTrack):
        super().__init__()
        self.sourceTrack = sourceTrack
        self.sampleRate = None
        self.bufferSize = int(48000 * BUFFER_DURATION)
        self.buffer = []
        self.last_frame_time = time.time()
        self.threshhold = 0.5

    async def recv(self):

        # Receive the incoming audio frame
        frame = await self.sourceTrack.recv()

        if self.sampleRate == None:
            self.sampleRate = frame.sample_rate
            self.bufferSize = int(self.sampleRate * BUFFER_DURATION)

        self.buffer.append(frame)

        total_samples = sum([frame.to_ndarray().shape[1] for frame in self.buffer])

        if total_samples >= self.sampleRate * BUFFER_DURATION:
            audio_data = self.processBuffer()
            text = self.processAudioData(audio_data)

            if text:
                sendToFrontend(text)

            self.buffer = []

        return frame

    def processBuffer(self) -> np.ndarray:
        """
        Process the buffered frames into a single chunk of audio.
        """
        frames_ndarray = np.concatenate(
            [frame.to_ndarray() for frame in self.buffer]
        ).flatten()
        return frames_ndarray

    def processAudioData(self, audioData: np.ndarray):
        """
        Process the audio frame.
        """

        timestamps = applyVAD(audioData=audioData, sampleRate=self.sampleRate)

        if timestamps:
            # logger.info("Speech detected in the chunk.")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tempFile:
                tempFilePath = tempFile.name
                outputContainer = av.open(tempFilePath, "w")

                stream = outputContainer.add_stream("pcm_s16le", rate=self.sampleRate)
                stream.layout = "stereo"

                # Write audio frames to the file
                for frame in self.buffer:
                    frame_data = frame.to_ndarray()
                    # If mono, duplicate the data to make it stereo
                    if frame_data.ndim == 1:
                        frame_data = np.column_stack((frame_data, frame_data))
                    packet = av.Packet(frame_data.tobytes())
                    outputContainer.mux(packet)

                outputContainer.close()

            # logger.info(f"Saved audio data to temporary file: {tempFilePath}")

            try:
                logger.debug("Sending audio to whisper")
                transcribed_text = groqWhisper(filename=tempFilePath)
            except Exception as e:
                logger.error(f"Error during transcription: {e}")
                transcribed_text = None
            finally:
                os.remove(tempFilePath)
            return transcribed_text
        else:
            return None


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

    @peerConnection.on("datachannel")
    async def on_datachannel(channel: RTCDataChannel):
        global dataChannel
        dataChannel = channel
        logInfo(f"Data channel created: {channel.label}")

        # Handle incoming messages from the frontend
        @channel.on("message")
        async def on_message(message):
            logInfo(f"Received message from frontend: {message}")
            # Example: Echo the message back
            channel.send(f"Echo: {message}")

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
            processedAudio = Audio(sourceTrack=relay.subscribe(track))
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
