import { defineWorkflow } from "@keystrokehq/keystroke/workflow";
import { gmailSendEmail } from "@keystrokehq/gmail/actions";
import { z } from "zod";

export default defineWorkflow({
  slug: "application-submitted-notify",
  name: "Application Submitted Notify",
  description: "Emails Mason a confirmation whenever JobApplicationTracker submits a new job application.",
  input: z.object({
    applicationId: z.number(),
    jobTitle: z.string(),
    company: z.string(),
    applyUrl: z.string().nullish(),
    atsPlatform: z.string().nullish(),
    appliedAt: z.string(),
  }),
  output: z.object({ notified: z.boolean() }),
  async run(input) {
    const lines = [
      `Applied to: ${input.jobTitle} at ${input.company}`,
      `Submitted: ${input.appliedAt}`,
    ];
    if (input.atsPlatform) {
      lines.push(`Platform: ${input.atsPlatform}`);
    }
    if (input.applyUrl) {
      lines.push(`Listing: ${input.applyUrl}`);
    }

    await gmailSendEmail.run({
      recipient_email: "masonsabin@gmail.com",
      subject: `Application submitted: ${input.jobTitle} at ${input.company}`,
      body: lines.join("\n"),
      is_html: false,
    });

    return { notified: true };
  },
});
