import twilio from 'twilio';
import type { RequestHandler } from '@sveltejs/kit';

const TWILIO_ACCOUNT_SID = process.env.TWILIO_ACCOUNT_SID || '';
const TWILIO_API_KEY = process.env.TWILIO_API_KEY || '';
const TWILIO_API_SECRET = process.env.TWILIO_API_SECRET || '';
const TWILIO_PHONE_NUMBER = process.env.TWILIO_PHONE_NUMBER || '';
const TWILIO_APP_SID = process.env.TWILIO_APP_SID || '';
const TWILIO_AUTH_TOKEN = process.env.TWILIO_AUTH_TOKEN || '';

// if (
// 	!TWILIO_ACCOUNT_SID ||
// 	!TWILIO_API_KEY ||
// 	!TWILIO_API_SECRET ||
// 	!TWILIO_PHONE_NUMBER ||
// 	!TWILIO_APP_SID
// ) {
// 	throw new Error('Missing required Twilio environment variables.');
// }

console.log('SID: ', TWILIO_ACCOUNT_SID);
console.log('API_KEY: ', TWILIO_API_KEY);
console.log('API_SECRET: ', TWILIO_API_SECRET);
console.log('Phone: ', TWILIO_PHONE_NUMBER);
console.log('APP_SID: ', TWILIO_APP_SID);

const client = twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, {
	accountSid: TWILIO_ACCOUNT_SID // You can also pass this if you need it in opts
});

export const POST: RequestHandler = async ({ request }) => {
	try {
		const { toPhoneNumber, identity } = await request.json();

		const AccessToken = twilio.jwt.AccessToken;
		const VoiceGrant = AccessToken.VoiceGrant;

		const token = new AccessToken(TWILIO_ACCOUNT_SID, TWILIO_API_KEY, TWILIO_API_SECRET, {
			ttl: 3600,
			identity: identity
		});
		token.identity = identity;

		const voiceGrant = new VoiceGrant({
			outgoingApplicationSid: TWILIO_APP_SID
		});
		token.addGrant(voiceGrant);

		const call = await client.calls.create({
			to: toPhoneNumber,
			from: TWILIO_PHONE_NUMBER,
			url: `${process.env.BASE_URL}/api/twiml`
		});

		return new Response(JSON.stringify({ token: token.toJwt(), callSid: call.sid }), {
			status: 200,
			headers: { 'Content-Type': 'application/json' }
		});
	} catch (error) {
		const typedError = error as Error;
		console.error('Error initiating call:', error);
		return new Response(
			JSON.stringify({ error: 'Error initiating call', message: typedError.message }),
			{ status: 500, headers: { 'Content-Type': 'application/json' } }
		);
	}
};
