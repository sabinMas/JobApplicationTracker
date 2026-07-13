import { defineWorkflow, promptLlm } from "@keystrokehq/keystroke/workflow";
import { gmailSendEmail } from "@keystrokehq/gmail/actions";
import { z } from "zod";

const InboxMessage = z.object({
  messageId: z.string(),
  threadId: z.string().nullish(),
  subject: z.string().nullish(),
  sender: z.string().nullish(),
  messageText: z.string().nullish(),
  messageTimestamp: z.string().nullish(),
  displayUrl: z.string().nullish(),
});

const Classification = z.object({
  isJobRelated: z.boolean(),
  category: z.enum(["interview_invite", "rejection", "recruiter_outreach", "application_update", "other"]),
  company: z.string().nullish(),
  summary: z.string(),
});

type Match = {
  subject: string;
  sender: string;
  category: string;
  company: string | null;
  summary: string;
  displayUrl: string | null;
};

function buildClassificationPrompt(message: z.infer<typeof InboxMessage>): string {
  return [
    "You are triaging one email from a job seeker's personal inbox.",
    "Decide whether it relates to a job application: an interview invite, a rejection, recruiter outreach, or an application status update.",
    "Marketing, newsletters, personal mail, and unrelated notifications are NOT job related.",
    "",
    `Subject: ${message.subject ?? "(none)"}`,
    `From: ${message.sender ?? "(unknown)"}`,
    `Body:\n${(message.messageText ?? "(no body)").slice(0, 2000)}`,
  ].join("\n");
}

function buildDigestBody(matches: Match[]): string {
  const lines = matches.map((match, index) => {
    const parts = [
      `${index + 1}. [${match.category}] ${match.company ?? "Unknown company"}`,
      `   Subject: ${match.subject}`,
      `   From: ${match.sender}`,
      `   ${match.summary}`,
    ];
    if (match.displayUrl) {
      parts.push(`   ${match.displayUrl}`);
    }
    return parts.join("\n");
  });

  return `Found ${matches.length} job-related email(s) in your inbox:\n\n${lines.join("\n\n")}`;
}

export default defineWorkflow({
  slug: "interview-inbox-triage",
  name: "Interview Inbox Triage",
  description: "Classifies newly seen inbox messages and emails a digest when any are interview invites, rejections, or recruiter replies.",
  input: z.object({ messages: z.array(InboxMessage) }),
  output: z.object({ matchCount: z.number(), notified: z.boolean() }),
  async run(input) {
    const matches: Match[] = [];

    for (const message of input.messages) {
      const classification = await promptLlm(buildClassificationPrompt(message), {
        model: "deepseek/deepseek-v4-flash",
        outputSchema: Classification,
      });

      if (classification.isJobRelated) {
        matches.push({
          subject: message.subject ?? "(no subject)",
          sender: message.sender ?? "(unknown sender)",
          category: classification.category,
          company: classification.company ?? null,
          summary: classification.summary,
          displayUrl: message.displayUrl ?? null,
        });
      }
    }

    if (matches.length === 0) {
      return { matchCount: 0, notified: false };
    }

    await gmailSendEmail.run({
      recipient_email: "masonsabin@gmail.com",
      subject: `Job search inbox: ${matches.length} update${matches.length === 1 ? "" : "s"}`,
      body: buildDigestBody(matches),
      is_html: false,
    });

    return { matchCount: matches.length, notified: true };
  },
});
