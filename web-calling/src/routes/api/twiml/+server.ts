import type { RequestHandler } from '@sveltejs/kit';

// GET handler to provide TwiML instructions
export const GET: RequestHandler = async () => {
  // TwiML response to connect the call to the WebRTC client
  const twiml = `
    <Response>
      <Dial>
        <Client>frontend-client</Client> <!-- Connects PSTN call to the frontend WebRTC client -->
      </Dial>
    </Response>
  `;

  return new Response(twiml, {
    status: 200,
    headers: {
      'Content-Type': 'application/xml',
    },
  });
};
