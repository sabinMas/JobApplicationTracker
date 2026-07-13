import { definePollSource } from "@keystrokehq/keystroke/trigger";
import { gmailFetchEmails } from "@keystrokehq/gmail/actions";
import { z } from "zod";
import workflow from "../workflows/interview-inbox-triage";

const PollState = z.object({ lastCheckedAt: z.string() });

export default definePollSource({
  slug: "interview-inbox-poll",
  name: "Interview Inbox Poll",
  description: "Polls Gmail every 30 minutes for messages seen since the last check and hands new ones to the triage workflow.",
  schedule: "*/30 * * * *",
  state: PollState,
  run: async ({ state, setState }) => {
    const sinceMs = state ? new Date(state.lastCheckedAt).getTime() : Date.now() - 24 * 60 * 60 * 1000;

    const { messages } = await gmailFetchEmails.run({
      query: "in:inbox newer_than:2d",
      max_results: 20,
      verbose: true,
      ids_only: false,
      include_payload: true,
    });

    const newMessages: {
      messageId: string;
      threadId: string | null;
      subject: string | null;
      sender: string | null;
      messageText: string | null;
      messageTimestamp: string | null;
      displayUrl: string | null;
    }[] = [];
    let newestMs = sinceMs;

    for (const message of messages ?? []) {
      const timestampMs = Number(message.messageTimestamp ?? 0);
      if (timestampMs > sinceMs) {
        newMessages.push({
          messageId: message.messageId ?? "",
          threadId: message.threadId ?? null,
          subject: message.subject ?? null,
          sender: message.sender ?? null,
          messageText: message.messageText ?? null,
          messageTimestamp: message.messageTimestamp ?? null,
          displayUrl: message.display_url ?? null,
        });
      }
      if (timestampMs > newestMs) {
        newestMs = timestampMs;
      }
    }

    setState({ lastCheckedAt: new Date(newestMs).toISOString() });

    return { messages: newMessages };
  },
  filter: (result) => result.messages.length > 0,
}).attach({ workflow });
