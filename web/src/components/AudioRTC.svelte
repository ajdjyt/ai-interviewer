<script lang="ts">
	import { onMount } from 'svelte';

	let localStream: MediaStream;
	let peerConnection: RTCPeerConnection;
	let peerConnectionId: string;
	let connected = false;
	let errorMessage: string | undefined = '';
	let dataChannel: RTCDataChannel;
	let outputElement: HTMLHeadingElement;

	const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;
	onMount(() => {
		outputElement = document.getElementById('output') as HTMLHeadingElement;
	});

	async function setupWebRTC() {
		peerConnection = new RTCPeerConnection();

		peerConnection.onicecandidate = (event) => {
			if (event.candidate && peerConnectionId != '') {
				fetch(BACKEND_URL + '/webrtc/ice-candidate', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({
						candidate: event.candidate,
						sdpMid: event.candidate.sdpMid,
						sdpMLineIndex: event.candidate.sdpMLineIndex,
						peerConnectionId: peerConnectionId
					})
				});
			}
		};
		dataChannel = peerConnection.createDataChannel('textChannel');

		dataChannel.onopen = () => {
			console.log('Data channel is open and ready to send messages');
		};

		dataChannel.onclose = () => {
			console.log('Data channel is closed');
		};

		dataChannel.onmessage = (event) => {
			// console.log('Received message from backend:');
			if (outputElement) {
				outputElement.textContent = (event.data!='')?event.data:outputElement.textContent ;
			}
		};
		peerConnection.onconnectionstatechange = () => {
			if (
				peerConnection.connectionState === 'disconnected' ||
				peerConnection.connectionState === 'failed'
			) {
				// Close both the audio and data channels
				closeWebRTC();
			}
		};

		try {
			localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
			if (localStream) {
				localStream.getTracks().forEach((track) => {
					console.log('Adding track to peer connection:', track.kind, track.id);
					peerConnection.addTrack(track, localStream);
				});
			}
			const offer = await peerConnection.createOffer();
			await peerConnection.setLocalDescription(offer);
			const response = await fetch(BACKEND_URL + '/webrtc/offer', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					sdp: offer.sdp,
					type: offer.type
				})
			});

			const data = await response.json();
			if (data.status == 'failure') {
				errorMessage = 'Failed to create a valid WebRTC connection. Please try again.';
				console.error('Failed to get a valid response for offer.');
				connected = false;
				return;
			}

			console.log('Got a successfull response');
			const answer = data.answer;
			peerConnectionId = data.peerConnectionId;

			console.log('peerConnectionID:', peerConnectionId);
			// console.log('answer:', answer);
			// console.log('SDP Offer: ', offer.sdp);
			await peerConnection.setRemoteDescription(
				new RTCSessionDescription({
					type: 'answer',
					sdp: answer
				})
			);
			connected = true;
			errorMessage = '';
		} catch (error) {
			errorMessage = String(error);
			console.error('Error setting up WebRTC:', error);
		}
	}
	// // Only run this code in the browser

	async function closeWebRTC() {
		if (localStream) {
			localStream.getTracks().forEach((track) => track.stop());
		}
		if (dataChannel) {
			dataChannel.close();
		}

		if (peerConnection) {
			peerConnection.close();
		}
		connected = false;
		errorMessage = '';
		peerConnectionId = '';
		console.log('Audio and data channels stopped.');
	}
	async function toggle() {
		if (connected) {
			await closeWebRTC();
		} else {
			await setupWebRTC();
		}
	}
</script>

<div
	class="min-w-screen mx-auto flex min-h-screen flex-col items-center justify-center bg-black text-slate-100"
>
	<button
		on:click={toggle}
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
	{#if errorMessage}
		<p class="mt-4 text-red-500">{errorMessage}</p>
	{/if}
</div>
