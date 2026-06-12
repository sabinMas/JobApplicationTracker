# UX Audit Report: JobApplicationTracker

**Date:** 2026-06-12  
**Scope:** Complete user journey from onboarding through job applications  
**Focus:** Clarity, trust, state persistence, and guided workflows

---

## 1. EXECUTIVE SUMMARY

**Current State:** The app has good technical components (resume extraction with feedback, form states, persistence) but suffers from:
- **Unclear product purpose** — what does the app actually do? Users see "Powered by Cerebras AI" which is incorrect
- **Broken user flow** — no clear path from signup → profile → preferences → jobs → apply
- **State persistence problems** — preferences save but don't show lasting confirmation
- **Inconsistent theming** — dashboard is dark/modern while other pages are light/minimal
- **Hidden functionality** — onboarding exists but users aren't routed to it; auto-apply isn't clearly labeled

**Impact:** Users likely feel lost, don't understand what they're setting up preferences for, and don't see their preferences being used.

---

## 2. KEY FINDINGS BY PAGE

### Onboarding (`/onboarding`)
**✅ Strengths:**
- Clear 3-step flow with visual progress
- Resume extraction shows success/failure states with detailed feedback
- Shows "Updated fields" badges (e.g., "Full Name", "Email")
- Extracts and auto-saves profile data
- Has "Next" buttons guiding to next step

**❌ Weaknesses:**
- **CRITICAL:** Not auto-routed. Users hitting "/" don't see this—must know the URL
- Step 2 (cover letters) says "Optional" but doesn't make the skip button obvious
- No progress indicator (e.g., "Step 1 of 3")
- No explanation of WHY we need each step
- "Powered by Claude will..." messaging incorrect in some places

### Profile (`/profile`)
**✅ Strengths:**
- Good extraction feedback with state transitions
- Shows what was updated with colored badges
- Resume upload shows "Profile auto-saved!" with changed fields
- Clear section breaks (Personal Info, Skills, Experience, Education, Documents)
- Document management with upload/delete states

**❌ Weaknesses:**
- No explanation of how profile data is USED (for resume tailoring, form filling, etc.)
- Resume extraction card doesn't explain why we need it
- Extracts and merges but users don't know that's happening
- No link to "Next step" (go to Preferences or Dashboard)
- Document upload states timeout too quickly (5 seconds)

### Preferences (`/preferences`)
**✅ Strengths:**
- Clear sections for each preference type (roles, niches, keywords, locations)
- Tag-based UI is intuitive
- "AI Suggest" button to seed preferences from profile
- Save button with states (Saving..., Saved!)

**❌ Weaknesses:**
- **CRITICAL:** No explanation of what preferences are FOR (job filtering, auto-apply threshold, scoring)
- Save button shows "Saved!" for only 2.5 seconds — users can't see lasting confirmation
- No indication that preferences are being USED to find or score jobs
- No link to "Next step" (go to Dashboard or Jobs)
- No empty state explanation ("Set these to find matching jobs")
- Heading says "the pipeline uses these to score and filter" but pipeline page doesn't show that

### Dashboard (`/`)
**✅ Strengths:**
- Shows key metrics: Jobs Discovered, Applications, Success Rate, Avg Score
- Charts show score distribution and jobs by source
- Onboarding guidance cards if profile is missing
- Links to Profile and Preferences with CTA buttons

**❌ Weaknesses:**
- **CRITICAL MISMATCH:** Dark theme with gradient background vs. light/minimal in other pages
- Message says "Go to Preferences to define what jobs you're looking for, then click Run Now on Pipeline page"—but there's no "Run Now" button visible in Pipeline
- Doesn't explain what "discovered" means (auto-scraped? manual? both?)
- Success rate is 0% if no applications—misleading
- No "Start Here" flow if user is brand new

### Pipeline (`/pipeline`)
**✅ Strengths:**
- Shows Kanban board of applications by status
- Can view application details
- Status tracking (pending, applied, in_review, etc.)

