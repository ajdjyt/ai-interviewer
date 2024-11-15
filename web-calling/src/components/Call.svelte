<script lang="ts">
  import { onMount } from 'svelte';
  import { createDevice, initiateCall } from '../lib/TwilioService';  
  import { Device } from '@twilio/voice-sdk';


  let device: Device | undefined;
  let isCallActive = false;
  let callSid: string = '';
  let isLoading = false;
  let errorMessage: string | null = null;

  async function initiateCallHandler(token: string, toPhoneNumber: string) {
    try {
      isLoading = true;
      errorMessage = null;
      device = createDevice(token);
      device.on('incoming', (call) => {
        console.log('Incoming call:', call);
        call.accept(); // Automatically accept the incoming call
        isCallActive = true;
        callSid = call.parameters.CallSid;
      });
      device.on('disconnect', () => {
        console.log('Call disconnected');
        isCallActive = false;
      });
      initiateCall(device, toPhoneNumber);
    } catch (error) {
      const typedError = error as Error;
      console.error('Error initiating call:', typedError);
      errorMessage = typedError.message;
    } finally {
      isLoading = false;
    }
  }

  onMount(async () => {
    try {
      const response = await fetch('/api/make-call', {
        method: 'POST',
        body: JSON.stringify({ toPhoneNumber: '+918296759003', identity: 'frontend-client' }),
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        throw new Error('Failed to initiate the call');
      }

      const { token } = await response.json();
      initiateCallHandler(token, '+918296759003'); 
    } catch (error) {
      const typedError = error as Error;
      errorMessage = 'Error initiating call: ' + typedError.message;
    }
  });

  function endCall() {
    if (device) {
      device.disconnectAll();
    }
  }
</script>


<style>
  .call-container {
    padding: 20px;
    text-align: center;
  }

  .loading, .error-message {
    color: red;
  }

  .call-btn {
    padding: 10px 20px;
    font-size: 16px;
    background-color: #007bff;
    color: white;
    border: none;
    cursor: pointer;
  }

  .call-btn:disabled {
    background-color: #ccc;
  }
</style>

<div class="call-container">
  <h2>Call to PSTN</h2>
  
  {#if isLoading}
    <p class="loading">Loading...</p>
  {:else if errorMessage}
    <p class="error-message">{errorMessage}</p>
  {:else if isCallActive}
    <button class="call-btn" on:click={endCall}>End Call</button>
  {:else}
    <p>Calling...</p>
  {/if}
</div>