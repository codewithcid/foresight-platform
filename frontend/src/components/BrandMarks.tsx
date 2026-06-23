// Hand-drawn icon marks that evoke each brand's visual identity (colors,
// general pictogram concept) without tracing or embedding the actual
// trademarked logo artwork -- an envelope-with-a-flap for mail, a
// phone-handset-in-a-speech-bubble for chat, both generic pictogram concepts
// long predating either brand, rendered in their recognizable brand colors.

export function MailMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size * 0.74} viewBox="0 0 40 30" xmlns="http://www.w3.org/2000/svg">
      <rect x="1" y="1" width="38" height="28" rx="3" fill="#ffffff" stroke="#dadce0" strokeWidth="1.5" />
      <path d="M3 3 L20 17 L37 3" fill="none" stroke="#ea4335" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3 27 L15 14" fill="none" stroke="#4285f4" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M37 27 L25 14" fill="none" stroke="#34a853" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M3 27 L3 4" fill="none" stroke="#fbbc05" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function WhatsAppMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
      <circle cx="20" cy="20" r="19" fill="#25D366" />
      <path
        d="M20 9a11 11 0 0 0-9.5 16.6L9 31l5.6-1.5A11 11 0 1 0 20 9z"
        fill="none" stroke="#ffffff" strokeWidth="1.6"
      />
      <path
        d="M15.5 15.2c.3-.6.9-.6 1.4-.2l1.1.9c.4.4.4.9.1 1.4l-.5.8c-.2.3-.1.7.1.9 1 1.1 2.2 1.9 3.6 2.3.3.1.6 0 .8-.3l.6-.9c.3-.4.8-.5 1.2-.2l1.3.9c.5.4.6 1 .2 1.5-1 1.4-2.8 1.9-4.4 1.2-2.4-1-4.5-2.9-5.7-5.2-.8-1.5-.5-3.3.6-4.1z"
        fill="#ffffff"
      />
    </svg>
  );
}