**❌ Weaknesses:**
- No "Run Now" or "Discover Jobs" button visible (Dashboard mentions it)
- Doesn't show what preferences are being used to filter/score
- No "0 applications" empty state with guidance

### Add Job (`/search`)
**✅ Strengths:**
- Three ways to add: URL import, Greenhouse search, manual
- Shows success feedback when job is scraped
- Links to application detail

**❌ Weaknesses:**
- No explanation of what happens after you add a job
- No link to "Next step" (apply, or go to pipeline)
- Greenhouse search error message could be clearer

### Navigation / App-Wide
**❌ Critical Issues:**
1. **"Powered by Cerebras AI"** in sidebar is WRONG—should say Claude/Bedrock per CLAUDE.md
2. No consistent app-wide onboarding—users can hit "/" and see Dashboard with no guidance
3. No breadcrumb or "next step" hints—users bounce between pages confused
4. Sidebar labels are vague (what's "Pipeline"? what's "Preferences"?)
5. No progress indicator (e.g., "Step 3: Set Preferences" when on /preferences)
6. No persistent save indicator—users wonder if preferences actually saved

---

## 3. USER PROBLEMS (Root Causes)

### Problem 1: Unclear Product Purpose
**Symptom:** User feels lost about what the app does  
**Root Cause:** No clear messaging about purpose  
**Evidence:** 
- Sidebar says "AI-powered job automation" but doesn't say what that means
- Dashboard references "pipeline," "scoring," "discovery" without defining them
- No explanation of the full workflow (find → score → tailor → apply)

### Problem 2: Preferences Don't Feel Persisted
**Symptom:** User sets preferences, leaves the page, returns unsure if they saved  
**Root Cause:** 
- Save confirmation only shows for 2.5 seconds
- No persistent indication that preferences are being actively used
- Preferences page doesn't show "Saved" or "Last updated" after reload

**Evidence:**
```tsx
// Preferences.tsx, line 24-31
const saveMutation = useMutation({
  mutationFn: updatePreferences,
  onSuccess: () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)  // ← Only 2.5 seconds!
  },
})
```

### Problem 3: No Guided Workflow
**Symptom:** User doesn't know what to do next after each page  
**Root Cause:**
- Each page is standalone; no indication of overall flow
- No progress indicator or roadmap
- No "Next" buttons linking pages

**Evidence:**
- Profile page doesn't link to "Go to Preferences"
- Preferences page doesn't link to "View Jobs"
- Dashboard guidance mentions "Pipeline" but no clear button

### Problem 4: Upload Feedback Disappears Too Quickly
**Symptom:** User uploads resume, sees "Profile auto-saved!" but it vanishes  
**Root Cause:** Success state times out after 5 seconds  

**Evidence:**
```tsx
// Profile.tsx, ResumeExtractUpload, line 368
setTimeout(() => setStatus('idle'), 5000)  // ← 5 seconds is too fast
```

### Problem 5: Onboarding Not Auto-Routed
**Symptom:** New users land on Dashboard with no guidance; onboarding page exists but isn't used  
**Root Cause:**
- Onboarding is a separate route (`/onboarding`) but App doesn't auto-route to it
- Dashboard shows "Upload your resume" CTA but doesn't link to onboarding flow

**Evidence:**
- App.tsx renders either onboarding OR main nav, but no logic to redirect new users
- Profile has full extraction UI but onboarding has a guided 3-step version

### Problem 6: Inconsistent Visual Branding
**Symptom:** Dashboard looks completely different from other pages  
**Root Cause:**
- Dashboard uses dark gradient background, white text, slate colors
- Other pages use light `parchment-50` background, light cards
- No shared design system enforcement

---

## 4. PROPOSED NEW FLOW & MESSAGING

### The Core User Journey (Simplified for Clarity)
```
1. SETUP Profile
   └─ "Upload your resume so we can understand your background"
   
2. SET Preferences
   └─ "Tell us what kind of jobs you want (roles, locations, keywords)"
   
3. DISCOVER Jobs
   └─ "We'll search and AI-score jobs matching your preferences"
   
4. REVIEW & APPLY
   └─ "Review scored jobs and apply to high-match ones"
```

