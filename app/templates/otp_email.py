def otp_email_html(code: str, minutes: int = 10) -> str:
    font = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

    return f"""\
<!DOCTYPE html>
<html>
<body style="margin:0; padding:0; background-color:#f4f4f5;">
  <!-- Preheader: the preview line shown in the inbox list -->
  <div style="display:none; max-height:0; overflow:hidden;">
    Your code is {code}. It expires in {minutes} minutes.
  </div>

  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f5; padding:40px 16px;">
    <tr>
      <td align="center">
        <table width="100%" cellpadding="0" cellspacing="0"
               style="max-width:440px; background-color:#ffffff; border-radius:16px;
                      border:1px solid #e4e4e7; font-family:{font};">

          <!-- Header -->
          <tr>
            <td style="padding:32px 32px 0;">
              <p style="margin:0; font-size:20px; font-weight:700; color:#18181b;">
                ∞ Nora<span style="color:#a1a1aa;">Chat</span>
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:24px 32px 8px;">
              <h1 style="margin:0 0 8px; font-size:22px; font-weight:600; color:#18181b;">
                Your sign-in code
              </h1>
              <p style="margin:0; font-size:15px; line-height:22px; color:#52525b;">
                Enter this code in the app to continue.
              </p>
            </td>
          </tr>

          <!-- Code box -->
          <tr>
            <td style="padding:16px 32px;">
              <div style="background-color:#f4f4f5; border-radius:12px; padding:20px;
                          text-align:center; font-size:34px; font-weight:700;
                          letter-spacing:10px; color:#18181b;
                          font-family:'SF Mono', Menlo, Consolas, monospace;">
                {code}
              </div>
            </td>
          </tr>

          <!-- Expiry note -->
          <tr>
            <td style="padding:0 32px 32px;">
              <p style="margin:0; font-size:13px; line-height:20px; color:#71717a;">
                This code expires in <strong>{minutes} minutes</strong>.
                If you didn't request it, you can safely ignore this email.
              </p>
            </td>
          </tr>
        </table>

        <!-- Footer -->
        <p style="margin:24px 0 0; font-size:12px; color:#a1a1aa; font-family:{font};">
          Sent by NoraChat · noraspace.in
        </p>
      </td>
    </tr>
  </table>
</body>
</html>"""


def otp_email_text(code: str, minutes: int = 10) -> str:
    return (
        f"Your NoraChat sign-in code is {code}\n\n"
        f"It expires in {minutes} minutes.\n"
        f"If you didn't request it, you can ignore this email."
    )