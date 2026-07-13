import { defineWebhookSource } from "@keystrokehq/keystroke/trigger";
import { z } from "zod";
import workflow from "../workflows/application-submitted-notify";

export default defineWebhookSource({
  slug: "application-submitted",
  name: "Application Submitted",
  description: "Fires when JobApplicationTracker's backend successfully submits a job application.",
  endpoint: "application-submitted",
  payload: z.object({
    applicationId: z.number(),
    jobTitle: z.string(),
    company: z.string(),
    applyUrl: z.string().nullish(),
    atsPlatform: z.string().nullish(),
    appliedAt: z.string(),
  }),
}).attach({ workflow });