### Proposed UX Changes

#### A. Clear Product Messaging
**In:** Sidebar footer, Dashboard hero, Onboarding hero
**Message:**
```
JobTracker: AI-powered job application assistant
• Discover jobs that match your profile
• AI scores each job 1-10
• Tailor your resume for each application
• Auto-fill application forms
• Track all submissions in one place
```

#### B. Fix Preferences Persistence
**Change:** 
- Keep "Saved!" indicator visible for 5+ seconds (not 2.5)
- Add "Last updated" timestamp below Save button
- Show a "Preferences Active" badge in sidebar
- When preferences are loaded, show "✓ Using X target roles, Y avoid keywords"

#### C. Add Progress/Next-Step Indicators
**Change:**
- Profile page footer: "✓ Profile set up. **Next →** Set your job preferences"
- Preferences page footer: "✓ Preferences saved. **Next →** Review discovered jobs"
- Dashboard "ready" state: "✓ All set up! **Find Jobs** or **Review Pipeline**"

#### D. Consistent Visual Design
**Change:**
- Dashboard should match the light `parchment-50` theme used elsewhere
- Use same card styles, same typography
- Maintain the sidebar-based layout even on Dashboard

#### E. Auto-Route New Users
**Change:**
- If user has no profile data, auto-redirect "/" → "/onboarding"
- After onboarding completes, show "Next: Set Preferences" flow
- After preferences, show "Next: Discover Jobs" with a button

---

## 5. HIGH-PRIORITY IMPLEMENTATION PLAN

### Tier 1 (Immediate — User Trust)
1. **Fix "Powered by Cerebras AI"** → "Powered by Claude AI"
2. **Fix Preferences Persistence:**
   - Keep "Saved!" visible for 5 seconds (not 2.5)
   - Add "Last updated at X" timestamp
   - Don't clear the "saved" state immediately
3. **Fix Upload Feedback Timing:**
   - Keep "Profile auto-saved!" visible for 8 seconds (not 5)
   - Or keep it visible until user navigates away

### Tier 2 (High Impact — Clarity & Guidance)
4. **Add Product Messaging:**
   - Update sidebar footer with 3-4 line explanation
   - Add "What is JobTracker?" section to Dashboard
   - Update onboarding copy to explain each step's purpose
5. **Add Next-Step Buttons:**
   - Profile page: "Set Preferences →" button
   - Preferences page: "View Jobs →" button  
   - Dashboard: "Start Setup" button if onboarded
6. **Fix Dashboard Styling:**
   - Change to light theme matching other pages
   - Keep sidebar navigation

### Tier 3 (Workflow Improvement)
7. **Auto-Route Onboarding:**
   - Redirect new users to `/onboarding` instead of Dashboard
   - Track completion state (has profile + preferences)
8. **Add Progress Indicators:**
   - Show "Step 1 of 3" in onboarding
   - Show "Setup Progress: Profile → Preferences → Jobs → Apply" header
9. **Consistent Upload States:**
   - Use standardized "uploading" → "success" → "clear after nav" pattern
   - Show clear summary of what was extracted

---

## 6. IMPLEMENTATION PRIORITY (By Impact)

| Priority | Issue | Effort | Impact | File |
|----------|-------|--------|--------|------|
| 🔴 HIGH | "Powered by Cerebras" → Claude | 1 line | Trust | App.tsx |
| 🔴 HIGH | Preferences save timeout 5s | 1 line | Trust | Preferences.tsx |
| 🔴 HIGH | Upload feedback timeout 8s | 1 line | Trust | Profile.tsx |
| 🟡 MEDIUM | Product messaging in sidebar | 5 lines | Clarity | App.tsx |
| 🟡 MEDIUM | Add "Next" buttons to Profile/Preferences | 10 lines | Guidance | Profile.tsx, Preferences.tsx |
| 🟡 MEDIUM | Add "Profile Updated" timestamp in Preferences | 5 lines | Persistence | Preferences.tsx |
| 🟠 LOWER | Consistent Dashboard styling | 30 lines | Branding | Dashboard.tsx |
| 🟠 LOWER | Auto-route new users to onboarding | 20 lines | Workflow | App.tsx |
| 🟠 LOWER | Progress indicators in onboarding | 10 lines | Clarity | Onboarding.tsx |

