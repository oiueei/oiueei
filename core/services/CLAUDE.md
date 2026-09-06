# Services Documentation

Business logic and side effects extracted from views into `core/services/`. Keeps views thin and logic reusable.

---

## Modules

### `booking_service.py` — Booking Business Logic

Handles state transitions for `BookingPeriod` and `Thing` models as an atomic unit.

#### Functions

| Function | Input | Behaviour |
|----------|-------|-----------|
| `cancel_booking(booking)` | `BookingPeriod` instance | Calls `booking.cancel()`. For single-use types (GIFT, SELL), restores thing to `ACTIVE`. Clears the owner's request notification (see below). Returns thing. |
| `accept_booking(booking)` | `BookingPeriod` instance | Calls `booking.accept()`. For single-use types, sets thing to `INACTIVE` and adds requester to `deal` M2M. Creates a `ThingTransfer` record (from owner to requester, lent_date = start_date or today). Returns thing. |
| `reject_booking(booking)` | `BookingPeriod` instance | Calls `booking.reject()`. For single-use types, restores thing to `ACTIVE`. Returns thing. |
| `compute_availability(blocked_periods, today=None, horizon_days=90, allowed_weekdays=None, durations=None)` | iterable of PENDING/ACCEPTED bookings (objects with `start_date`/`end_date`), plus the governing collection's rental rules | **Pure, side-effect-free.** Returns `(available_today: bool, next_available: date|None)` for a date-based thing. Walks forward from `today` (default `timezone.localdate()`), treating each booking `[s, e]` as blocking pickup on `[s, e)` — the return day `e` is free for the next pickup (matching `BookingPeriod.has_overlap()`'s strict overlap / back-to-back handovers) — and returns the first day a pickup could start, or `(False, None)` when no day within `horizon_days` qualifies. Null-dated rows are skipped. **`allowed_weekdays` (0=Mon…6=Sun) + `durations` (days) are the rental rules (#7)**: a day counts only if its weekday is allowed, it is free for pickup, and — when the collection fixes the lengths — at least one length both lands its return day on an allowed weekday and fits without a strict overlap. This mirrors `frontend/src/utils/rental.js::isPickupDisabled` exactly, so the card and the date picker can't contradict each other (the bug: a Wednesdays-only collection with next Wednesday booked reported "available today" on a Monday). Either rule may be passed alone; with neither the walk is byte-identical to the unrestricted one. Consumed by `Thing.availability_window()` → the `available_today`/`next_available` serializer fields. |

##### Reservation requests

These own the **create** side (formerly the `ThingRequestView._handle_*` methods). Each performs the locked create + status transition, then fans out the request emails + in-app notification + `HOLD_REQUESTED` event via the shared `send_*_request_notifications()` helpers. Rule violations raise `BookingRequestError(message, status_code)`; `ThingRequestView` catches it and returns `{"error": message}` with that status (default 400; 409 for a date overlap). Serializer validation stays in the view.

| Function | Input | Behaviour |
|----------|-------|-----------|
| `request_date_based_booking(thing, requester, owner_email, start_date, end_date, rental_collection=None)` | LEND/RENT | Enforces `rental_collection.rental_violation()` (400) and `BookingPeriod.has_overlap()` (409), then creates the dated booking. Returns the booking. |
| `request_standard_booking(thing, requester, owner_email)` | GIFT/SELL | Re-checks availability + duplicate under the lock; creates the booking and flips a non-endless thing to `TAKEN`. Returns the booking. |
| `resolve_rental_collection(thing, collection_code=None)` | LEND/RENT | Picks the collection whose rental rules apply (the passed `collection_code`, else the thing's first collection with rules, else `None`). |
| `resolve_request_collection(thing, collection_code=None)` | any | Picks the collection a request was **made through**, for the notification payload. The request's own context wins (`collection_code`, sent by the SPA from the card/detail page it was showing); without it — the standalone `/things/:code` page — it approximates: the rental-rules collection, else the thing's first ACTIVE one, else `None`. A thing can live in several collections, so the guess is what decides where the owner's notification shows up; the SPA passing the code is what makes it exact. |
| `send_booking_request_notifications(...)` | — | RSVP accept/reject pair → owner request email + requester confirmation + owner in-app notification + `HOLD_REQUESTED` event. |

##### The request notification's lifecycle

`BOOKING_REQUESTED` is a **question put to the owner** — accept or reject? — so it must not outlive its answer. `_clear_request_notifications(booking)` deletes it (`user=booking.owner_code`, matched by `payload__booking_code`) and is called from every path that settles a request:

- `finalize_booking_decision()` on success — **both** accept and reject, and it is the single convergence point of the email/RSVP path (`VerifyLinkView`) and the in-app path (`BookingActionView`), so one call covers both. (The reported bug: accepting from the email left the notification sitting there.)
- `cancel_booking()` — the requester withdrew; the owner has nothing left to decide.

The payload keys that make this work (`booking_code`, `thing_code`, `collection_code`) are documented under [`InAppNotification`](../models/CLAUDE.md#inappnotification). Notifications created before those keys existed simply never match the filter and stay until dismissed by hand.

#### Patterns

- **Snapshots, not lookups**: both `request_*` functions copy the thing's `type` **and** its `deposit` onto the booking (`thing_type`, `deposit_amount`). The reservation is a record of what was agreed, so editing the listing afterwards cannot rewrite it — and since `accept_booking` always attaches the booking to the `ThingTransfer` it creates, the journey reads the agreed amount through `transfer.booking` rather than keeping a second copy that could disagree.
- **Atomic transactions**: Every function wraps its work in `transaction.atomic()` to ensure `BookingPeriod` and `Thing` are updated together or not at all.
- **Row-level locking**: Uses `Thing.objects.select_for_update()` to prevent race conditions when two concurrent requests try to modify the same thing's status.
- **Single-use type check**: Only GIFT and SELL things (`SINGLE_USE_TYPES` from `core.models.booking`) change thing status on accept/reject/cancel. Date-based types (LEND, RENT) leave thing status unchanged because multiple bookings can coexist.
- **`is_endless` guard**: For GIFT/SELL things where `thing.is_endless=True`, all status changes (TAKEN on request, INACTIVE on accept, ACTIVE on reject/cancel) and ThingTransfer creation are skipped. The thing remains ACTIVE at all times and accumulates multiple simultaneous PENDING bookings from different users. `expire_old_pending()` also excludes endless things from the TAKEN→ACTIVE restore.
- **Thin view, service raises**: the reservation-request business logic lives entirely in the `request_*` functions. `ThingRequestView` only does HTTP-layer work — shared guards, serializer parsing, response shaping — and translates `BookingRequestError` into the `{"error": ...}` response. Callers outside DRF (management commands, future flows) can request bookings without touching the view.

---

### `email_service.py` — Centralised Email Sending

All outbound emails are composed and sent from this module. Views call these functions rather than constructing emails inline.

#### Categories and notification preferences

Every email belongs to one of three categories. Each function routes through the internal `_send()` helper, which checks the recipient's preferences (looked up by email on the `User` model) before dispatching.

| Category | Constant | User flag | Scope |
|----------|----------|-----------|-------|
| **Cat. 1 — Mandatory** | `CATEGORY_MANDATORY` | (ignored — always sent) | `send_magic_link_email`, `send_collection_invite_email`, `send_collection_welcome_doc_email`, `send_collection_revoke_email`, `send_account_delete_email`, `send_inactivity_warning_email` |
| **Cat. 2 — Activity** | `CATEGORY_ACTIVITY` | `User.notify_activity` | `send_booking_request_email`, `send_booking_decision_email`, `send_booking_confirmation_email`, `send_invite_rejected_email`, `send_faq_question_email`, `send_faq_answer_email`, `send_faq_hide_email`, `send_thing_reported_email`, `send_return_reminder_email`, `send_return_due_email`, `send_broadcast_email`, `send_invitation_proposal_email`, `send_proposal_declined_email` |
| **Cat. 3 — News** | `CATEGORY_NEWS` | `User.notify_news` **and** `Collection.digest_muted` | `send_digest_email` |

**Both flags default to ON, and Cat. 3 has a second, narrower switch.** `notify_news` used to default to `False`, which — combined with `Collection.digest_frequency` defaulting to `NONE` — meant the digest reached almost nobody: an owner had to find a setting buried in an accordion *and* every reader had to have opted in to a toggle labelled "optional". The 2026-08 design round turned both on and added the control that makes it honest rather than a pre-ticked opt-in (DESIGN §6): **`Collection.digest_muted`**, a per-group mute.

- A member silences one group without losing anything else — the booking, question and reminder emails are Cat. 2 and untouched. There is no "all or nothing" any more.
- Two ways out, both one click: the toggle in the collection hero (`is_digest_muted` on `CollectionSerializer`, `POST /collections/{code}/digest/`) and the link in the footer of the digest itself (`POST /digest/mute/{token}/`, no login — see the signed tokens below).
- **The mute is scoped to CATEGORY_NEWS only.** `_should_send`/`_filter_recipients` take a `collection` and consult it for news alone, so silencing a chatty group never suppresses the notice that your own hold there was confirmed.
- If the mute is ever removed, `notify_news` has to go back to defaulting `False` — pinned by `test_new_user_starts_subscribed_to_both_categories`.

- **Lookup fallback**: if no `User` matches the recipient email (e.g. a not-yet-registered invitee), `_should_send` returns `True` — all emails reach non-users by default.
- **Multi-recipient**: functions that take `emails=[...]` (digest, broadcast) use `_filter_recipients()` for a bulk query that drops opted-out addresses before iterating. `_send_per_language` also accepts an **`extra_footer(user, lang)`** hook for a line that must be built *per recipient* rather than per language — the digest's mute link carries a token signed for one user, so it cannot join the language-cached body.
- **Preferences footer**: Cat. 2 and Cat. 3 emails get an auto-appended footer with a link to `/me/notifications/{token}` (see below). Cat. 1 skips it — nothing to manage. **Separately, every category including Cat. 1 gets a legal footer** — see the art. 14 note below, which is not preference-gated because it is a disclosure duty, not an opt-out.
- **Viral CTA**: every send except the operator's own ops mail (which passes `include_viral=False` — a report, not growth copy) prepends one random growth blurb from the per-language `VIRAL_LINES` catalogue (`email_texts/{lang}.py`, read via `viral_lines()`) above the footer — the CTA is always the plain `{frontend_base}/collections/new` link, never tracking-wrapped (DESIGN §9). It is suppressed for recipients who already own ≥1 collection (the `_owns_collection` flag is folded into the existing `_lookup_user`/`_lookup_users` query via an `Exists` annotation — no extra round-trip), and for an empty list. So the bottom order is always: body → viral line (when shown) → preferences footer (when present). **`send_magic_link_email` carries it too since S2** (CA decided: the magic link is the one email every user gets, so suppressing growth copy there starved the loop) — this makes `_send()` do one extra `User` lookup for magic-link sends it used to skip, but both its callers only ever reach it after the recipient is already resolved (`RequestLinkView` for a confirmed-registered address, `JoinView` after `get_or_create`), so the lookup adds no new registered/unregistered timing signal (L10 stays about language resolution, not this gate — see below).

#### The legal footer (art. 14 GDPR) — every email, no exceptions

`_render_email()` (the shared HTML renderer every sender's `html = _render_email(...)` goes through) always injects a link to `{frontend_base}/legal`, rendered by `core/templates/email/layout.html` after the last content block. Unlike the preferences footer above, this one is **not gated by category** — an unsubscribe link is a courtesy the recipient can decline; a controller's identity and the terms under which their data is processed are not. `lang` (the same value senders already thread through `T`/`L`) picks the label's language via the `footer_legal` key; a caller that omits it falls back to the deployment default, same as `T()` everywhere else.

**`send_collection_invite_email` carries a second, specific disclosure** (`invite_source_note`, all three catalogues): the invitee's address didn't come from them, it came from whoever invited them, which is exactly the case art. 14 exists for. The sentence says where the address came from, what it's used for, and that declining or ignoring the email ends it — appended to **both** the HTML blocks and the plain body, since this is the one email in the catalogue sent to somebody who never asked OIUEEI for anything directly.

**`<html lang="...">` itself follows the same resolved language** (A4, 2026-08): `_render_email` computes `lang or EMAIL_LANGUAGE` once and passes it to the template as `lang`, so a screen reader pronounces the body in the language it's actually written in rather than whatever the browser/client's own default assumes. Every email already speaks a specific, known language by the time it's composed (`resolve_email_language`), so this was never genuinely unknown — only unstated.

#### Email language — the hierarchy (`EMAIL_LANGUAGE` + `Collection.language` + `User.language`)

Which language an email speaks is decided per **recipient**, by three levels, weakest to strongest:

1. **Deployment default** — `EMAIL_LANGUAGE` (env var, default `en`; the standalone repo stays English, www.oiueei.com sets `es`).
2. **The collection's language** — `Collection.language`, the owner's choice for their group.
3. **The recipient's own preference** — `User.language`, which always wins.

Blank means "inherit", so a level only speaks when it was actually set — existing rows keep the old per-deployment behaviour with no data migration. `resolve_email_language(user=None, collection=None)` implements it; `_recipient(email, collection=None)` resolves the recipient's `User` **once** and returns `(user, lang)`, handing the user to `_send()` so the preference check, footer link and viral gate don't re-query it.

Senders **shadow the module-level `T` with a language-bound one** (`T = _texts(lang)`), so every `T("key")` in the body speaks the recipient's language without threading the argument through each call. `_send(..., lang=)` follows it for the footer and viral line, so the whole message is in one language.

Senders bind **`L = _local(lang)`** next to `T` and pass every **owner-written** value through it — a collection headline, a thing headline (O6: either of them may carry one text per language as inline JSON). So the resolution happens exactly where the recipient's language is already known, and a Catalan member reads "…a 'Les coses de mama'…" while their Spanish neighbour reads "…a 'Las cosas de mamá'…" from the same row. A plain headline — nearly all of them — comes back untouched. The operator-facing senders carry aggregate numbers, not owner content.

- **Collection-scoped emails pass their collection**: invite (+ bulk), invite-rejected, revoke, welcome-doc, broadcast, digest, and the join magic link.
- **Thing-scoped 1:1 emails pass only the recipient** (bookings, FAQs, reminders, reports): there is no group to speak for, so it's their preference or the deployment default — never a guessed collection.
- **Bulk sends compose per language**: `_send_per_language(emails, category, compose, collection=...)` drops opt-outs, bulk-resolves the users in one query, and calls `compose(lang)` once per *distinct* language among the recipients — so one digest to a bilingual group leaves in two languages while a 50-member single-language group still composes once.
- **The magic link is the exception**: its caller (`core/views/auth.py::_send_magic_link`) resolves the language and passes it in, because that sender must not look the recipient up — `request-link` only sends for a registered address, so a DB round trip would make "registered" responses measurably slower and become an email-enumeration timing oracle (L10).
- **`JoinView` accepts an optional `language`** in the body and stores it on **newly created** users only, so a joiner's very first magic link already speaks their UI language; an existing user's saved preference is never overwritten by the browser they arrived from.

Every user-facing string lives in a per-language catalogue — `email_texts/en.py` (the reference + universal fallback), `es.py`, `ca.py` — as flat `TEXTS` dicts of `str.format` templates, mirroring the `seed_data/{lang}.py` pattern. `T(key, lang=None)` falls back to English for an unknown language or a missing key; without `lang` it reads `settings.EMAIL_LANGUAGE` on every call (so `override_settings` works in tests). `test_email_language.py` pins the en default, the es/ca deployments, the fallback, and en↔{es,ca} catalogue/placeholder/viral-line parity (the email analogue of `i18nParity.test.js`); `test_email_hierarchy.py` pins the resolution matrix and the per-recipient bulk sends. To add a language: copy `en.py` → `{lang}.py`, translate only the values (keep keys + `{placeholders}`), and add the code to `Language` in `core/models/language.py` so owners and users can pick it. The operator-facing senders (the capacity alarm) carry data, not copy, and are not part of the catalogue.

#### Signed tokens for unauthenticated preference editing

- `make_notifications_token(user_code)` — returns a `TimestampSigner`-signed string (salt `notifications-prefs`, TTL 1 year) scoped to notification preferences editing.
- `verify_notifications_token(token)` — returns the user_code on success, `None` on failure.
- `make_digest_mute_token(user, collection)` / `verify_digest_mute_token(token)` — the digest footer's one-click unsubscribe. Signs `{user_code}:{collection_code}` under its **own salt** (`digest-mute`), so it can't be swapped for a preferences token either way. Same 1-year TTL, same reasoning. Blast radius: one row in one M2M, undoable by the member from the collection page. Consumed by `DigestMuteByTokenView` (`POST /api/v1/digest/mute/{token}/`) — **POST, never GET**, so a mail client's link scanner or a prefetch can't unsubscribe somebody; the SPA page at `/digest/mute/:token` fires it from JS, which a scanner never runs.
- Used by `NotificationsByTokenView` at `GET/PATCH /api/v1/notifications/token/<token>/` so recipients can toggle preferences via the email footer without logging in.

**The 1-year TTL is deliberate, and was reviewed as such** (2026-08 security round — don't re-flag it without reading `_PREFS_TOKEN_MAX_AGE`). It looks like a token that should expire fast: it rides in a URL path, in the footer of every Cat. 2 / Cat. 3 email, and authenticates without a login. But stolen it can flip exactly two booleans — nothing to read, nothing to spend — while expired it breaks the link somebody clicks *to stop receiving email from us*. That is the unsubscribe link whatever the page calls it, and a dead one turns withdrawing consent into "log in, find the profile editor, scroll to preferences". The long TTL is the user-protective side of that trade, not the lax one. Rotating `SECRET_KEY` invalidates every outstanding token at once, which is the revocation path that matters.



#### Functions

| Function | Trigger | Recipient |
|----------|---------|-----------|
| `send_magic_link_email(email, magic_link, collection_headline=None)` | User requests login, or joins a collection | The user (subject names the joined collection when `collection_headline` is passed; generic welcome subject otherwise) |
| `send_booking_request_email(requester, thing, booking, owner_email, accept_link, reject_link)` | Guest submits a hold request | Thing owner |
| `send_booking_confirmation_email(requester, thing, booking)` | Guest submits a hold request | Requester (confirmation of what was requested) |
| `send_booking_decision_email(booking, thing, accepted)` | Owner accepts or rejects a booking | Requester |
| `send_collection_invite_email(inviter_name, collection_headline, email, accept_link, reject_link)` | Owner invites a user to a collection | Invitee |
| `send_invite_rejected_email(invitee_name, collection_headline, owner_email)` | Invitee declines a collection invitation | Collection owner |
| `send_collection_welcome_doc_email(collection_headline, doc_url, email)` | A user becomes a member of a collection **for the first time** (any join path — invite, share token, public-collection join) and the owner has set a welcome PDF | The new member. The PDF travels as a **link** to the bucket, never an attachment. Membership lifecycle ⇒ Cat. 1: a member who never sees the rules can't follow them |
| `send_collection_revoke_email(owner_name, collection_headline, email)` | Owner removes a user from a collection | Revoked user |
| `send_account_delete_email(user, delete_link)` | User requests account deletion (`AccountDeleteRequestView`) | The account owner. States what is deleted and what stays anonymised; the link previews on GET and commits on POST (24h, single-use). `include_viral=False` — a growth CTA on an erasure email would be grotesque |
| `send_inactivity_warning_email(user, months, days, will_delete=True)` | `purge_expired_data`, before an unused account is erased for retention | The account owner. Mandatory for the same reason as the erasure confirmation — it is about whether the account continues to exist — and `include_viral=False` for the same one. **Two bodies:** the default says the account goes in `days` days and that signing in once keeps it; `will_delete=False` is the version for an account that owns a group other people are using, which is never auto-deleted and therefore must not be told that it will be. Neither nags — the first ends "if you would rather it went, you don't have to do anything at all" (DESIGN §6: an inactive account is somebody who already left) |
| `send_contact_email(name, email, message, kind)` | Anonymous-capable contact/collaborate form (`ContactView`; `kind` picks the subject — support/collab) | The operator (`CONTACT_EMAIL` env, default `DEFAULT_FROM_EMAIL`), with the sender as `Reply-To`. Operator mail: mandatory category, `include_viral=False`, deployment language |
| `send_faq_question_email(questioner_name, thing, question, owner_email)` | Guest asks a question on a thing | Thing owner |
| `send_faq_answer_email(owner_name, thing, question, answer, questioner_email)` | Owner answers a FAQ | Questioner (the email links the thing — label is the thing headline, via `_thing_url`) |
| `send_faq_hide_email(owner_name, thing_headline, question, questioner_email)` | Owner hides a FAQ | Questioner |
| `send_thing_reported_email(thing, owner_email)` | A member reports a thing | Thing owner (**anonymous** — the reporter is never named; body links to the listing so they can review it) |
| `send_broadcast_email(owner_name, owner_email, collection_headline, collection_code, message, emails)` | Owner sends broadcast to collection | All collection invitees (individually, Reply-To owner + a link to the collection). Subject auto-generated as `Hey! {collection}`. |
| `send_digest_email(collection_headline, collection_code, thing_headlines, emails)` | Daily command (weekly/monthly) | All collection invitees (individually) |
| `send_return_reminder_email(requester_name, thing_headline, end_date, owner_email)` | Daily command (end_date = tomorrow) | Thing owner — "somebody's hold ends tomorrow"; nothing is asked of them |
| `send_return_due_email(owner_name, thing_headline, end_date, requester_email, thing_url=None)` | Daily command (end_date = tomorrow), **alongside** the owner's | The **borrower** — "tomorrow you take it back", naming the owner they owe it to. The half that was missing until the 2026-08 design round: only the owner was told a loan was ending, so the one person with something to do heard nothing. `send_reminders` fans out to both and swallows a failure per recipient, so one broken send costs neither the other side nor the rest of the run |

#### Patterns

- **XSS prevention**: All user-provided content is escaped with `django.utils.html.escape()` before being inserted into HTML email bodies. Plain text versions use raw values (safe in plain text context).
- **Nobody is named to a stranger by their address (L2)**: `User.display_name` falls back to the email, and `name` is empty for **every** account made by `get_or_create(email=…)` — everyone who arrived by magic link or invitation and never filled in a profile. So the fallback is the ordinary state of a new member, not an exotic one. Callers pass the **bare `name`** and `_member_name(name, lang)` substitutes the localized `a_member` ("A member" / "Un miembro" / "Un membre") where the copy interpolates it mid-sentence; where the name has a line to itself the caller drops the line instead (`proposer_name`). `display_name` survives only where the reader already holds the address — a collection owner (`owner_member_rows`) or a thing owner reading a request (`BookingPeriodSerializer.requester_email`) — plus the operator's own ops mail. The in-app payloads follow the same rule and the SPA fills the gap with `common.aMember`. Pinned by `core/tests/integration/test_member_name_privacy.py` and `test/inboxNotifications.test.jsx`.
- **Dual format**: Every email is an `EmailMultiAlternatives` with a plain-text body plus an HTML alternative (`attach_alternative(html, "text/html")`) for clients that support it.
- **Inline logo (CID, no remote fetch)**: `_send()` attaches `frontend/public/oiueei-logo.png` as an inline `MIMEImage` (`Content-ID: <oiueei-logo>`, `Content-Disposition: inline`), read once via `_logo_bytes()` (`functools.lru_cache`). `layout.html` renders `<img src="cid:oiueei-logo" ...>` above the body blocks — `_render_email()` only emits the tag when `_logo_bytes()` found the file, so a missing asset degrades to "no logo" (never a broken image, never a failed send). A remotely-hosted logo would be a de-facto open beacon (DESIGN.md §9), so the PNG travels inside the email instead. When the logo is present, `_send()` sets `mixed_subtype = "related"` before attaching it, so the image is a CID reference inside `multipart/related[multipart/alternative[plain, html], image]` rather than a `multipart/mixed` sibling — Apple Mail otherwise renders the 30px inline logo *and* a full-size copy with a paperclip (S1).
- **Action links**: Booking and invitation emails include accept/reject links (RSVP-based URLs generated by the calling view). FAQ question emails include a direct link to the thing page, and so does the booking **decision** email — that one reaches the requester at the end of their flow, so it has to lead somewhere; it reuses `view_thing_cta` rather than adding a fourth way to say "view the listing". The decision email also carries **one subject per outcome** (`decision_subject_confirmed` / `decision_subject_cancelled`): a single subject for both an accepted and a refused hold cannot be read from an inbox.
- **`from_email=None`**: Uses Django's `DEFAULT_FROM_EMAIL` setting.
- **Booking email variants**: `send_booking_request_email` and `send_booking_decision_email` adapt their content based on booking type — date-based (start/end) or simple (no extra fields).
- **Per-type action nouns**: the three generic booking emails (request/confirmation/decision) interpolate `{action}` from `_action_noun(thing)` (`T(f"action_noun_{thing.type}")`) so the wording mirrors the frontend's per-type vocabulary — a SELL request reads "purchase request" / "solicitud de compra", a LEND request "loan request" / "solicitud de préstamo", etc. Four nouns live in each catalogue (`action_noun_{GIFT,SELL,LEND,RENT}_THING`) — one per type, and a missing key would be a `KeyError` mid-decision, after the booking already committed (guarded by `test_every_bookable_type_has_an_action_noun`). **Catalan caveat**: in `ca.py` the noun values carry the preposition (`"de compra"`) and the templates read `sol·licitud {action}` — Catalan elides "de" before a vowel, so the en/es template shape (`de {action}`) can't work there; a new type starting with one needs `d'` in the value. The owner confirm/cancel button verbs (`hold_confirm_cta`/`hold_cancel_cta`) stay generic by design.
- **Reply-To header**: `send_broadcast_email()` uses `EmailMultiAlternatives` with `reply_to` so invitees can respond directly to the collection owner (routed through `_send(..., reply_to=[owner_email])`). The visible body links to the collection (`/collections/{code}`) — the object that originated the message — rather than promising an email reply. **The owner is told before they send**: the broadcast box's helper line says that whoever receives it can reply directly and will see their address (`broadcast.replyToNotice`). It is the one place in the product where a member learns an address the API takes care never to serve them, and it is the owner's own — so the answer is disclosure, not a switch: dropping the header would turn a group message into a megaphone whose replies land on a noreply.
- **Digest emails**: `send_digest_email()` lists new thing headlines in both plain text (bulleted) and HTML (`<ul>/<li>`) formats.
- **Direct collection links**: `send_digest_email()` links straight to `{frontend_base}/collections/{code}`. Per DESIGN.md §9 we do not track email engagement — links are never wrapped in a redirect or tracking pixel.
- **Preference pipeline**: every send goes through `_send()` → `_should_send()` + `_with_viral_line()` + `_with_footer()`. Never build an `EmailMultiAlternatives` directly from outside this module — the preference check, viral CTA, footer and logo attachment would all be bypassed.

---

### `invitation_service.py` — Sending an invitation, and the member-proposal flow

**`deliver_invitation(collection, email, inviter_name, quota_user_code=None, proposer_name=None)`** is the single place an invitation actually goes out: the `get_or_create`, the RSVP pair, the email and the daily quota. Both callers reach it — the owner inviting directly (`CollectionInviteView`) and an owner approving a member's recommendation — so an approved proposal is indistinguishable from an owner's own invite. Two paths would drift, and the one used less often is the one that would rot. (The bulk-invite endpoint keeps its own batched fan-out: it creates RSVPs in a batch and mails off the request thread, a different shape.)

The **daily invitation-email quota** helpers live here too (`_invite_quota_left`, `_consume_invite_quota`) — they moved out of the views when both senders ended up here, since a service reaching back into a view for them was a layering inversion. The views import them.

| Function | Behaviour |
|---|---|
| `create_proposal(collection, proposer, email, note="")` | Records the suggestion, mints the owner's approve/reject RSVP pair, writes their in-app notification and emails them. **Nothing reaches the proposed address** — no `User` row, no email. If the answer turns out to be no, that person must never learn they were suggested. |
| `proposal_approval_blocked(proposal)` | `(message, http_status)` if this approval cannot be delivered — the owner's daily quota (429) or the collection's member ceiling (400) — else `None`. **Shared by the owner's two routes**, the in-app POST and the emailed approve link, which used to differ: the link approved unconditionally, making `INVITE_EMAILS_PER_DAY` walkable one recommendation at a time. Someone already in the group is excluded from the ceiling check — an approval that adds nobody must not be refused. |
| `approve_proposal(proposal)` | Delivers the real invitation via `deliver_invitation`, charged to the **owner's** quota (the mail leaves their group under the deployment's domain) and naming the proposer in the body — the invitee almost certainly knows *them*, not the owner. Bare `name`, never `display_name`: the fallback is the email address and this message goes to a third party (L2). |
| `reject_proposal(proposal)` | Marks it rejected and tells the **proposer** — in-app and by email, **with no reason**. Silence would leave them waiting and asking again; a reason would put words in the owner's mouth about rules that are not the product's business. The proposed person is never contacted. |

---

### `join_quota.py` — The daily cap on the door that needs no account

`POST /auth/join/` mails a magic link to whatever address is typed into it, and **neither door that reaches it is a secret**: a PUBLIC collection's `collection_code` is printed in that collection's own URL, and a share token exists to be passed around. So without a cap, anyone may ask a deployment to send mail to anyone — a relay pointed at the operator's own sending domain, ending in complaints against it and genuine magic links landing in spam.

The view's own rate limits never closed this and were not meant to: they cap how often **one IP** asks (5/min) and how often **one victim** is mailed (5/hour), which says nothing about a hundred IPs mailing a hundred different strangers once each. `INVITE_EMAILS_PER_DAY` did not either — it counts what an *account* sends through the owner's invite routes, and this is the one door with no account behind it.

| Function | Behaviour |
|---|---|
| `join_quota_exhausted(collection_code)` | Whether this collection has already taken today's joins. `False` when the cap is off. Checked in `JoinView` **after** the target resolves and **before** anything is created, so a refusal leaves no `User`, no RSVP and no mail. |
| `consume_join_quota(collection_code)` | Records one join against today's allowance. Called after the send is dispatched, so a join that failed earlier costs the collection nothing. |

**Keyed per collection, deliberately.** Per IP is what already failed. Per *deployment* would be worse than nothing here: one abused collection would deny every other collection its joins, handing the attacker a denial of service against the whole instance in the name of stopping a relay. Per collection, abusing a group's public code costs that group its own day.

**Off unless the operator sets `COLLECTION_JOINS_PER_DAY`**, like every other abuse guard — and for the usual reason plus one of its own: a share link pasted into a group chat can legitimately bring in two hundred people in an evening, which upstream has no business calling abuse. It follows `RATELIMIT_ENABLE` (the same switch as the invitation quota, so an operator turning limits off does not have to find two places to do it), and shares the DatabaseCache read-then-set non-atomicity note (I7) — a burst can slip a few past the line, which is the right trade for coarse reputation protection.

A refusal returns the endpoint's **unified response** and writes a `security` warning. It cannot say why: "over its limit" would confirm that the token or code names a real, joinable collection, which is exactly what that response exists to withhold. The operator is told instead — the same shape as the capacity alarms, where the tripwire reports to whoever set it and never to whoever tripped it.

Each join sends one magic link, and a **first** join also sends the collection's welcome document when the owner set one, so the mail this permits is at most twice the configured number. It caps joins because that is the event worth counting; the emails follow from it.

---

### `creator_policy.py` — Who May Create What, On This Deployment

The one place a deployment says whether an account is enough to open a collection in either mode and offer a thing under any of the four verbs. Upstream the answer is **yes, to everyone, always** — `OpenCreatorPolicy`, the default of the `CREATOR_POLICY` setting — so a standalone checkout has no gate and behaves exactly as it did before this module existed. A deployment with a narrower rule (only the board opens COMMUNITY collections; lending is vetted first) points the setting at its own subclass instead of editing the serializers, and nothing about that rule needs to live in this repository.

It answers only *may this person bring such a thing into existence here at all*. It is **not** object-level permission (`IsCollectionOwner`), and **not** the owner's per-collection `allowed_thing_types` allowlist (`core.views._helpers.type_validity_error`).

| Function / class | Behaviour |
|---|---|
| `Capabilities` | Frozen dataclass: `collection_modes`, `thing_types`, `request_url`. `as_dict()` is the JSON shape served on `GET /auth/me/` (lists, not tuples). `request_url` is where to go and ask; `None` means there is nowhere, which is the standalone's answer because there is nothing to ask for. |
| `CreatorPolicy` | Base class. A subclass overrides **`capabilities(user)`** and nothing else; `allows_collection_mode()` / `allows_thing_type()` are derived from it, so a policy cannot allow something it does not advertise. Instances are cached and shared across requests — subclasses must be **stateless**. |
| `OpenCreatorPolicy` | The default. Every mode, every verb, no request URL. Its two lists come from `Collection.Mode.values` / `Thing.Type.values` rather than being spelled out, so a verb added to the model is available the day it is added. |
| `get_creator_policy()` | The configured policy, instantiated once **per dotted path** (`lru_cache` under the setting lookup, not over it — a module global would pin whichever policy the process loaded first, and `override_settings` in a test would silently not apply). |
| `capabilities_for(user)` | This deployment's answer for one user — the single way to ask, used by both denial helpers and by `MeView`. **Not cached**: a caller in a loop must hoist it and pass it down (see `ThingBulkCreateView`). |
| `collection_mode_denial(user, mode, capabilities=None)` | The message explaining why this deployment refuses that mode, else `None`. |
| `thing_type_denial(user, thing_type, capabilities=None)` | The same for a verb, in prose (`"a lend thing"`, not `LEND_THING`) — the text reaches an API client as the 403 body. Answers the **personal** question only. |
| `community_contribution_types(collection, user)` | The set of thing types `user` may add to `collection` **despite** `thing_type_denial()` — empty unless they are an invited member of a COMMUNITY collection whose owner has explicitly named the type in `allowed_thing_types`. See "Initiating vs. contributing" below. Empty for a non-member, the owner, a PROPRIETARY collection, an empty allowlist, and `None`. |

**A policy is consulted exactly once per decision.** Both helpers resolve `capabilities()` a single time and read the allowed list *and* the `request_url` off it — the refusal needs both, and asking twice used to make every denial cost double. Both also accept an already-resolved `capabilities=`, which is how `ThingBulkCreateView` judges up to 100 CSV rows with one evaluation instead of 100: the verb is per row, whether this deployment offers it is not. `CreatorPolicy` requires subclasses to be **stateless, not cheap** — the policies this setting exists for are the ones that go and look something up — so the call count is part of the contract, pinned by `TestThePolicyIsConsultedOnce`.

**The module stays free of HTTP**, like `booking_service`: it returns a message and the call site raises the 403. The message carries the request URL when the policy has one, because the API is usable without the SPA and a client that only ever sees the refusal would never learn that asking is possible.

#### Where it is enforced (five doors, not two)

| Call site | Refuses |
|---|---|
| `CollectionViewSet.perform_create` | The mode, **including the PROPRIETARY default** when the body names none |
| `CollectionViewSet.perform_update` | Switching an existing collection **into** a withheld mode |
| `ThingViewSet.perform_create` | The verb, unless it is a COMMUNITY contribution (below). The collection is resolved first now, but a nonexistent or un-addable one still falls through to the **same 403** as no collection at all — the verb refusal never turns on which collection was named |
| `ThingViewSet.perform_update` | Moving a thing **into** a withheld verb — unless every collection it sits in is a COMMUNITY contribution that allows the new one |
| `ThingBulkCreateView` | The verb of each CSV row — as a **row error (400)**, like the collection's own allowlist, since that endpoint's contract is that one response names every bad row. The COMMUNITY exception is resolved once for the whole batch |

**Initiating vs. contributing.** A `CreatorPolicy` gates *initiating* — opening a collection, or offering a verb under your own name or into your own collection. It does **not** gate a member adding a thing to a COMMUNITY collection they were invited to, of a type that group's owner has explicitly put in `allowed_thing_types`. That owner is the vetted party (a deployment narrow enough to hold COMMUNITY creation behind a request vetted *them*), and the allowlist is them opening their group to that verb. `community_contribution_types()` is the single definition; the three thing-creation doors gate on `thing_type in community_contribution_types(...)` before raising. An **empty** allowlist is not "every type" here — it means the owner made no choice, so the deployment default still governs what an un-vetted member may bring in. Upstream (`OpenCreatorPolicy`) the whole branch is dead: every verb is allowed, so `thing_type_denial()` returns `None` first. Pinned by `test_creator_policy_gate.py`.

**The two edit paths only judge a change.** A collection already in a mode (or a thing already under a verb) the policy has since stopped handing out stays fully editable by its owner: the gate is on bringing that state into existence, never on living in it, so narrowing a deployment cannot freeze what people already own.

**`GET /auth/me/` serves the same `capabilities()`** the doors refuse with (see `MeView`), which is what keeps the UI from offering a control that 403s when pressed.

---

### `account_service.py` — Account Erasure (Right to Be Forgotten)

One function, `delete_account(user)`: a `user.delete()` inside `transaction.atomic()` plus a security-log line, returning the (now dangling) user code. The module exists because the *erasure map* deserves one written-down home — the schema already encodes it: collections/things/bookings/RSVPs/notifications/daily-activity **cascade**; FAQ questions and ThingTransfer hops on other people's things **survive with the user FK nulled** (SET_NULL — content stays, attribution goes, rendered as "former member"); `Report` rows were already SET_NULL; the `Event` log holds only code snapshots (never exposed); stored files are deleted by the `asset_cleanup` `post_delete` handlers, which fire for cascade-deleted rows too. Called only from `VerifyLinkView._handle_account_delete` (the emailed-link commit step).

---

### `export_service.py` — Data Portability (Right to a Copy)

The mirror of `account_service`: *what dies with you is what you get to take with you*. Read the two docstrings together — when a new model arrives, both are wrong until both are updated.

#### Public API

| Function | Returns |
|----------|---------|
| `build_account_export(user)` | The whole of one person's data as a JSON-serialisable tree: `_manifest`, `_readme`, `profile`, `collections_owned`, `collections_member_of`, `things`, `bookings`, `faqs`, `proposals_made`, `transfers`, `notifications`, `reports_filed`, `activity`. One private helper per key, each with its own `select_related`/`prefetch_related`. |
| `build_collection_export(collection)` | An **operational** copy of a group, other members' things included: `collection`, `members`, `pending_invitations`, `proposals`, `things`, `bookings`, `faqs`, `transfers`, `stats`. Not art. 20 and doesn't pretend to be — it is what makes a library of things portable. **Owner-only; the caller enforces that** (`require_collection_owner`), this function trusts it. |
| `export_bytes(payload)` | `json.dumps(..., ensure_ascii=False, indent=2, default=str)` encoded UTF-8. `default=str` is the safety net, not the plan: every builder already returns JSON-native values, so a type reaching it means a new column arrived without a decision. |
| `export_filename(code)` | `oiueei-ABC123-2026-08-21.json` — the code says which copy, the date says when it stopped being true. |
| `collection_stats_rows(collection)` | `[(metric, value)]` — **the** definition of every usage metric, rendered two ways: `CollectionStatsView` writes it as CSV, the collection export carries it as a dict under `stats`. Public despite living among the private helpers, because a view in another module imports it. `STATS_WINDOW_DAYS` (90) is the window every `(90d)` metric measures. |

`_manifest.counts` indexes every key that holds rows (nested one level for the keys holding two lists), so the top-level data keys are exactly `profile` + the keys of `counts`. `_readme` ships the file's own explanation in the reader's language, resolved through **`resolve_email_language`** — the recipient's preference over the group's over `EMAIL_LANGUAGE`; an unknown language falls back to English rather than raising. The catalogue is `README_TEXTS` (en/es/ca), kept in parity by a test, and it exists because a JSON tree can't explain its own omissions: someone who finds no reports about their things should learn *here* that they are anonymous by design, not conclude the export is broken.

#### What never leaves — each pinned by a test, most against the raw bytes

| Omission | Why |
|----------|-----|
| `Collection.share_token`, every `RSVP.token` | A file gets forwarded; a token inside it is a group — or an account — forwarded with it. |
| Co-members' emails from groups the exporter merely **joined** | Member emails ride along only in collections they **own**, which is the roster the guests page already shows them. |
| `age_range` / `postal_code` of anyone else, unless the group is COMMUNITY | Built by `Collection.owner_member_rows`, the **same** row shape `CollectionSerializer.get_invites` serves the guests page — one definition, so the export cannot be the back door to what the API withholds. It used to be a second copy of that loop, kept true by vigilance. *(The aggregate breakdown inside `stats` is a different thing and stays: it is the stats CSV, unchanged, which any collection owner can already download.)* |
| Reports **about** the exporter's things (both exports) | Reporting is anonymous by design; the export must not become the leak the notification avoids. |
| `BookingPeriod.requester_email`, third parties' demographics, other members' notifications and activity | Third-party data with no reason to be in this file — a counterpart is a code and a public name. |
| The `deal` M2M, `password`, `is_staff`/`is_superuser`, the `*_alarm_sent` / `capacity_unblocked` flags | Not the person's content: the first is third parties, the last is this deployment's moderation ledger. |

**Owner text stays raw.** A localized `headline` (`{"es": …, "ca": …}`) exports as the map the owner wrote, never resolved to one language: the file is for machines, and resolving would silently drop two thirds of it.

**Photos and the welcome PDF travel as URLs, not bytes.** It keeps the response inside Heroku's 30-second window — and it is why the page offering the download has to say that deleting the account breaks those links.

---

### `asset_cleanup.py` — Delete Stored Files on Delete

Frees the stored objects a record owns when the record itself is deleted, so removing a thing / collection / user doesn't leave orphaned files piling up (storage cost + clutter). The bucket has no notion of a foreign key, so nothing else would ever notice they had become unreachable.

#### How it's wired

- **`post_delete` signal handlers** on `Thing`, `Collection` and `User` (registered in `core.apps.CoreConfig.ready`). Django fires `post_delete` for cascade-deleted rows too, so this single hook covers every path: a direct thing/collection delete, the collection view's orphan-thing sweep (`CollectionViewSet.perform_destroy`), and a user-account FK cascade (which removes their collections and things).
- **Runs on `transaction.on_commit`** — a delete that rolls back keeps its images. The destroy **never raises** (`_destroy` swallows + logs): an orphaned asset is a smaller problem than a delete that blows up.

#### What gets destroyed per model

| Model | Assets |
|-------|--------|
| `Thing` | `thumbnail` and every `gallery` id |
| `Collection` | `thumbnail`, `welcome_doc` (the welcome PDF — also `resource_type=image`, so the default destroy kwargs are right) |
| `User` | `photo` |

#### The seed pool is never destroyed

Keys under **`storage.SEED_PREFIX`** (`oiueei/seed/`) are skipped outright. The demo's fixtures are a *shared, static pool*: every database that has ever run `seed_demo` points at the same objects, so they don't belong to the rows that reference them and one delete must not take them from every other environment.

The skip is **per key, not per record** — a genuine upload sitting in the same thing's gallery as a seed image is still cleaned.

This used to be handled only by `seed_demo --reset` suspending the mechanism, which left every *other* door open: the Django admin, an FK cascade, a shell delete. Deleting the demo from the admin emptied the whole folder for real, which is what prompted the guard. `cleanup_orphan_images` already skipped the same prefix — the two now read it from one constant in `storage`, because two hand-written copies of a path that must agree are one edit away from a demo that deletes its own photographs.

#### Suspension (still needed, for a different job)

`suspended()` is a context manager that disables the cleanup entirely for deletes inside the block. **`seed_demo._reset()` still wraps its deletes in it** — belt and braces over the skip above, and the reusable guard for any bulk delete that must not touch the bucket at all.
