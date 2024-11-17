<script lang="ts">
	let localStream: MediaStream;
	let peerConnection: RTCPeerConnection;

	let connected = false;

	const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;

	// Only run this code in the browser
	if (typeof window !== 'undefined') {
		peerConnection = new RTCPeerConnection();

		peerConnection.onicecandidate = (event) => {
			if (event.candidate) {
				fetch(BACKEND_URL + '/api/webrtc/ice-candidate', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ candidate: event.candidate })
				});
			}
		};
	}

	async function toggleAudioStream(){
		if (connected){
			// Stop the audio stream and close the connection
			localStream.getTracks().forEach(track => {
				track.stop();
			});
			peerConnection.close();
			connected = false;
			console.log("Audio stream stopped.");
		} else {
			startAudioStream();
		}
	}
	// Function to start capturing audio and create an offer
	async function startAudioStream() {
		try {
			// Get the audio stream from the microphone
			localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
			console.log(localStream);
			if (localStream) {
				localStream.getTracks().forEach((track) => {
					console.log('Adding track to peer connection:', track.kind, track.id);
					peerConnection.addTrack(track, localStream);
				});
				// localStream.getTracks().forEach((track) => peerConnection.addTrack(track, localStream));
			}

			// Create an SDP offer
			const offer = await peerConnection.createOffer();
			await peerConnection.setLocalDescription(offer);

			// Send the offer to the backend (using FastAPI)
			const response = await fetch(BACKEND_URL + '/api/webrtc/offer', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ sdp: offer.sdp })
			});

			const { answer } = await response.json();
			await peerConnection.setRemoteDescription(
				new RTCSessionDescription({ type: 'answer', sdp: answer })
			);
			connected = true;
		} catch (error) {
			console.error('Error accessing microphone or creating offer:', error);
		}
	}
</script>

<div
	class="min-w-screen mx-auto flex min-h-screen flex-col items-center justify-center bg-black text-slate-100"
>
	<button
		on:click={toggleAudioStream}
		class="m-6 min-w-[10rem] rounded-[1rem] border border-indigo-700 px-[1.2em] py-[0.6em]"
	>
		{#if connected}
			Stop
		{:else}
			Start
		{/if}
	</button>
	<h1
		id="output"
		class="max-h-[8rem] min-h-[8rem] min-w-[12rem] max-w-[12rem] rounded-[1rem] px-[1.2em] py-[0.6em] text-center outline outline-indigo-800"
	>
		wowza
	</h1>
</div>
