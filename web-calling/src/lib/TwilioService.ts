import { Call } from '@twilio/voice-sdk'
import { Device } from '@twilio/voice-sdk';

export const createDevice = (token: string): Device => {
  const device = new Device(token, {
    codecPreferences: [Call.Codec.Opus, Call.Codec.PCMU],
  });

  device.on('ready', () => {
    console.log('Device is ready');
  });

  device.on('error', (error) => {
    console.error('Device error:', error);
  });

  return device;
};

export const initiateCall = (device: Device, toPhoneNumber: string) => {
  device.connect({
    params:{ 
      to: toPhoneNumber 
    }
  });
};