**Start with Tier 1 (3 items, 3 lines total)** — these build trust immediately.

---

## 7. SPECIFIC CODE CHANGES NEEDED

### File: `frontend/src/App.tsx`
```tsx
// Line 43: Change sidebar footer
<p className="text-[10px] text-gray-600 leading-relaxed">
-  AI-powered job automation.
-  Bedrock + Lambda + ECS.
+  Find, score & apply to jobs
+  with AI-tailored resumes.
</p>

// Line 43: Change the brand line
<p className="font-bold text-gray-800 text-sm leading-tight">JobTracker</p>
- <p className="text-[10px] text-brand-700">Powered by Cerebras AI</p>
+ <p className="text-[10px] text-brand-700">Powered by Claude AI</p>
```

### File: `frontend/src/pages/Preferences.tsx`
```tsx
// Line 29: Extend timeout
- setTimeout(() => setSaved(false), 2500)
+ setTimeout(() => setSaved(false), 5000)
```

### File: `frontend/src/pages/Profile.tsx`
```tsx
// Line 368: Extend upload feedback timeout
- setTimeout(() => setStatus('idle'), 5000)
+ setTimeout(() => setStatus('idle'), 8000)

// Line 24: Add last_updated tracking
const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
const mutation = useMutation({
  mutationFn: (data: Profile) => updateProfile(data),
  onSuccess: () => {
    qc.invalidateQueries({ queryKey: ['profile'] })
    setSaved(true)
    setLastUpdated(new Date())
    setTimeout(() => setSaved(false), 5000)
  },
})

// Line 54-62: Add timestamp display after Save button
{lastUpdated && (
  <p className="text-xs text-gray-500 mt-1">
    Last updated {formatDistanceToNow(lastUpdated, { addSuffix: true })}
  </p>
)}
```

### File: `frontend/src/pages/Preferences.tsx`
```tsx
// Add after save mutation (line 32):
const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

const saveMutation = useMutation({
  mutationFn: updatePreferences,
  onSuccess: () => {
    qc.invalidateQueries({ queryKey: ['preferences'] })
    setSaved(true)
    setLastUpdated(new Date())
    setTimeout(() => setSaved(false), 5000)  // Changed from 2500
  },
})

// Add timestamp display (after Save button, line 79):
{lastUpdated && (
  <p className="text-xs text-gray-500 mt-1">
    Last updated {formatDistanceToNow(lastUpdated, { addSuffix: true })}
  </p>
)}
```

---

## 8. REMAINING GAPS (Post-MVP)

These are intentionally NOT in the implementation plan (too large for this sprint):

1. **Auto-routing to onboarding** — Requires checking onboarding state on app load (db query)
2. **Consistent Dashboard styling** — Requires full component rewrite (~100 lines)
3. **Progress indicators** — Requires new component + state management
4. **"Run Now" button in Pipeline** — Requires clarifying what "discover jobs" means (manual vs. automatic)
5. **Preferences → Jobs link** — Requires deciding if we auto-discover or link to manual search

---

## SUMMARY

**Root Issues:**
1. Branded wrong (Cerebras not Claude)
2. Preferences don't feel saved
3. No clear user flow
4. No explanation of what the app does

**Quick Fixes (3 items, 10 minutes):**
1. Change "Cerebras" → "Claude"
2. Extend save timeouts (2.5s → 5s, 5s → 8s)
3. Add "Last updated" timestamps

**These changes will:**
- Restore trust (show persistence)
- Clarify purpose (Claude branding, better messaging)
- Guide users (next-step buttons, timestamps show saving works)
