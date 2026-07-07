"""
build_dataset.py
================
Generates the email->reply dataset used by this project.

WHERE THE DATA COMES FROM
-------------------------
The data is *hand-authored synthetic* data modelled on a real SaaS customer-support
shared inbox (the domain Hiver operates in). Every pair was written by a human
(the author) to be realistic: real intents, real tone, real edge cases. No PII,
no scraped customer data, so it is safe to publish.

WHY IT IS REPRESENTATIVE
------------------------
A support inbox is dominated by a small number of recurring *intents*. We cover the
ones that make up the long tail of a B2B SaaS support queue:
    billing / invoicing, refunds, cancellations, technical bugs, how-to questions,
    account access / login, sales / pricing, feature requests, integrations,
    onboarding, complaints / escalations, and outages.
Each intent appears multiple times with *different phrasings and difficulty* so a
retriever has something meaningful to retrieve, and so the evaluator is tested on
easy, medium and hard cases.

OUTPUT
------
    emails.jsonl    -> reference/"training" pool the generator retrieves from
    test_set.jsonl  -> held-out incoming emails with GOLD replies + a human quality
                       note (used to validate the accuracy metric)

Run:  python data/build_dataset.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# REFERENCE POOL  (incoming email  ->  the reply an experienced agent sent)
# Fields: id, category, subject, email, reply
# ---------------------------------------------------------------------------
REFERENCE = [
    # ---- Billing / invoicing ----
    dict(id="ref-001", category="billing",
         subject="Wrong amount charged this month",
         email="Hi, we were billed $290 this month but our plan is $240. Can you tell me why the amount is higher than usual?",
         reply="Hi there,\n\nThanks for flagging this. The extra $50 is a proration charge: you added one seat on the 12th, so this invoice covers the new seat for the remainder of the current cycle plus your usual $240. From next month you'll be back to a flat $290 for 6 seats. I've attached the itemised invoice so you can see the breakdown. Happy to walk through it on a call if that's easier.\n\nBest,\nSupport Team"),
    dict(id="ref-002", category="billing",
         subject="Need a copy of our invoice",
         email="Could you send us the invoice for June? Our finance team needs it for reconciliation.",
         reply="Hi,\n\nOf course - I've attached your June invoice (PDF) to this email. You can also download all past invoices anytime from Settings > Billing > Invoice history. If your finance team needs a specific PO number or billing address added, just let me know and I'll reissue it.\n\nBest,\nSupport Team"),
    dict(id="ref-003", category="billing",
         subject="Update credit card on file",
         email="Our card on file expired. How do I update the payment method before the next charge?",
         reply="Hi,\n\nYou can update it in under a minute: go to Settings > Billing > Payment method, click 'Update card', and enter the new details. The change applies immediately and your next charge will use the new card. Nothing else is needed on your end - no interruption to your service. Let me know if the page gives you any trouble.\n\nBest,\nSupport Team"),

    # ---- Refunds ----
    dict(id="ref-004", category="refund",
         subject="Refund for accidental annual upgrade",
         email="I accidentally clicked the annual plan and got charged $1,200. I meant to stay monthly. Can I get a refund?",
         reply="Hi,\n\nTotally understand - that's an easy mistake. I've moved you back to the monthly plan and refunded the full $1,200 to your original card. Refunds usually land within 5-7 business days depending on your bank. You'll get a separate confirmation email once it's processed. Sorry for the scare, and let me know if anything looks off.\n\nBest,\nSupport Team"),
    dict(id="ref-005", category="refund",
         subject="Requesting refund - not using the product",
         email="We haven't used the tool since we signed up 3 weeks ago and want a refund for this month.",
         reply="Hi,\n\nThanks for being upfront about it. You're within our 30-day window, so I've processed a full refund for this month's charge - it'll appear on your card in 5-7 business days. Your account will stay active until the end of the current period in case your team wants to give it another try; after that it won't renew. If there was something specific that got in the way, I'd genuinely like to hear it.\n\nBest,\nSupport Team"),

    # ---- Cancellation ----
    dict(id="ref-006", category="cancellation",
         subject="How do I cancel",
         email="We want to cancel our subscription. What's the process and will we lose our data?",
         reply="Hi,\n\nSorry to see you go. You can cancel from Settings > Billing > Cancel plan - it takes effect at the end of your current billing period, so you keep full access until then and won't be charged again. Your data isn't deleted immediately: we retain it for 60 days after cancellation, so you can export everything (Settings > Data > Export) or reactivate without losing anything. Let me know if you'd like a hand exporting.\n\nBest,\nSupport Team"),

    # ---- Technical bug ----
    dict(id="ref-007", category="bug",
         subject="Export button not working",
         email="The CSV export button does nothing when I click it. I'm on Chrome. This is blocking my report.",
         reply="Hi,\n\nSorry that's holding up your report. This is usually caused by a browser extension blocking the download or a stale cached version of the app. Two quick things to try: (1) open the app in an incognito window and click Export, and (2) if that works, disable ad-block/download-manager extensions on our domain. If it still fails in incognito, reply with your account email and roughly what time you clicked - I'll pull the server logs and get our engineers on it right away.\n\nBest,\nSupport Team"),
    dict(id="ref-008", category="bug",
         subject="Getting a 500 error on save",
         email="Every time I try to save a record I get a '500 internal server error'. Started this morning.",
         reply="Hi,\n\nThanks for the report and sorry for the disruption. A 500 on save that started this morning points to something on our side, not your setup. I've logged this with engineering as a priority and included your account so they can trace it. As a temporary workaround, saving one field at a time (rather than a bulk edit) is getting past the error for most people. I'll email you the moment it's fixed - should be within a few hours.\n\nBest,\nSupport Team"),

    # ---- How-to ----
    dict(id="ref-009", category="howto",
         subject="How to add teammates",
         email="How do I invite my team to the account? There are 4 of us.",
         reply="Hi,\n\nHappy to help. Go to Settings > Team > Invite members, enter your 4 teammates' email addresses (comma-separated is fine), pick a role for each, and hit Send. They'll get an invite link that's valid for 7 days. You can change anyone's role or remove them later from the same page. Since you're adding 4 seats, your next invoice will reflect the extra seats, prorated for the current cycle.\n\nBest,\nSupport Team"),
    dict(id="ref-010", category="howto",
         subject="Can I set up automatic reminders?",
         email="Is there a way to automatically remind assignees about overdue tasks?",
         reply="Hi,\n\nYes - that's exactly what Automations are for. Go to Settings > Automations > New rule, choose the trigger 'Task is overdue', and set the action to 'Send reminder to assignee'. You can pick how often it repeats (e.g. daily until done) and quiet hours so it doesn't fire overnight. It takes about two minutes to set up. Want me to send a short screen-recording walking through it?\n\nBest,\nSupport Team"),

    # ---- Account access ----
    dict(id="ref-011", category="access",
         subject="Locked out of my account",
         email="I've been locked out after too many login attempts. I need to get in urgently for a client call.",
         reply="Hi,\n\nI understand the urgency - let's get you back in. For security the lockout auto-clears after 15 minutes, but I've just cleared it manually on my side so you can sign in right now. Please use the 'Forgot password' link to set a fresh password, and if you have 2FA handy, keep it nearby. If you're still stuck in the next few minutes, reply here and I'll stay on it until you're in.\n\nBest,\nSupport Team"),
    dict(id="ref-012", category="access",
         subject="SSO not working for new hire",
         email="Our new employee can't log in via Okta SSO - it says 'user not provisioned'. Everyone else works fine.",
         reply="Hi,\n\nThanks for the detail - 'user not provisioned' with everyone else working almost always means the new hire hasn't been assigned to our app in Okta yet. In your Okta admin console, open Applications > our app > Assignments and add the new employee (or the group they belong to). Once assigned, they should be able to log in within a couple of minutes. If it still fails after that, send me the exact email they're using and I'll check our provisioning logs.\n\nBest,\nSupport Team"),

    # ---- Sales / pricing ----
    dict(id="ref-013", category="sales",
         subject="Pricing for 50 users",
         email="We're evaluating your product for a team of 50. What pricing options do you have at that scale?",
         reply="Hi,\n\nThanks for considering us for your team of 50 - that's squarely in our Business tier, and at that size you're eligible for volume pricing plus a dedicated onboarding specialist. Rather than quote a list price, I'd like to put together numbers that fit how you'll actually use it. Are you open to a 20-minute call this week? In the meantime I can start a 14-day trial with all Business features unlocked so your team can evaluate hands-on. Just say the word.\n\nBest,\nSupport Team"),
    dict(id="ref-014", category="sales",
         subject="Do you offer a nonprofit discount?",
         email="We're a registered nonprofit. Do you have any discount for organizations like ours?",
         reply="Hi,\n\nWe do - registered nonprofits get 30% off any annual plan. To set it up, reply with a copy of your 501(c)(3) determination letter (or your local equivalent) and I'll apply the discount to your account, including a credit for the current term if you're already paying. Thanks for the work you do, and I'm glad we can help stretch your budget a little further.\n\nBest,\nSupport Team"),

    # ---- Feature request ----
    dict(id="ref-015", category="feature_request",
         subject="Please add dark mode",
         email="Would love a dark mode. Staring at the white screen all day is rough. Any plans?",
         reply="Hi,\n\nYou're not alone - dark mode is one of our most-requested items, and the good news is it's actively on the roadmap for this quarter. I've added your vote to the request so you'll be notified the moment it ships. In the meantime, if you're on Chrome or Edge, a browser-level 'force dark' flag gives a rough version today. Thanks for the nudge - it genuinely helps us prioritise.\n\nBest,\nSupport Team"),
    dict(id="ref-016", category="feature_request",
         subject="API rate limits too low",
         email="Your API caps us at 100 requests/min and we keep hitting it during syncs. Can this be raised?",
         reply="Hi,\n\nThanks for the concrete detail - hitting 100 req/min during syncs is a fair reason to raise the limit. On the Business plan we can lift you to 1,000 req/min; I can enable that on your account today. Two suggestions that also help: batch your sync into our bulk endpoints (one call updates up to 200 records) and add exponential backoff on 429s so bursts smooth out. Want me to bump the limit now?\n\nBest,\nSupport Team"),

    # ---- Integrations ----
    dict(id="ref-017", category="integration",
         subject="Slack notifications stopped",
         email="Our Slack notifications suddenly stopped coming through yesterday. Nothing changed on our end.",
         reply="Hi,\n\nSorry for the silence in Slack. A sudden stop like this is usually an expired Slack token (they can be revoked when a Slack admin changes app permissions). The fix is quick: go to Settings > Integrations > Slack, click 'Reconnect', and re-authorise. That reissues the token and notifications should resume immediately. If it still doesn't fire a test notification after reconnecting, tell me which channel it targets and I'll check the delivery logs.\n\nBest,\nSupport Team"),

    # ---- Onboarding ----
    dict(id="ref-018", category="onboarding",
         subject="Where do I start?",
         email="Just signed up and feeling a bit lost. What's the best way to get started quickly?",
         reply="Hi, and welcome!\n\nHappy to point you the right way. The fastest path is our 3-step Setup Guide (top-right 'Get started' checklist): (1) import or add your first data, (2) invite a teammate so you're not working solo, (3) set up one automation to feel the value. That takes about 15 minutes and covers 80% of what most teams use. If you tell me what you're hoping to achieve, I'll tailor the next steps - and I'm happy to jump on a quick onboarding call.\n\nBest,\nSupport Team"),

    # ---- Complaint / escalation ----
    dict(id="ref-019", category="complaint",
         subject="Very frustrated with repeated downtime",
         email="This is the third outage this month. We're paying for a reliable service and not getting it. Extremely disappointed.",
         reply="Hi,\n\nYou're right to be frustrated, and I won't sugar-coat it - three disruptions in a month is not the standard we hold ourselves to, and I'm sorry for the impact on your team. Here's what I'm doing concretely: I've escalated your account to our reliability lead, I'm applying a credit for this month to your account, and I'll personally send you a written summary of the root cause and the fixes we're putting in place within 48 hours. You deserve to know it won't keep happening. Can I also set up a call with our engineering lead directly?\n\nBest,\nSupport Team"),
    dict(id="ref-020", category="complaint",
         subject="Nobody has replied to my ticket",
         email="I opened a ticket 4 days ago and still no response. This is unacceptable for a paid plan.",
         reply="Hi,\n\nFour days without a reply on a paid plan is genuinely not okay, and I'm sorry - that ticket slipped through a routing gap on our side, which I'm fixing so it can't recur. I'm treating your issue as top priority right now. To get moving fast, can you confirm the ticket number or briefly restate the problem here? I'll own it personally from this point and won't hand you off.\n\nBest,\nSupport Team"),

    # ---- Outage / status ----
    dict(id="ref-021", category="outage",
         subject="Is the service down?",
         email="The app won't load for anyone on our team. Is there an outage right now?",
         reply="Hi,\n\nThanks for checking in - yes, we're aware of a partial outage affecting app loading and our team is actively on it. You can follow live updates at status.ourapp.com (subscribe there for push updates). We expect resolution shortly and I'll also reply here once it's fully restored. Sorry for the disruption to your team's morning.\n\nBest,\nSupport Team"),

    # ---- Data / export ----
    dict(id="ref-022", category="howto",
         subject="Export all our data",
         email="We need a full export of all our data for a compliance audit. What formats do you support?",
         reply="Hi,\n\nHappy to help with the audit. Go to Settings > Data > Export and choose 'Full account export' - you can export as CSV (per-table) or JSON (complete, structured). For large accounts we generate it asynchronously and email you a secure download link when it's ready, usually within 30 minutes. If your auditors need a specific schema or a signed data-processing summary, let me know and I'll arrange it.\n\nBest,\nSupport Team"),

    # ---- Security ----
    dict(id="ref-023", category="security",
         subject="Do you support 2FA / SAML?",
         email="Before we roll this out company-wide, does your product support two-factor auth and SAML SSO?",
         reply="Hi,\n\nGreat questions to ask before a rollout. Yes on both: two-factor authentication (authenticator app or SMS) is available on every plan and can be enforced org-wide from Settings > Security. SAML SSO (Okta, Azure AD, Google, OneLogin) is included on the Business plan and up, with SCIM provisioning so users are added/removed automatically. I can share our security whitepaper and SOC 2 report if that's useful for your review.\n\nBest,\nSupport Team"),

    # ---- Extra how-to / mixed for retrieval depth ----
    dict(id="ref-024", category="howto",
         subject="Change notification email",
         email="How do I change the email address that gets our account notifications?",
         reply="Hi,\n\nYou can point notifications wherever you like: Settings > Notifications > Delivery address. You can even route different notification types to different addresses (e.g. billing to finance, alerts to your ops channel). Changes take effect immediately. If you'd rather send them to a shared inbox or distribution list, that works too - just enter that address.\n\nBest,\nSupport Team"),
    dict(id="ref-025", category="billing",
         subject="Switch from monthly to annual",
         email="We'd like to switch to annual billing to save money. How does that work and when does it take effect?",
         reply="Hi,\n\nSmart move - annual billing saves you about 20% versus monthly. You can switch anytime from Settings > Billing > Change plan > Annual. When you switch, we credit the unused portion of your current month against the annual charge, so you're never double-paying. The annual term starts immediately and renews a year out. Want me to preview the exact prorated amount before you confirm?\n\nBest,\nSupport Team"),
    dict(id="ref-026", category="bug",
         subject="Emails going to spam",
         email="Notifications from your system keep landing in our spam folder. How do we fix that?",
         reply="Hi,\n\nAnnoying when useful emails hide in spam. The reliable fix is on the receiving side: ask your email admin to add our sending domain to the allow-list/safe-senders, and (if you run your own domain) it helps to whitelist our IP range - I can send that list. On our side everything is properly authenticated (SPF, DKIM, DMARC all pass), so allow-listing us is enough to keep them in the inbox going forward.\n\nBest,\nSupport Team"),
    dict(id="ref-027", category="sales",
         subject="Can we get a trial extension?",
         email="Our trial ends tomorrow but we haven't finished evaluating. Can we get more time?",
         reply="Hi,\n\nAbsolutely - I've extended your trial by 14 more days, no strings attached, so your team has room to finish evaluating properly. Everything you've set up stays exactly as-is. If it would help, I'm happy to jump on a short call to answer any open questions and make sure you're seeing the parts that matter most for your use case. What's still on your list to test?\n\nBest,\nSupport Team"),
    dict(id="ref-028", category="access",
         subject="Remove a former employee",
         email="An employee left the company. How do we revoke their access immediately?",
         reply="Hi,\n\nImportant to get right - here's the fast path. Go to Settings > Team, find the person, and click 'Remove'. That instantly revokes their access and ends any active sessions. Their work stays in the account (nothing is deleted) and you can reassign anything they owned. If you use SSO/SCIM, deprovisioning them in your identity provider will also remove them automatically. Want me to confirm they're fully removed once you've done it?\n\nBest,\nSupport Team"),
    dict(id="ref-029", category="feature_request",
         subject="Bulk edit would save us hours",
         email="Editing records one by one is painful. Is bulk edit something you're considering?",
         reply="Hi,\n\nCompletely hear you - one-by-one editing at scale is a real time sink. Bulk edit is on our roadmap, and I've added your vote so you'll be notified when it lands. In the meantime there are two workarounds that help a lot today: (1) our CSV import supports upsert, so you can export, edit in a spreadsheet, and re-import changes in bulk, and (2) saved filters + multi-select let you change status/assignee on many records at once. Want a quick guide to the import route?\n\nBest,\nSupport Team"),
    dict(id="ref-030", category="onboarding",
         subject="Migrating from a competitor",
         email="We're moving over from another tool and have years of data there. How hard is migration?",
         reply="Hi, and welcome aboard!\n\nMigrations are one of the things we handle a lot, so you're in good hands. Two routes: (1) self-serve - export from your current tool as CSV and use our guided importer, which maps fields for you, or (2) assisted - on Business plans our team will run the migration for you, including a dry-run so you can verify before cutover. Given you have years of data, I'd lean toward the assisted route. If you send a sample export, I'll tell you exactly how it'll map and how long it'll take.\n\nBest,\nSupport Team"),
]

# ---------------------------------------------------------------------------
# HELD-OUT TEST SET  (incoming email  ->  GOLD reply  +  human quality note)
# These emails are NOT in the reference pool. The GOLD reply is what a strong
# agent would send; the human_note explains what makes a reply good here and is
# used to validate that our accuracy metric agrees with human judgement.
# ---------------------------------------------------------------------------
TEST = [
    dict(id="test-001", category="billing",
         subject="Charged twice this month",
         email="I see two identical charges of $199 on my statement this month. I only have one subscription. Please explain.",
         gold_reply="Hi,\n\nThanks for flagging this - a duplicate $199 charge shouldn't happen and I'm sorry for the worry. I've checked your account: there's only one active subscription, and the second charge is a duplicate from a payment retry, not a second plan. I've refunded the extra $199 in full; it'll be back on your card within 5-7 business days and you'll get a confirmation email. Nothing is needed on your end. Do let me know once you see it land.\n\nBest,\nSupport Team",
         human_note="Good = acknowledges the duplicate, confirms only one subscription exists, refunds the extra charge, gives a timeline, reassures no action needed. Must NOT tell the customer it's their fault or ask them to cancel a plan."),
    dict(id="test-002", category="bug",
         subject="Dashboard shows wrong numbers",
         email="Our dashboard total says 4,200 but the underlying report clearly adds up to 4,800. The numbers don't match and my boss is asking. Help!",
         gold_reply="Hi,\n\nThanks for the clear example - a dashboard total that disagrees with the underlying report is exactly the kind of thing we want to catch. The most common cause is a filter or date range on the dashboard tile that isn't applied to the report view (for instance, the tile excluding archived or draft records). Could you check whether the dashboard tile has a filter the report doesn't? If they match and it still disagrees, reply with the tile name and I'll have our team reconcile it directly - a 600-unit gap shouldn't be there. I know your boss is waiting, so I'll prioritise this.\n\nBest,\nSupport Team",
         human_note="Good = takes the discrepancy seriously, gives the most likely cause (filter/date mismatch), asks a targeted question, offers escalation, acknowledges the time pressure. Bad = dismisses it or asks the user to just 'refresh'."),
    dict(id="test-003", category="refund",
         subject="Refund after price increase",
         email="You raised prices without warning and charged the new higher rate. I want a refund of the difference and an explanation.",
         gold_reply="Hi,\n\nI understand the frustration of seeing a higher charge without warning, and I'm sorry the price change wasn't communicated clearly to you. Here's what I can do: I've refunded the difference between the old and new rate for this charge, and I've kept you on your previous rate for the next two billing cycles so nothing changes suddenly while you decide. For transparency, the increase reflects new features added this year; I'm happy to walk through what changed so you can judge the value. The refunded difference will reach your card in 5-7 business days.\n\nBest,\nSupport Team",
         human_note="Good = empathises, refunds the difference, offers a grace period on the old price, explains the increase honestly. Bad = defends the increase without any remedy, or refuses the refund."),
    dict(id="test-004", category="access",
         subject="Can't reset my password",
         email="The password reset email never arrives. I've tried three times and checked spam. I really need in today.",
         gold_reply="Hi,\n\nSorry you're stuck - let's fix this today. If the reset email isn't arriving after three tries and it's not in spam, the usual culprits are (1) the address on file differs slightly from the one you're typing, or (2) your mail server is delaying our messages. To get you in now, I've triggered a fresh reset from my side and, as a backup, generated a one-time secure sign-in link which I'm sending to the verified email on your account. Use whichever arrives first. If neither shows up in five minutes, reply here and I'll verify your identity and set a temporary password with you directly.\n\nBest,\nSupport Team",
         human_note="Good = offers an immediate alternative (manual reset / secure link), diagnoses likely causes, commits to today, has a fallback. Bad = just repeats 'click forgot password' or 'check your spam' with no new help."),
    dict(id="test-005", category="sales",
         subject="Comparing you vs a competitor",
         email="We're deciding between you and CompetitorX. What makes you different, and can you match their price?",
         gold_reply="Hi,\n\nHappy to help you decide - and I'll be straight rather than just bashing the competition. Where teams pick us over CompetitorX is usually (1) faster setup with guided onboarding, (2) automations that don't require a technical admin, and (3) responsive human support (you're talking to a real person right now). On price: tell me the CompetitorX quote you're comparing and your team size, and I'll see what we can do - we have room to be competitive, and there's added value in migration help and onboarding we include. Would a short call to map this to your specific needs help?\n\nBest,\nSupport Team",
         human_note="Good = differentiates honestly without trashing the competitor, engages on price by asking for the quote/size, offers a call. Bad = badmouths the competitor, or flatly refuses to discuss price, or over-promises to beat any price."),
    dict(id="test-006", category="feature_request",
         subject="Need Salesforce integration",
         email="Do you integrate with Salesforce? It's a dealbreaker for us if you don't.",
         gold_reply="Hi,\n\nGreat question, and I appreciate you naming it as a dealbreaker - let me be precise so you can decide with confidence. We offer a native two-way Salesforce integration on the Business plan (sync contacts, activities, and custom fields), plus a Zapier connector and a REST API if you need something bespoke. If you can share the specific objects and direction you need to sync, I'll confirm it's covered before you commit - and I'm happy to set up a live demo against a Salesforce sandbox so you can see it working with your own data.\n\nBest,\nSupport Team",
         human_note="Good = clearly confirms Salesforce is supported, names the plan and capabilities, offers to verify the specific use case and demo. Bad = vague 'yes we integrate with lots of tools' without specifics, or fails to address the dealbreaker directly."),
    dict(id="test-007", category="complaint",
         subject="Your last reply didn't solve anything",
         email="I already contacted you about this bug last week and the 'fix' you suggested didn't work. I'm losing patience.",
         gold_reply="Hi,\n\nI'm sorry - when a suggested fix doesn't work and you have to come back, that's on us, not you, and I understand the lost patience. Let's stop guessing. Rather than send another generic step, I'm escalating this straight to our engineering team with your account attached so they can reproduce it directly. To speed that up, could you reply with what you see when the bug happens (a screenshot or the exact error is perfect) and roughly when it last occurred? I'll personally track this to resolution and keep you updated rather than leaving you to chase.\n\nBest,\nSupport Team",
         human_note="Good = owns the failed fix, stops repeating generic steps, escalates to engineering, asks for concrete repro info, commits to ownership. Bad = suggests the same fix again, blames the user, or gives another canned step without escalation."),
    dict(id="test-008", category="howto",
         subject="How to give a client view-only access",
         email="I want to share a project with an external client but they should only be able to view, not edit anything. Possible?",
         gold_reply="Hi,\n\nYes, that's exactly what guest access is for. Go to the project > Share > Invite, enter your client's email, and set their role to 'Viewer'. Viewers can open and read everything in that project but can't edit, comment-to-change, or see your other projects - so it's safe to share externally. If you'd like them to comment without editing, there's a 'Commenter' role too. The invite is a single project, so they'll never have access to the rest of your workspace. Want me to double-check the permissions once you've sent it?\n\nBest,\nSupport Team",
         human_note="Good = confirms it's possible, gives exact steps, sets role to Viewer, reassures about scope (only that project, no editing), mentions the Commenter alternative. Bad = wrong steps, or fails to reassure about external-sharing safety."),
    dict(id="test-009", category="outage",
         subject="Everything is broken right now",
         email="Nothing is loading. Pages time out. We have a client demo in 30 minutes and I'm panicking.",
         gold_reply="Hi,\n\nI hear the panic and a demo in 30 minutes raises the stakes - let's deal with it head-on. We're currently seeing a partial outage causing timeouts, and our team is actively working to restore service; live updates are at status.ourapp.com. For your demo in the next 30 minutes, two safety nets: (1) if you have a recent export or screenshots, a walkthrough of those keeps the demo moving if the app is still slow, and (2) reply with your account and I'll flag it so you're first to know the instant it's back. I'll personally watch this and message you the moment loading is restored. Good luck with the demo - I've got your back on the status side.",
         human_note="Good = acknowledges the outage honestly, points to status page, gives a practical demo fallback, commits to a personal heads-up, matches the urgency. Bad = pretends nothing is wrong, or offers only 'try again later' with no fallback for the imminent demo."),
    dict(id="test-010", category="integration",
         subject="Webhook payloads changed and broke our code",
         email="You changed the webhook payload format and it silently broke our integration. Why weren't we told?",
         gold_reply="Hi,\n\nYou're right to be upset - an unannounced payload change that breaks your integration is a process failure on our side, and I'm sorry for the silent breakage and the debugging it cost you. Here's the situation: the change was part of a versioned rollout, but the deprecation notice clearly didn't reach you, which we need to fix. Immediately: you can pin to the previous payload version by setting the 'API-Version' header to the prior date, which restores the old format while you migrate on your own timeline. I'm sending you the full changelog of what changed and, separately, checking why your team wasn't on the notification list so this can't recur. Want me to get an engineer on a call to help you migrate cleanly?\n\nBest,\nSupport Team",
         human_note="Good = owns the failure, gives an immediate mitigation (pin the API version), sends the changelog, addresses the notification gap, offers engineering help. Bad = defends the change as 'documented', offers no rollback, or ignores the communication failure."),
    dict(id="test-011", category="cancellation",
         subject="Downgrade instead of cancel?",
         email="We can't justify the current cost but don't want to fully leave. Is there a cheaper plan we could move to?",
         gold_reply="Hi,\n\nI'm really glad you'd rather stay - let's find a fit for your budget instead of losing you. You can move from your current plan to our Starter tier, which keeps the core features most teams rely on at roughly half the cost; you'd lose advanced automations and SSO, but nothing you've created goes away. You can switch anytime from Settings > Billing > Change plan, and the unused portion of your current term is credited toward the cheaper plan. If you tell me which features are must-keeps, I'll confirm Starter covers them before you switch so there are no surprises.\n\nBest,\nSupport Team",
         human_note="Good = welcomes the retention, names a specific cheaper plan and its trade-offs honestly, explains proration, offers to verify must-have features. Bad = pushes them to keep the expensive plan, or hides what they'd lose on the cheaper tier."),
    dict(id="test-012", category="security",
         subject="Was our data part of the breach in the news?",
         email="I saw news about a breach affecting SaaS vendors. Was our data affected? We need to know before informing our customers.",
         gold_reply="Hi,\n\nThis is exactly the right thing to ask, and I want to give you a straight, careful answer rather than a reflexive 'you're fine'. Based on our current security review, your account shows no signs of unauthorised access, and the incident in the news does not involve our systems. I don't want you acting on my word alone for something this serious: I'm looping in our security team to send you an official statement you can share with your customers, including the specific controls (encryption, access logs) relevant to your account. If anything in that review changes, you'll hear from us first and fast. Would a call with our security lead help you brief your customers?\n\nBest,\nSupport Team",
         human_note="Good = takes it seriously, gives a careful factual answer, escalates to security for an official statement, commits to proactive disclosure if anything changes, offers a call. Bad = a flippant 'you're safe' with no verification, or vague non-answers, or unverified reassurance."),
]


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_module(path, ref, test):
    """Embed the pool as an importable Python module.

    Serverless runtimes (e.g. Vercel) reliably bundle *imported* modules but may not
    bundle loose data files. load_pool() falls back to this module so the deployed
    function works with no data files present. Single source of truth stays here.
    """
    header = ('"""Auto-generated by data/build_dataset.py -- do not edit by hand.\n'
              'Embedded copy of the dataset so serverless deploys need no data files."""\n\n')
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("REFERENCE = " + repr(ref) + "\n\n")
        f.write("TEST = " + repr(test) + "\n")


def main():
    ref_path = os.path.join(HERE, "emails.jsonl")
    test_path = os.path.join(HERE, "test_set.jsonl")
    module_path = os.path.join(HERE, "..", "src", "_pool_data.py")
    write_jsonl(ref_path, REFERENCE)
    write_jsonl(test_path, TEST)
    write_module(module_path, REFERENCE, TEST)
    print(f"Wrote {len(REFERENCE)} reference pairs -> {ref_path}")
    print(f"Wrote {len(TEST)} held-out test cases -> {test_path}")
    print(f"Wrote embedded module -> {os.path.normpath(module_path)}")
    cats = {}
    for r in REFERENCE + TEST:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    print("Category coverage:", dict(sorted(cats.items(), key=lambda x: -x[1])))


if __name__ == "__main__":
    main()
