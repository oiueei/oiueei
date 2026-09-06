# OIUEEI Views Documentation

This document describes the behaviour, endpoints, permissions, and business logic for each view in the OIUEEI application.

---

## Auth Views (`core/views/auth.py`)

### RequestLinkView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/auth/request-link/` |
| **Permission** | `AllowAny` |
| **Rate limit** | 5 requests/minute per IP **and** 5 requests/hour per account (the requested email, lowercased — `email_ratelimit_key`) so one mailbox can't be flooded from rotating IPs. |

Requests a magic link for passwordless authentication.

**Request body:**
```json
{ "email": "user@example.com" }
```

**Behaviour:**
1. Validates email via `RequestLinkSerializer`.
2. Looks up user by email (lowercased). Returns 200 with unified message regardless of whether email exists (anti-enumeration).
3. If user found: creates an RSVP with action `MAGIC_LINK` and sends magic link email via `send_magic_link_email()`.
4. Logs request to `security` logger with IP.

**Anti-enumeration, and the timing delta that remains (L10).** The response body is identical either way, and the SMTP send is dispatched to a daemon thread in production (`EMAIL_SEND_ASYNC`) so the slow part can't be timed — that was L10. What it did not close: the `RSVP.objects.create()` INSERT (and the thread spawn itself) run **only** on the registered path, so a registered address still answers marginally faster-to-measure than an unregistered one. This is **known and accepted**, not an oversight. Equalising it would mean writing the RSVP from inside the daemon thread and spawning that thread on both paths — a DB write with no connection cleanup, and a failed INSERT downgraded from a 500 to a silent no-email — to hide a sub-millisecond difference that the rate limits (5/min per IP, 5/hour per email) already cap sampling of far below the point where it could be averaged out of network noise.

**Responses:**
| Status | Condition |
|--------|-----------|
| 200 | Always (unified message for anti-enumeration) |
| 429 | Rate limited |

---

### VerifyLinkView

| | |
|---|---|
| **Endpoint** | `GET` / `POST /api/v1/auth/verify/{token}/` (also aliased at `/api/v1/rsvp/{token}/`) |
| **Permission** | `AllowAny`. **`authentication_classes = []`** — the ~134-bit URL token is the bearer credential, so no authenticator runs; this also keeps `POST` clear of DRF's `SessionAuthentication` CSRF gate (no handler reads `request.user`). |
| **Rate limit** | 10 requests/minute per IP (GET and POST keyed separately) |

The URL segment is the RSVP's high-entropy `token` (≈134 bits), not the 6-char PK — the PK can no longer resolve an RSVP.

**GET vs POST — `BOOKING_ACCEPT`/`BOOKING_REJECT` require a POST to commit.** These two decisions are irreversible and authenticate no one, so a bare GET must never fire them — an email link-scanner or a page prefetch/refresh could otherwise auto-decide a hold. For those actions **GET only previews** (`200 {"action", "requires_confirmation": true, "thing_headline"}` — no mutation, RSVP not consumed); the frontend `VerifyPage` then **auto-fires the committing POST from JS** on load (one click for the owner — opening the link — with no second on-page button). This keeps the anti-prefetch guarantee: a scanner/prefetch does a bare GET, runs no JS, and so never reaches the committing POST. The login/invite actions (`MAGIC_LINK`, `COLLECTION_INVITE`, `COLLECTION_REJECT`) still resolve on GET — a scanner that consumes one only forces a fresh link; it decides nothing on the user's behalf.

Routes to the appropriate handler based on `rsvp.action`:

| Action | Handler | Commit verb | Description |
|--------|---------|-------------|-------------|
| `MAGIC_LINK` | `_handle_magic_link` | GET | Authenticates user, sets auth cookies, and returns the `landing` contract below |
| `COLLECTION_INVITE` | `_handle_collection_invite` | GET | Adds user to collection invites M2M, sets auth cookies, deletes sibling `COLLECTION_REJECT` RSVP. Returns `landing: "collection"` + `collection` + `invited_collection` (or `landing: "home"` if the collection was deleted meanwhile) |
| `COLLECTION_REJECT` | `_handle_collection_reject` | GET | Notifies collection owner of rejection, deletes sibling `COLLECTION_INVITE` RSVP, no JWT |
| `BOOKING_ACCEPT` | `_handle_booking_accept` | **POST** | Accepts booking via `accept_booking()` service (GET previews only) |
| `BOOKING_REJECT` | `_handle_booking_reject` | **POST** | Rejects booking via `reject_booking()` service (GET previews only) |
| `PROPOSAL_APPROVE` | `_handle_proposal_approve` | **POST** | Sends the real invitation, behind the **same** quota + member-ceiling guard as the in-app approval (`invitation_service.proposal_approval_blocked` — the link is not a way around either; a refusal leaves both links alive so the owner can answer tomorrow, and carries `retryable: true` to say so — a full collection and a settled suggestion both answer 400, so the SPA cannot tell "not now" from "gone" without it). GET previews (who was suggested, by whom, their note) — approving **mails a third party**, so a link scanner must never fire it |
| `PROPOSAL_REJECT` | `_handle_proposal_reject` | **POST** | Declines. Both links die with the decision, either way |
| `ACCOUNT_DELETE` | `_handle_account_delete` | **POST** | Erases the account via `account_service.delete_account()` (GET previews only: name, email, owned collection/thing counts). Unlike bookings, the frontend **never auto-commits** this preview — the person must press the explicit on-page confirm button. The commit response also clears the auth cookies (the session died with the account); the RSVP itself cascades away with the user row |

**Post-login landing (`landing`).** The successful-login response carries where the SPA should send the user — `"collection"` (plus `collection`, the code), `"welcome"`, or `"home"`. It used to be decided in the browser from the `seenWelcome` localStorage key, but logout clears that key, so every re-login looked like a first visit and dropped returning users on `/welcome`. The rules, in order:

1. The RSVP carries a `target_code` — a share-token or public-collection join — ⇒ **that collection** (they joined it precisely to get there). `invited_collection` is still returned alongside `collection`: it is what tells the SPA the landing came from an invitation (it shows the collection's welcome box).
2. Otherwise the link was born at an open door with no target (`RSVP.origin == POPIN`) ⇒ **`"welcome"`** — a genuinely new visitor with nothing else to see. **Nothing in this repository produces that RSVP any more**: every join here carries a collection, and `/welcome` left the standalone with the demo. It is kept because a deployment that adds its own open door stamps exactly this shape, and `VerifyLinkView` is a shared file it must never have to edit; the SPA resolves it against `deployment/aboutPath` and falls through to home when there is none.
3. Otherwise (`/login`, `origin == LOGIN` — and any legacy magic link with a blank `origin`) ⇒ their **single ACTIVE collection** (owned or invited) when they have exactly one, else **home**. `_solo_collection_code()` stops the query at two rows.

`RSVP.origin` is stamped `LOGIN` by `RequestLinkView` and `POPIN` by `JoinView`; it is blank on every other action. `seenWelcome` survives only as the suppressor for `CollectionPage`'s first-time welcome box — it no longer decides navigation.

**Common behaviour (`_resolve_rsvp` → `_dispatch`):**
1. Looks up RSVP by `token` (the high-entropy URL token, not the PK). Returns 401 if not found.
2. Checks `rsvp.is_valid()` (per-action expiry — magic 24h / booking 72h / invite ~30 days, see the RSVP model). Deletes and returns 401 if expired.
3. GET previews a confirm-required action (`_preview`, no mutation); otherwise (and always on POST) delegates to the action handler.
4. On commit, the RSVP is deleted after use (one-time use).

**Internal helpers:**
- `_authenticate_user(request, rsvp)` — Shared by `MAGIC_LINK` and `COLLECTION_INVITE` handlers. Validates user, calls `update_last_activity()`, mints a JWT. Returns `(user, refresh, user_data)` tuple or `Response` on failure. Auth tokens are set as HttpOnly cookies via `_set_auth_cookies()`. Auth is JWT-cookie-only — it deliberately does **not** open a Django session (no `login()`); the admin site has its own session, so a shadow session would be needless attack surface.
- `_handle_booking_action(rsvp, accepted)` — Shared by `BOOKING_ACCEPT` and `BOOKING_REJECT` handlers. Looks up booking, validates via `is_valid()`, calls `accept_booking()`/`reject_booking()` service, sends decision email, deletes sibling RSVPs.

**MAGIC_LINK response (200):**
```json
{
  "action": "MAGIC_LINK",
  "user": { ... },
  "invited_collection": "<collection_code>"
}
```
Auth tokens (`access_token`, `refresh_token`) are set as HttpOnly cookies via `_set_auth_cookies()`. `invited_collection` is present **only** when the RSVP carried a `target_code` — i.e. the magic link came from a join (private share token or PUBLIC login-to-act code). The SPA then drops the user straight onto that collection rather than the default landing (home, or their single collection). A plain `/login` magic link has no `target_code`, so the field is omitted.

**COLLECTION_INVITE response (200):**
```json
{
  "action": "COLLECTION_INVITE",
  "user": { ... },
  "invited_collection": "<collection_code>"
}
```
Auth tokens are set as HttpOnly cookies via `_set_auth_cookies()`.

**COLLECTION_REJECT response (200):**
```json
{
  "action": "COLLECTION_REJECT",
  "message": "Invitation declined"
}
```

**BOOKING_ACCEPT response (200):**
```json
{
  "action": "BOOKING_ACCEPT",
  "message": "Booking accepted",
  "thing_headline": "...",
  "start_date": "...",
  "end_date": "..."
}
```

---

### JoinView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/auth/join/` |
| **Permission** | `AllowAny` |
| **Rate limit** | 5 requests/minute per IP **and** 5/hour per account (email), plus the per-collection daily join cap (below) |

How a visitor who was pointed at a collection joins it and gets a magic link
back. Two doors reach it, and both are somebody choosing to let a specific
person in: an owner's `share_token` (the `/share/{token}` link they handed out)
and a PUBLIC collection's `collection_code` (login-to-act).

It was `POST /auth/pop-in/` until v0.12.0, when the open demo door left the
standalone. `RSVP.Origin.POPIN` keeps its name — see the model for why.

**Request body:**
```json
{ "email": "user@example.com", "share_token": "<optional 22-char token>", "collection_code": "<optional PUBLIC collection code>" }
```

**Behaviour:**
1. Validates email via `RequestLinkSerializer`.
2. **Resolves the target first** (`_resolve_target`): a `share_token` naming an ACTIVE collection, else a `collection_code` naming a **PUBLIC, ACTIVE** one. A code is never a way into a PRIVATE collection, and an unknown/revoked/INACTIVE one is silently ignored.
3. **With no target, nothing is created** — no `User`, no RSVP, no email — and the same 200 is returned. Ordering matters here and is the point: `get_or_create` used to run *first*, so a POST carrying only an email minted a real account that joined nothing, which on any deployment without onboarding collections was an open registration door on an otherwise invite-only product.
4. `get_or_create` user by email; a **newly created** user is stamped with the `language` from the body (`es`/`ca`/`en`) so their first magic link speaks it. An existing user's saved preference is never overwritten.
5. Adds them to the collection's `invites` M2M (via `_join_collection`, so first-join side effects — `MEMBER_JOINED`, the welcome PDF — fire exactly once) **and stamps it as the RSVP `target_code`**, so verifying the link lands them on that collection.
6. Creates the `MAGIC_LINK` RSVP (`origin=POPIN`) and sends the magic link, **whose subject names the joined collection** (`"Hello, welcome to '{headline}' - OIUEEI!"`) and whose language follows the collection's.
7. Logs to the `security` logger with IP, whether the user is new, and which collection — or that nothing was created.

**The per-collection daily cap (`COLLECTION_JOINS_PER_DAY`).** Neither door here
is a secret — a PUBLIC collection's code is printed in its own URL and a share
token exists to be passed around — so anyone may ask this deployment to mail a
magic link to any address they type. That is a relay pointed at the operator's
sending domain, and the two rate limits above do not reach it: they cap how often
**one IP** asks and how often **one victim** is mailed, not many IPs each mailing
a different stranger once, which is the shape of the abuse. `INVITE_EMAILS_PER_DAY`
did not cover it either — that counts what an *account* sends through the owner's
invite routes, and this door has no account behind it.

So `join_quota_exhausted()` is checked **after** the target resolves and
**before** anything is created; `consume_join_quota()` charges one after the send
is dispatched. It is keyed per collection, never per deployment: a single global
counter would let anyone shut joining off for every group on the instance by
spending it on one. A refusal creates nothing, sends nothing, returns the
**unified response** — telling the visitor "over its limit" would confirm the
code names a real, joinable collection — and writes a `security` warning, the
same shape as the capacity alarms, where the tripwire reports to whoever set it
and never to whoever tripped it. Off by default; see
[`join_quota`](../services/CLAUDE.md).

**The unified response is the anti-enumeration guarantee.** The refusal and the
success are byte-for-byte identical, which is what stops the endpoint answering
"does this address / token / collection code exist?". `test_join_hardening.py`
compares whole responses rather than a message, so a field added to one path and
not the other fails there — and it now does the same for the quota refusal.

**It is a guarantee about the *body*, not the clock.** Since the no-target path
was made to create nothing, it also returns without the writes the joining path
does — so the two differ in *duration* even though they are identical in
content. What keeps the spaces unwalkable is therefore not constant time but
their size and the rate limits: a 22-character share token, a 6-character code
(36⁶ ≈ 2.2 × 10⁹), and 5/min per IP + 5/h per email. Timing is the weaker of the
two properties and always was; the fix that removed the account creation
improved the endpoint and narrowed this claim at the same time. **Don't add
sleeps to "even it out"** — padding to the slow path would slow every real join
for a threat the rate limit already bounds, and padding accurately is a much
harder problem than it looks.

**Responses:**
| Status | Condition |
|--------|-----------|
| 200 | Always (unified message, whether or not anything was created) |
| 400 | Malformed email |
| 429 | Rate limited |

---

### MeView

| | |
|---|---|
| **Endpoint** | `GET /api/v1/auth/me/` |
| **Permission** | `IsAuthenticated` |

Returns the current authenticated user's full profile via `UserSerializer`. Updates `last_activity` on each call.

**Plus `capabilities`** — what this deployment lets that account create:

```json
"capabilities": {
  "collection_modes": ["PROPRIETARY", "COMMUNITY"],
  "thing_types": ["GIFT_THING", "SELL_THING", "RENT_THING", "LEND_THING"],
  "request_url": null
}
```

The standalone answers with everything and a null `request_url` (see [`creator_policy`](../services/CLAUDE.md#creator_policypy--who-may-create-what-on-this-deployment)). It is **not** a `UserSerializer` field: what someone may create belongs to the deployment, not to the person, and that serializer is also what `/users/{code}/` returns about somebody else. It rides here because the SPA calls this endpoint on every app load, and it comes from the **same `capabilities()` call the create endpoints refuse with** — that is what stops the UI offering a control the API would 403. `request_url` is where to ask for what was withheld; null means there is nowhere, which is the difference between "this deployment does not do that" and "ask here".

---

### LogoutView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/auth/logout/` |
| **Permission** | `AllowAny`, `authentication_classes = []` |

Logs out the current user. Reads the refresh token from the `refresh_token` HttpOnly cookie (scoped to `/api/v1/auth/` so it actually reaches this endpoint — `REFRESH_COOKIE_PATH`), blacklists it so it can't be reused to refresh, and clears both `access_token` and `refresh_token` cookies.

**Authenticates nothing, on purpose — logout must never fail.** It used to be `IsAuthenticated`, which broke it in the two cases that matter most: an **expired access token** 401'd the request, leaving the still-valid (up to 7 days) refresh token unblacklisted; and a cookie-authenticated POST **without an `X-CSRFToken` header** was rejected by `CookieJWTAuthentication.enforce_csrf` with a 403, leaving every cookie alive while the SPA navigated to `/login` anyway — so the session came back to life on the next page load (the reported "logout doesn't log out" bug; `LogoutPage` now also goes through `apiFetch`, which sends the header). With no authenticator the view simply reads the refresh cookie, blacklists it (best-effort — an invalid token is swallowed) and **always** returns 200 with the three cookie-deleting headers. The trade-off is a CSRF-forced logout: a cross-site POST can end a session, never act inside one.

### AccountDeleteRequestView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/auth/delete-account/` |
| **Permission** | `IsAuthenticated` |
| **Rate limit** | 3 requests/hour per user |

Step one of the right-to-erasure flow. Deletes any previous `ACCOUNT_DELETE` RSVP for the account (resend-safe: at most one live link), creates a fresh one (24h expiry) and emails its confirmation link via `send_account_delete_email` (Cat. 1, always delivered, no viral CTA). **Nothing is deleted here** — the deletion commits in `VerifyLinkView._handle_account_delete`, on an explicit POST from the page the link lands on, so a stolen browser session alone can't erase an account (the attacker would also need the mailbox). Returns `200 {"message": "Confirmation email sent"}`.

---

### TokenRefreshView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/auth/refresh/` |
| **Permission** | `AllowAny` |

Rotates auth tokens. Reads the `refresh_token` from the HttpOnly cookie, validates it, generates a new access/refresh token pair, and sets them as HttpOnly cookies on the response.

**Responses:**
| Status | Condition |
|--------|-----------|
| 200 | Tokens rotated successfully |
| 401 | Missing, invalid, or expired refresh token |

---

## Contact View (`core/views/contact.py`)

### ContactView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/contact/` |
| **Permission** | `AllowAny` — anonymous on purpose: the person who most needs the support channel is the one who can't log in |
| **Rate limit** | 5 requests/hour per IP |

Forwards a support/feedback message to the operator's mailbox (`CONTACT_EMAIL` env var, defaulting to `DEFAULT_FROM_EMAIL`) via `send_contact_email`, with the sender's address as `Reply-To` so answering is one click. Body: `{name?, email, message, kind?}` (`ContactSerializer` — SafeHeadline name ≤32, EmailField, SafeText message ≤2000, so HTML/injection is rejected at the boundary; `kind` is `support` (default, the contact page) or `collab` (the collaborate page) and only changes the operator's subject line). Fixed recipient: the form can annoy exactly one mailbox, never relay spam to third parties. Returns `200 {"message": "Message received"}`.

---

## User Views (`core/views/users.py`)

### can_view_user(viewer_user_code, target_user_code)

Helper function. Returns `True` if:
- Viewer is the target (own profile)
- Target is invited to any collection owned by viewer
- Viewer is invited to any collection owned by target

This provides IDOR protection — users can only see profiles of people connected via collections.

### UserDetailView

| | |
|---|---|
| **Endpoint** | `GET /api/v1/users/{user_code}/` |
| **Permission** | `IsAuthenticated` + `can_view_user()` |

Returns user profile. Own profile returns full data (`UserSerializer`), other profiles return public data (`UserPublicSerializer`) plus a `shared_collections` array (collections where both users are connected as owner/invite) with `code` and `headline` for each.

| | |
|---|---|
| **Endpoint** | `PUT /api/v1/users/{user_code}/` |
| **Permission** | `IsAuthenticated` + own profile only |

Updates own profile via `UserUpdateSerializer` (partial update). Accepts optional `name`, `headline`, `about` (Markdown bio, max 2000, HTML rejected), `photo` (storage key), `koro`, `theeeme` (Theeeme code), `notify_activity`, and `notify_news`. Returns the full `UserSerializer` (including `photo_url`). Returns 403 if attempting to update another user.

---

## Inbox Views (`core/views/inbox.py`)

### InboxView

| | |
|---|---|
| **Endpoints** | `GET /api/v1/inbox/[?collection={code}]` and `DELETE /api/v1/inbox/{code}/` |
| **Permission** | `IsAuthenticated` |

GET lists the current user's in-app notifications (`code`, `type`, `payload`, `created`). DELETE dismisses (hard-deletes) one, scoped to the requesting user — a code belonging to someone else 404s. Both URL routes resolve to this one view; each handler takes an optional `code` and returns a clean **405** for the combination it doesn't serve (`GET /inbox/{code}/` and `DELETE /inbox/`) rather than a signature-mismatch 500.

**`?collection={code}`** narrows the list to the notifications born in that collection (`payload__collection_code`, a JSONField lookup that works on SQLite and PostgreSQL alike) — no param means today's behaviour, everything. It is what lets a collection's own page show its owner the hold requests for the things that live there, instead of stranding them on Home (O1); the frontend `InboxNotifications` component is the only caller. Payloads written before the key existed carry no collection and so never match a filtered list.

Booking notifications also **clear themselves** once the request they announce is settled — see [`booking_service`](../services/CLAUDE.md#the-request-notifications-lifecycle). Both decision paths (this API's `BookingActionView` and the email/RSVP `VerifyLinkView`) converge on `finalize_booking_decision`, so neither can leave a stale one behind.

---

## Notification Preference Views (`core/views/notifications.py`)

### NotificationsByTokenView

| | |
|---|---|
| **Endpoints** | `GET /api/v1/notifications/token/{token}/` and `PATCH /api/v1/notifications/token/{token}/` |
| **Permission** | `AllowAny` |
| **Rate limits** | GET: 20/min per IP. PATCH: 10/min per IP. |

Unauthenticated endpoint scoped to editing `notify_activity` / `notify_news` on a specific user. The token is a `TimestampSigner` signature over the user's code (salt `notifications-prefs`, ~1-year TTL — no stored column), produced by `core.services.email_service.make_notifications_token()` and resolved by `verify_notifications_token()`; every Cat. 2 / Cat. 3 email footer contains a link of the form `/me/notifications/{token}`.

**Behaviour:**
- Resolves the token via `verify_notifications_token()`. Returns 401 `{ "detail": "Invalid or expired link" }` if invalid.
- On GET: returns `{ notify_activity, notify_news }` for the signed user.
- On PATCH: accepts partial `{ notify_activity?, notify_news? }` via `NotificationPrefsSerializer` and persists the change.
- Token has blast radius limited to these two booleans — it cannot be used to read or modify anything else.

### DigestMuteByTokenView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/digest/mute/{token}/` |
| **Permission** | `AllowAny` — the signed token is the whole credential |
| **Rate limit** | 10 requests/minute per IP |

The one-click unsubscribe at the foot of every digest. The token signs `{user_code}:{collection_code}` under its own salt (`make_digest_mute_token`), so it can't be exchanged for a preferences token; its blast radius is one row in one M2M, which the member can undo from the collection page.

**POST, not GET** — the same anti-prefetch reasoning as the booking decisions in `VerifyLinkView`: a mail client's link scanner issues a bare GET and runs no JS, so it must not be able to unsubscribe someone. The SPA page at `/digest/mute/:token` fires the POST from JS on mount. Answers 401 on an invalid/expired/tampered token, and never reveals whether the member was subscribed.

---

## Thing Views (`core/views/things.py`)

### ThingViewSet

| | |
|---|---|
| **Base** | `ModelViewSet` with `DefaultRouter` |
| **Lookup** | `code` |

| Action | Endpoint | Permission |
|--------|----------|------------|
| `list` | `GET /api/v1/things/` | `IsAuthenticated` |
| `create` | `POST /api/v1/things/` | `IsAuthenticated` |
| `retrieve` | `GET /api/v1/things/{code}/` | `AllowAny` + `can_view()` — anonymous-safe: visible when the thing sits in a PUBLIC, ACTIVE collection |
| `update` | `PUT /api/v1/things/{code}/` | `IsAuthenticated` + `IsThingOwner` |
| `partial_update` | `PATCH /api/v1/things/{code}/` | `IsAuthenticated` + `IsThingOwner` |
| `destroy` | `DELETE /api/v1/things/{code}/` | `IsAuthenticated` + `_can_delete()` |
| `activate` | `POST /api/v1/things/{code}/activate/` | `IsAuthenticated` + `IsThingOwner` |
| `hide` | `POST /api/v1/things/{code}/hide/` | `IsAuthenticated` + `IsThingOwner` |

**Serializers:**
- Create: `ThingCreateSerializer`
- Update: `ThingUpdateSerializer` (`status` is read-only to prevent direct manipulation, `type` is editable)
- Read: `ThingSerializer`

**Queryset:** Own things only (`Thing.objects.filter(owner=request.user)`), ordered by `-created`.

**Retrieve:** Uses `thing.can_view(user_code)` — owner, or invited to an ACTIVE collection containing the thing (INACTIVE things are only visible to their owner).

**Deployment policy (`CREATOR_POLICY`).** `perform_create` asks whether this deployment offers that verb to this account at all — **403** if not — **unless** it is a member contributing to a COMMUNITY collection they were invited to, of a type its owner allow-listed (`community_contribution_types`; a `CreatorPolicy` gates *initiating*, not *contributing* to a group someone else already vouched for). The collection is resolved before the check now, but a nonexistent or un-addable one still falls through to the **same 403** as no collection at all, so the verb refusal never turns on — or reveals — which collection was named. `perform_update` asks the same, but **only when the type actually changes** (a thing already under a withheld verb stays editable), and the COMMUNITY exception there needs *every* collection the thing sits in to allow the new verb. The standalone's policy allows everything, so none of this does anything upstream. See [`creator_policy`](../services/CLAUDE.md#creator_policypy--who-may-create-what-on-this-deployment).

**Create behaviour:** Optionally accepts `collection_code` in request body. `perform_create` raises DRF exceptions directly (no `{"error": ...}` two-phase protocol): an unknown `collection_code` → **404 NotFound**; a collection the user can't add to → **403 PermissionDenied**; a type/tag rule violation → **400 ValidationError** (field-keyed: `{"type": [...]}` / `{"tags": [...]}`, like `perform_update`). If valid, the thing is automatically added to it. **Per-collection allowlist** (`Collection.allowed_thing_types`): if non-empty, the thing's type must be in it — returns 400 otherwise. Empty list = no per-collection restriction. **Tags**: any `tags` on the thing must belong to the collection's `Collection.tags` vocabulary — returns 400 otherwise (tags require a collection; on update, `ThingUpdateSerializer.validate_tags` checks the union of the thing's collections' tags). Removing a tag from a collection (via `CollectionUpdateSerializer`) cascade-strips it from that collection's things.

**`activate` action:** Sets `status = 'ACTIVE'`. Returns 400 if thing is not INACTIVE.

**`hide` action:** Sets `status = 'INACTIVE'`. Only the current thing owner (`thing.owner`) can hide — returns 403 for everyone else. Returns 400 if thing is not ACTIVE (cannot hide a TAKEN thing — cancel the hold first).

**`destroy` action (`_can_delete()`):** Permanent deletion (the thing and all related data). Two cases grant permission: (1) the user owns any collection containing the thing (collection owner can always delete); (2) the user is the current thing owner AND no `ThingTransfer` records exist (thing has never changed hands). Returns 403 otherwise. Frontend shows the Delete button for the collection owner regardless of thing status; the thing owner sees it when the thing has never changed hands.

### InvitedThingsView

| | |
|---|---|
| **Endpoint** | `GET /api/v1/invited-things/` |
| **Permission** | `IsAuthenticated` |
| **Pagination** | `StandardResultsPagination` |

Lists things from collections where the current user is invited. Only returns ACTIVE or TAKEN things (excludes INACTIVE). Only returns things from ACTIVE collections. Uses `.distinct()` to avoid duplicates.

### ThingBulkCreateView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/collections/{collection_code}/things/bulk/` |
| **Permission** | `IsAuthenticated` + `collection.can_add_thing()` |
| **Rate limit** | `10/h` per user |

CSV/ZIP bulk-add (F-9). Body is `{"rows": [{type, headline, description, fee, availability, location, condition, tags, thumbnail, is_endless}, ...]}` (max 100 rows), parsed and previewed client-side by `BulkAddCsv`. Each row is validated with `ThingBulkRowSerializer` (the project's Safe* fields + a `reject_spreadsheet_formula` CSV-injection guard on free-text fields, including each `tags` entry; `thumbnail` uses `ImageIdField`, path-traversal-safe; `fee` accepts a decimal comma — `LocaleDecimalField`, S9 — since a CSV cell has no client `NumberInput` to normalise it first) , `thing_type_denial` (the deployment's `CREATOR_POLICY` — reported as a row error like every other row failure, since the contract here is that one response names every bad row) and `type_validity_error`; `tags` are additionally checked in the view against the target collection's `Collection.tags` vocabulary (mirrors the single-create subset check). **A CSV tag may name a localized vocabulary entry by any of its languages** (S10, `_resolve_tag_aliases`): `{"es": "Crianza", "ca": "Criança"}` in the vocabulary accepts a CSV cell of `Crianza` or `Criança` (case-insensitively) as well as the exact canonical JSON, storing the canonical string either way; a casefolded alias that matches two distinct vocabulary entries is rejected as ambiguous rather than guessed, and an alias matching nothing keeps the existing "not defined by the collection" error. If **any** row fails the request returns `400 {"errors": [{row, errors}]}` and **nothing** is created. On full success every row is created in one `transaction.atomic()` and the response is `201 {"created": N, "codes": [...]}`. **Photos** are importable via the client's ZIP path: `BulkAddCsv` unzips, uploads each image to the bucket through the same ticketed path as every other upload, and sends the resulting storage key as `thumbnail` — the server only ever receives the validated key, never the binary. Gallery photos are still not bulk-importable.

---

## Collection Views (`core/views/collections.py`)

### CollectionViewSet

| | |
|---|---|
| **Base** | `ModelViewSet` with `DefaultRouter` |
| **Lookup** | `code` |

| Action | Endpoint | Permission |
|--------|----------|------------|
| `list` | `GET /api/v1/collections/` | `IsAuthenticated` |
| `create` | `POST /api/v1/collections/` | `IsAuthenticated` |
| `retrieve` | `GET /api/v1/collections/{code}/` | `AllowAny` + `can_view()` — anonymous-safe: a PUBLIC, ACTIVE collection is readable without login |
| `update` | `PUT /api/v1/collections/{code}/` | `IsAuthenticated` + `IsCollectionOwner` |
| `partial_update` | `PATCH /api/v1/collections/{code}/` | `IsAuthenticated` + `IsCollectionOwner` |
| `destroy` | `DELETE /api/v1/collections/{code}/` | `IsAuthenticated` + `IsCollectionOwner` |
| `add_thing` | `POST /api/v1/collections/{code}/add-thing/` | `IsAuthenticated` + `can_add_thing()` |
| `remove_thing` | `POST /api/v1/collections/{code}/remove-thing/` | `IsAuthenticated` + owner or thing owner (COMMUNITY) |

**Serializers:**
- Create: `CollectionCreateSerializer`
- Update: `CollectionUpdateSerializer`
- Add thing: `CollectionAddThingSerializer`
- Read: `CollectionSerializer`

**Queryset:** Own collections only, ordered by `-created`. List and retrieve actions use the module-level `_optimise_collection_queryset()` helper for `select_related`/`prefetch_related` optimisation (also reused by `InvitedCollectionsView`).

**Deployment policy (`CREATOR_POLICY`).** `perform_create` refuses a mode this deployment does not hand out with **403**, judging the **PROPRIETARY default** when the body names no mode. `perform_update` refuses switching an existing collection *into* a withheld mode — only on a real change, so a collection already in one stays editable by its owner. Both are no-ops under the standalone's open policy. See [`creator_policy`](../services/CLAUDE.md#creator_policypy--who-may-create-what-on-this-deployment).

**Retrieve:** Uses `collection.can_view(user_code)` — owner, or invited user if collection is ACTIVE (INACTIVE collections are only visible to their owner). The `CollectionSerializer.things` field excludes INACTIVE things for non-owners.

**Add thing:** Uses `collection.can_add_thing(user_code)` — owner can always add; in COMMUNITY mode, invited users can add their own things. Validates thing exists, belongs to user, and is not already in collection.

**Remove thing:** Owner can remove any thing. In COMMUNITY mode, thing owners can remove their own things. Validates thing is in the collection, removes it from the M2M without deleting the thing itself.

### CollectionInviteView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/collections/{collection_code}/invite/` |
| **Permission** | `IsAuthenticated` + collection owner |
| **Rate limit** | 30 requests/hour per user, plus the shared daily invitation-email quota (below) |

Invites a user to a collection by email. Creates user if they don't exist (`get_or_create`). Returns 400 if the user is already invited (in M2M). Deletes any existing pending RSVPs for the same user+collection before creating new ones (resend-safe). Creates two RSVPs (`COLLECTION_INVITE` for accept and `COLLECTION_REJECT` for decline) and sends invitation email with both links.

**Daily invitation-email quota (shared with the bulk endpoint).** The per-view rate limits count *requests*, so one bulk request could still fan out 100 emails (5/h × 100 rows ≈ 500 owner-authored emails an hour from one free account — a spam vector riding the platform's sending domain). `INVITE_EMAILS_PER_DAY` counts the invitation *emails* an account sends per day — **operator policy, not a product rule**: it guards a particular deployment's sending reputation, so the standalone ships it **unset (= unlimited)** and each operator sets their own (0 also means unlimited). It is shared between this endpoint and `CollectionBulkInviteView`. Exhausted → **429** `{"error": ...}` before any User/RSVP is created. The counter lives on the shared cache (`invq:{user}:{date}`, ~24h TTL) and follows `RATELIMIT_ENABLE` — off in dev/tests, same switch as the django-ratelimit decorators; its read-then-set shares the DatabaseCache non-atomicity note (I7) in `config/settings/base.py`.

**Request body:**
```json
{ "email": "invitee@example.com" }
```

| | |
|---|---|
| **Endpoint** | `DELETE /api/v1/collections/{collection_code}/invite/` |
| **Permission** | `IsAuthenticated` + collection owner |

Removes a user from the collection's invite list. If the invite is still pending (user has not accepted yet), deletes the pending RSVPs instead of removing from M2M, and no revocation email is sent. If the invite was accepted (user is in M2M), removes from M2M and sends revocation notification email.

**Request body:**
```json
{ "user_code": "ABC123" }
```

### CollectionJoinView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/collections/{collection_code}/join/` |
| **Permission** | `IsAuthenticated` + the collection must be readable (`can_view`) and PUBLIC |
| **Rate limit** | 30/h per user, plus the operator's `COLLECTION_JOINS_PER_DAY` ceiling |

Lets a **signed-in** reader join a PUBLIC collection themselves — the mirror of `CollectionLeaveView`, and the half of login-to-act that was missing. The anonymous funnel (`POST /auth/join/`, reached from `/collections/{code}/join`) takes an email and answers with a magic link, which is no use to a session that already exists; so the one reader with an account and the most intent had no way into a public group, while `CollectionPage` offered them "Add thing" — an action `Collection.can_add_thing` refuses without an invite, after the form was filled and the photos uploaded.

Answers **404** whenever `can_view()` says no, so a PRIVATE or INACTIVE collection never confirms it exists; **400** for the owner ("You already own this collection."); **429** once the collection has spent its day's joins. There is also a **403** for a collection that is readable but not PUBLIC, and it is **unreachable as the guards stand** — `can_view` admits a non-owner only to a PUBLIC ACTIVE collection or one they are invited to, and `is_invited` is the same query the membership check above it runs. It is kept because that invariant lives in another file: widen `can_view` (a federated tier, a "readable by link" mode) and it is what stops a readable-but-not-public collection becoming joinable. The two tests that pin the invariant instead of the branch are `test_a_private_collection_does_not_confirm_it_exists` and `test_a_member_of_a_private_collection_is_told_they_are_already_in`. An existing member gets a plain `200` and nothing happens twice. On success it goes through `_join_collection` — the single funnel every join path shares — so it logs one `MEMBER_JOINED` (`Event.Source.PUBLIC`, the same door the anonymous half records), sends the welcome document if the owner set one, and consumes one of the day's joins. The ceiling applies here for the reason it exists: one that only stopped strangers would be a cap anyone with an account could walk around.

### CollectionLeaveView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/collections/{collection_code}/leave/` |
| **Permission** | `IsAuthenticated` + must be an invited member (not the owner) |

Lets an invited member remove **themselves** from a collection (self-unlink) — the inverse of the owner-only `CollectionInviteView` DELETE. Returns 400 if the requester is the collection **owner** ("The owner can't leave their own collection." — owners delete instead) or is **not a member** ("You are not a member of this collection."). On success removes the user from the `invites` M2M, creates a `MEMBER_LEFT` in-app notification for the owner (payload: `collection_headline`, `member_name`, `collection_code`), and returns `200 {"message": "You have left the collection"}`. The frontend shows the "Leave the group" button (hero, `CollectionSerializer.is_member` gate) → `LeaveCollectionPage` confirm → back to Home.

### CollectionProposeInviteView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/collections/{collection_code}/invite/propose/` |
| **Permission** | `IsAuthenticated` + must be a member (not the owner) + `collection.allow_member_proposals` |
| **Rate limit** | 30/day per member |

A member recommends somebody: `{email, note?}` → an `InvitationProposal` plus the owner's email and in-app notification. **Nothing reaches the proposed address** — no `User` row, no email — until the owner approves. Open in **both** modes: PROPRIETARY decides who may add a *thing*, never who may suggest a person, and the owner's approval is the gate either way. 400 for the owner (they invite directly), for a non-member, for someone already in the group, and for a duplicate pending suggestion; **403** when the owner has switched recommendations off.

**The last two 400s share one message, and must keep sharing it.** "Already in the group" and "already suggested" used to read differently, which made the first an email-membership oracle: a member could put any address to this endpoint 30 times a day and read a yes/no on whether it belongs to a co-member — the fact the roster withholds from non-owners (`invites` is `code` + `name`, no email — L2). The single answer ("either they are already in this group, or someone has already suggested them") still tells the proposer the only thing they needed, which is that there is nothing to do. Pinned by `test_an_address_already_inside_is_answered_exactly_like_one_merely_queued`, which compares the two responses byte for byte.

The 30/day cap is high on purpose: abuse is not expected, and an owner has a better answer than a quota — removing the member.

### CollectionProposalActionView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/proposals/{proposal_code}/{approve\|reject}/` |
| **Permission** | `IsAuthenticated` + collection owner |

The owner's in-app answer; the email links reach the same two decisions through `VerifyLinkView`. Owner-only — the proposer must not be able to wave their own suggestion through. Approving runs `invitation_service.proposal_approval_blocked` first — the owner's daily quota (429) and the collection's member ceiling (400), since an approval that can't be delivered should say so rather than half-happen — then goes through `approve_proposal`. Both refusals answer `{error, retryable: true}` — the suggestion stays pending and the owner may come back to it. 400 (with no `retryable`) on a suggestion that is no longer pending.

**The guard is shared with the emailed approve link**, which used to apply neither: an owner clicking the link in their mail client instead of the button in the app walked straight past `INVITE_EMAILS_PER_DAY`, a cap that exists to protect the deployment's sending reputation. Nothing documented the difference and this view's own reasoning argued against it, so the two routes now answer identically. A blocked approval decides nothing and consumes no RSVP — "not now", not "never". **Declining is never blocked**: it adds nobody and mails one member who is already inside the count.

### CollectionDigestPrefView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/collections/{collection_code}/digest/` |
| **Permission** | `IsAuthenticated` + must be an invited member |
| **Rate limit** | 30 requests/hour per user |

A member silences (or un-silences) this one group's digest: `{"muted": true|false}` → `Collection.digest_muted`. Members only — the owner never receives their own collection's digest (it goes to `invites`), so they change `digest_frequency` instead; a non-member gets **400**. Idempotent (`add`/`remove`), so a double POST is harmless.

This is the control that lets `User.notify_news` default to `True` without it being a pre-ticked opt-in (DESIGN §6): leaving one group's summaries costs the member none of their Cat. 2 activity email. Read back as `is_digest_muted` on `CollectionSerializer`.

### InvitedCollectionsView

| | |
|---|---|
| **Endpoint** | `GET /api/v1/invited-collections/` |
| **Permission** | `IsAuthenticated` |

Lists ACTIVE collections where the current user is in the invites M2M. INACTIVE collections are excluded — they are only visible to their owner. Not paginated.

### MyPendingInvitationsView

| | |
|---|---|
| **Endpoint** | `GET /api/v1/my-invitations/` |
| **Permission** | `IsAuthenticated` |

Lists pending collection invitations (not yet accepted) for the current user. Returns `COLLECTION_INVITE` RSVPs for the user, joined with the collection and its owner. For each invitation returns: `accept_code`, `reject_code`, `collection_code`, `collection_headline`, `owner_name`. Used to display in-app invitation notifications on the HomePage.

### CollectionShareLinkView

| | |
|---|---|
| **Endpoints** | `POST` and `DELETE /api/v1/collections/{collection_code}/share-link/` |
| **Permission** | `IsAuthenticated` + collection owner |
| **Rate limit** | POST: 30 requests/hour per user. DELETE: unrestricted. |

Owner-only management of the public share token. The token is a 22-character URL-safe bearer credential (`secrets.token_urlsafe(16)`); anyone with the resulting `/share/{token}` link can join the collection by completing the join flow. The token is intentionally excluded from `CollectionSerializer` and any other read endpoint — it must never leak.

**`POST` behaviour:**
- Generates a new token if none exists. Returns the existing token unchanged on subsequent calls (idempotent).
- Pass `{"rotate": true}` to force a fresh token (invalidates any previously shared link).
- Returns `{share_url, share_token}`. `share_url` is built from `settings.SHARE_LINK_BASE_URL` (default `http://localhost:3000/share`).

**`DELETE` behaviour:**
- Sets `share_token` back to `null`. The shared link becomes invalid for everyone immediately.
- Returns `{"message": "Share link revoked"}`.

**Frontend integration:** `ShareCollectionMenu` (HDS Select with `IconEnvelope` / `IconShare` / `IconWhatsapp`) calls `POST` lazily the first time the owner triggers any share action. The URL is cached for the rest of the session to avoid extra round-trips.

### CollectionBroadcastView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/collections/{collection_code}/broadcast/` |
| **Permission** | `IsAuthenticated` + collection owner |
| **Rate limit** | 5 requests/day per user |

Sends a broadcast email from the collection owner to all invitees. Validates `message` (SafeTextField, max 256) via `CollectionBroadcastSerializer`; the subject is auto-generated as `Hey! {collection_headline}` (the owner does not provide one). Returns 400 if the collection has no invitees. Emails carry a `Reply-To` header (the owner) and a link to the collection (labelled "I can help!"); the in-app `BROADCAST` notification carries `collection_code` so it can deep-link there too. The email send is dispatched off the request thread in production (`_send_broadcast` → daemon thread when `EMAIL_SEND_ASYNC`, mirroring `_send_bulk_invites`) so a large group's sequential SMTP can't exhaust the Heroku 30s window (H12); the in-app notifications are still written synchronously.

**Request body:**
```json
{ "message": "Bring snacks please" }
```

**Response (200):**
```json
{ "message": "Broadcast sent", "recipients": 5 }
```

### CollectionBulkInviteView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/collections/{collection_code}/invite/bulk/` |
| **Permission** | `IsAuthenticated` + collection owner |
| **Rate limit** | 5 requests/hour per user, plus the shared daily invitation-email quota (see `CollectionInviteView`) |

Invites many guests at once from a client-parsed CSV (`{"invites": [{"email": ..., "name": ...?}, ...]}`, capped at `MAX_ROWS=100`). Best-effort: valid, new addresses are invited (accept + reject RSVP pair created, invite email sent) and the rest are reported as skipped with a reason (`invalid`, `duplicate`, `already_member`, `already_invited`, `daily_limit`) — one bad row never fails the batch. The **daily quota** (`INVITE_EMAILS_PER_DAY`, shared with the single endpoint) is enforced per email actually sent: an exhausted quota returns **429** outright; a batch that crosses the cap mid-way invites up to the remaining allowance and reports the overflow rows as skipped with reason `daily_limit` (no User row is created for those), so the owner sees exactly which addresses wait for tomorrow.

**Response (200):** `{ "invited": 2, "skipped": [{"email": "...", "reason": "..."}], "total": 3 }`

### CollectionStatsView

| | |
|---|---|
| **Endpoint** | `GET /api/v1/collections/{collection_code}/stats/` |
| **Permission** | `IsAuthenticated` + collection owner |

Owner-only usage statistics for a collection, returned as a `metric,value` CSV download: a snapshot (members, pending invitations, things total/active) plus a 90-day activity window, and an aggregate age-range/postal-code breakdown (member demographics stay COMMUNITY-only and per-member on the guests page — this endpoint is aggregate-only).

The metrics themselves live in [`export_service.collection_stats_rows()`](../services/CLAUDE.md#export_servicepy--data-portability-right-to-a-copy); this view only wraps them in a CSV. The collection export renders the same rows as a dict, so the two can't drift.

---

## FAQ Views (`core/views/faq.py`)

### ThingFAQListView

| | |
|---|---|
| **Endpoint** | `GET /api/v1/things/{thing_code}/faq/` |
| **Permission** | `AllowAny` (part of the public social layer — anyone who can view the thing may read its FAQs) |
| **Pagination** | `StandardResultsPagination` |

Lists FAQs for a thing. Owner sees all FAQs (including hidden). Invited users see only visible FAQs.

**Response fields:** `code`, `thing`, `created`, `questioner` (user code), `questioner_name` (user display name — **empty for a reader who is not signed in**; see the anonymous-read note under Security), `question`, `answer`, `is_visible`.

| | |
|---|---|
| **Endpoint** | `POST /api/v1/things/{thing_code}/faq/` |
| **Permission** | `IsAuthenticated` + `thing.can_view()` + not owner |
| **Rate limit** | 20 requests/hour per user |

Creates a new FAQ question. Owner cannot ask questions about their own thing (400). Sends notification email to thing owner with a "View and reply" link to the thing page.

**Request body:**
```json
{ "question": "Is this available in blue?" }
```

### FAQDetailView

| | |
|---|---|
| **Endpoint** | `GET /api/v1/faq/{faq_code}/` |
| **Permission** | `IsAuthenticated` + `thing.can_view()` |

Returns a single FAQ. Hidden FAQs are only visible to the thing owner and the questioner. Returns 404 for others.

### FAQAnswerView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/faq/{faq_code}/answer/` |
| **Permission** | `IsAuthenticated` + thing owner only |

Answers a FAQ. Sends notification email to questioner.

**Request body:**
```json
{ "answer": "Yes, it comes in blue." }
```

### FAQVisibilityView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/faq/{faq_code}/hide/` |
| **Permission** | `IsAuthenticated` + thing owner only |

Hides a FAQ. Sends notification email to questioner (includes thing headline only, no question text).

| | |
|---|---|
| **Endpoint** | `POST /api/v1/faq/{faq_code}/show/` |
| **Permission** | `IsAuthenticated` + thing owner only |

Shows a previously hidden FAQ.

---

## CSP Report View (`core/views/csp.py`)

### csp_report

| | |
|---|---|
| **Endpoint** | `POST /api/v1/csp-report/` |
| **Permission** | Anonymous — the reporter is a browser, and it sends no credentials. `@csrf_exempt` for the same reason |
| **Rate limit** | 30 requests/hour per IP |

Where the browser reports a Content-Security-Policy violation. It exists so that a blocked injection leaves a trace instead of failing silently — the CSP is the last net under `MarkdownText`, the one place the app hands the browser markup it did not write. Reports go to the `security` logger, alongside the auth events.

**First-party on purpose** (DESIGN §9): a hosted report collector would receive the URL of every page a member visits, which is exactly the tracking OIUEEI promises not to do.

**A plain Django view, not a DRF one**: browsers send `application/csp-report` or `application/reports+json`, which DRF's JSON parser rejects with a 415 before the handler runs.

**Always answers 204**, whatever arrives — the browser is not a client we owe an error to, and a report we can't parse is one to drop. Three guards keep the endpoint from becoming a liability of its own, since anyone can POST to it and browser extensions generate a lot of false reports:

- **Body cap** (`MAX_REPORT_BYTES`, 8 kB) — the log must not be a surface an anonymous POST can write megabytes into.
- **Field allowlist, each truncated** — only `violated-directive`, `effective-directive`, `document-uri`, `blocked-uri` and `script-sample` are logged (the two attacker-influenced ones get the shortest limits). A report can't smuggle its own payload into the log.
- **Newlines stripped** — `blocked-uri` is attacker-chosen, and a raw newline in it would forge extra `[SECURITY]` log lines.

Both report shapes are understood: the legacy `{"csp-report": {...}}` and a `report-to` batch (`[{"body": {...}}, ...]`, first entry only — the rest are repeats). Pinned by `core/tests/unit/test_csp_report.py`, whose negative assertions need the local `security_log` fixture: the `security` logger sets `propagate: False`, so plain `caplog` reads empty and every "must NOT be logged" test would pass vacuously.

---

## Upload Views (`core/views/upload.py`)

### UploadTicketView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/upload/ticket/` |
| **Permission** | `IsAuthenticated` |
| **Rate limit** | 30 requests/hour per user |

Hands the browser a short-lived ticket to write **one** object to the media
bucket, so the binary never routes through Django. That property is unchanged
from the Cloudinary signature endpoint this replaces; what changed is who
enforces the rules. Before, the server computed an HMAC over a set of upload
parameters and the client echoed them back. Now the rules are signed into a
presigned `PUT` URL, and the storage provider refuses the upload with
`SignatureDoesNotMatch` if any of them is altered in flight.

Four things are decided here and cannot be moved by the client:

- **the key** — `secrets.token_urlsafe(16)` inside the folder, so a client can't
  name its own object and overwrite somebody else's. The key's entropy is also
  what keeps a *public* object unguessable: the bucket is private and does not
  list, so knowing the key is the only way to reach the object;
- **the folder** — one of `oiueei/users`, `oiueei/things`, `oiueei/collections`
  in image mode, and `oiueei/documents` **forced** in document mode. Anything
  else falls back to `oiueei/users`, `oiueei/documents` included, so an image can
  never be written where documents live (S4);
- **the content type** — from an allowlist, signed exactly. Raster photo types
  only in image mode (**SVG is excluded** — it can carry script, and an
  `<img>`-rendered upload must never carry active content), `application/pdf`
  alone in document mode. Because it is signed rather than sniffed at read time,
  the type the bucket later serves is the type decided here — which is also what
  stops an upload coming back as `text/html` and turning the bucket into an XSS
  origin. It is not optional: an object stored without one is served as
  `binary/octet-stream`, and the welcome PDF then downloads instead of opening;
- **the size** — and this one is new. Cloudinary's signature computation
  *excluded* `max_file_size`, so signing it made ours diverge from theirs and
  every document upload failed with "Invalid Signature" (S3, a production
  outage). The cap had to live in `PdfUpload`, in the browser, where anyone could
  skip it. There is no such exclusion here: the client declares
  `content_length`, this view refuses anything over the limit, and the exact
  number is signed into the URL. Declaring one size and sending another — in
  either direction — fails the signature, and JavaScript cannot forge it because
  it may not set `Content-Length`. Limits: **5 MB** documents (the welcome doc's
  long-standing figure, now enforced where it can't be skipped), **10 MB**
  images — a backstop against abuse rather than a UX limit, since the browser
  downscales to 1216px first and a real upload lands in the hundreds of kB.

Any `kind` other than the literal `"document"` is an image upload, so an unknown
value can only ever narrow to the image defaults.

**Request body:**
```json
{ "folder": "oiueei/things", "content_type": "image/webp", "content_length": 183422 }
{ "kind": "document", "content_type": "application/pdf", "content_length": 812004 }
```

**Response:**
```json
{
    "url": "https://<bucket>.<endpoint>/<key>?X-Amz-Algorithm=...&X-Amz-Signature=...",
    "method": "PUT",
    "headers": {
        "x-amz-acl": "public-read",
        "Content-Type": "image/webp",
        "Cache-Control": "public, max-age=31536000, immutable"
    },
    "key": "oiueei/things/<random>"
}
```

`Cache-Control` is signed with the upload because there is no CDN in front of
the bucket — without it every visit is another round trip to the storage region.
It is safe to make it `immutable`: keys are random and an object is never
rewritten.

**Frontend upload flow:**
1. Call this endpoint with the file's type and byte length.
2. `PUT` the file as the **raw request body** (not multipart) to `url`, with
   exactly the `headers` given.
3. Store `key` in the relevant model field (`thumbnail`, `User.photo`, an entry
   in a Thing's `gallery`, or `Collection.welcome_doc`) — the response has no
   body to read a name out of, because the key was decided before the upload.

---

## Theeeme Views (`core/views/theeemes.py`)

### TheeemeListView

| | |
|---|---|
| **Endpoint** | `GET /api/v1/theeemes/` |
| **Permission** | `IsAuthenticated` |

Lists all available theeemes. Returns `code` and `name` for each theeeme via `TheeemeSerializer`.

---

## Booking Views (`core/views/booking.py`)

### ThingCalendarView

| | |
|---|---|
| **Endpoint** | `GET /api/v1/things/{thing_code}/calendar/` |
| **Permission** | `AllowAny` + `get_viewable_thing()` (public read on a viewable thing) |

Returns blocked periods for a thing's calendar. Owner sees full details (`BookingPeriodOwnerCalendarSerializer`), guests see only dates and status (`BookingPeriodCalendarSerializer`).

### MyBookingsView

| | |
|---|---|
| **Endpoint** | `GET /api/v1/my-bookings/` |
| **Permission** | `IsAuthenticated` |
| **Pagination** | `StandardResultsPagination` |

Lists all booking requests made by the current user, ordered by `-created`.

### OwnerBookingsView

| | |
|---|---|
| **Endpoint** | `GET /api/v1/owner-bookings/` |
| **Permission** | `IsAuthenticated` |
| **Pagination** | `StandardResultsPagination` |

Lists all booking requests for things owned by the current user, ordered by `-created`. Consumed by the frontend's **`/owner-bookings`** page — the owner's mirror of `/my-bookings`. (It was implemented and documented for a long time with no caller at all: an owner's only routes to a pending request were the email, an inbox banner, or opening each collection in turn.)

### BookingCancelView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/bookings/{booking_code}/cancel/` |
| **Permission** | `IsAuthenticated` + booking requester |

Allows the requester to cancel their own pending booking. Validates `booking.requester_code == request.user`, checks `is_valid()`. Calls `cancel_booking()` service (restores Thing status to ACTIVE for single-use types), and deletes related RSVPs.

**Responses:**
| Status | Condition |
|--------|-----------|
| 200 | Cancelled |
| 400 | Booking expired or already processed |
| 403 | Not the requester |
| 404 | Booking not found |

### BookingActionView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/bookings/{booking_code}/accept/` |
| **Permission** | `IsAuthenticated` + booking owner |

Accepts a pending booking. Validates `booking.owner_code == request.user`, checks `is_valid()`. Calls `accept_booking()` service, sends decision email via `send_booking_decision_email()`, and deletes related RSVPs (`BOOKING_ACCEPT`/`BOOKING_REJECT`) to invalidate old email links.

| | |
|---|---|
| **Endpoint** | `POST /api/v1/bookings/{booking_code}/reject/` |
| **Permission** | `IsAuthenticated` + booking owner |

Rejects a pending booking. Same permission and validation as accept. Calls `reject_booking()` service, sends decision email, and deletes related RSVPs.

**Responses:**
| Status | Condition |
|--------|-----------|
| 200 | Action completed |
| 400 | Booking expired or already processed |
| 403 | Not the booking owner |
| 404 | Booking not found |

---

## Reservation Views (`core/views/reservations.py`)

### ThingRequestView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/things/{thing_code}/request/` |
| **Permission** | `IsAuthenticated` + `thing.can_view()` + not owner |
| **Rate limit** | 10 requests/hour per user |

Creates a reservation/booking request. The view is **thin**: it runs the shared guards (auth, own-thing, availability, INACTIVE/paused collection, owner email) and validates the type-specific serializers, then dispatches to the `request_*` functions in `core.services.booking_service` (`request_date_based_booking`, `request_standard_booking`) which own the locked create + status transition + email fan-out. A business-rule failure raises `BookingRequestError(message, status_code)`, which the view maps back to `{"error": message}` with the same status. Routes based on thing type:

**Date-based (LEND/RENT):**
- Requires `start_date` and `end_date`.
- **Rental rules (#7):** resolves the applicable collection (the `collection_code` in the body — the SPA passes the collection context — else the thing's first collection with rules) and calls `collection.rental_violation(start, end)`. Returns 400 if the span isn't an allowed fixed duration or the pickup/return day isn't an allowed weekday. Collections without rules impose no constraint (legacy free range). This is the server-side backstop; the frontend already limits the picker.
- Checks for conflict via `BookingPeriod.has_overlap()` (**strict** overlap — a booking's return day may be the next's pickup day; only a shared interior day conflicts). Returns 409 if conflict.
- Thing stays `ACTIVE` (multiple bookings for different date ranges allowed).

**Request body:**
```json
{ "start_date": "2025-06-01", "end_date": "2025-06-15" }
```

**Standard (GIFT/SELL):**
- No extra fields required.
- Checks for existing pending request from same user. Returns 400 if duplicate.
- Thing status changes to `TAKEN` (blocks other requests).

**Common behaviour:**
0. Reads an optional **`collection_code`** from the body — the collection the requester was browsing. It already governed the rental rules (above); it now also decides which collection the owner's in-app notification belongs to, so the request shows up on the right collection's page (a thing can live in several — see `resolve_request_collection`). The SPA sends it from the card and the detail page whenever it has one; the standalone `/things/:code` page has none and the service approximates.
1. Validates owner email in the parent `post()` method (shared across all type handlers).
2. Creates `BookingPeriod` with status `PENDING`.
3. Creates two RSVPs (`BOOKING_ACCEPT` and `BOOKING_REJECT`) for the owner's email action links via `booking_service.send_booking_request_notifications()`.
4. Sends booking request email to owner with accept/reject links, and a confirmation email to the requester ("Hold request sent").

**INACTIVE collection enforcement:**
If all collections containing the thing are INACTIVE, the request is blocked with 400 "This collection is currently inactive".

**Paused collection enforcement:**
If all active collections containing the thing have a non-empty `pause_message` (i.e. are paused), the request is blocked with 400 "This collection is currently paused". Collections that are paused remain visible but no new hold requests are accepted.

**Responses:**
| Status | Condition |
|--------|-----------|
| 201 | Request created (booking `PENDING`) |
| 400 | Own thing / already pending / invalid data / collection inactive |
| 403 | Not authorised to view thing |
| 409 | Date overlap (date-based only) |

---

## Transfer Views (`core/views/transfers.py`)

### ThingTransferView

| | |
|---|---|
| **Endpoint** | `GET /api/v1/things/{thing_code}/transfers/` |
| **Permission** | `AllowAny` + `get_viewable_thing()` (public read on a viewable thing) |

Returns the transfer history (Loan Chain) and aggregate stats for a thing. **The four name fields are empty/null for a reader who is not signed in** (`` per hop, `null` for the two aggregates) — the counts and dates are the public story, the people are not; see the anonymous-read note under Security. The sample below is what a signed-in reader gets.

**Response (200):**
```json
{
  "total_transfers": 3,
  "unique_homes": 4,
  "current_holder": "ABC123",
  "current_holder_name": "Lala",
  "original_owner": "ABC123",
  "original_owner_name": "Lala",
  "transfers": [
    {
      "code": "XYZ789",
      "from_user": "ABC123",
      "to_user": "DEF456",
      "from_user_name": "Lala",
      "to_user_name": "Lele",
      "lent_date": "2026-04-01",
      "returned_date": "2026-04-10"
    }
  ]
}
```

**Behaviour:**
1. Looks up thing by `thing_code`. Returns 404 if not found.
2. Checks `thing.can_view(user_code)`. Returns 403 if not authorised.
3. Queries all transfers for the thing, ordered by `-lent_date`.
4. Computes `unique_homes` (distinct user codes across all `from_user` and `to_user` fields; NULL users — deleted accounts — count as at most one former home).
5. Computes `current_holder` from the most recent unreturned transfer's `to_user`.
6. Computes `original_owner` from the `from_user` of the oldest transfer (by `lent_date`). Null if no transfers.

---

## Report Views (`core/views/report.py`)

### ThingReportView

| | |
|---|---|
| **Endpoint** | `POST /api/v1/things/{thing_code}/report/` |
| **Permission** | `IsAuthenticated` + `thing.can_view()` + not owner |
| **Rate limit** | 10 requests/hour per user |

A logged-in member flags a thing as inappropriate (content moderation, #12).

**Behaviour:**
1. Returns 400 if the requester is the thing owner ("You can't report your own listing").
2. Returns 403 if the requester can't view the thing (`deny_if_cannot_view`).
3. `get_or_create` a `Report` for `(thing, reporter)` with a `thing_headline` snapshot — **idempotent per member**, so re-reporting the same thing doesn't create a second row or re-notify.
4. On the **first** report only: emails the owner (`send_thing_reported_email`, Cat. 2) and creates a `THING_REPORTED` `InAppNotification` (payload `thing_headline`, `thing_code`). Both are **anonymous** — the reporter's identity is never included.
5. Always returns `200 {"message": "Thanks — we've let the owner know."}` (the reporter can't tell whether it was their first report).

The reporter is stored server-side only (`Report.reporter`) as a moderation trail; see the [`Report` model](../models/CLAUDE.md#report) and `ReportAdmin` for the platform-facing log.

---

### Management Command: `close_transfers`

Daily command (`python manage.py close_transfers`) that closes overdue transfers:
- Finds unreturned `ThingTransfer` records linked to `ACCEPTED` bookings whose `end_date < today`.
- Sets `returned_date = today` **and `auto_closed = True`** via bulk update — the date is inferred from the due date passing, not confirmed by anyone, and the journey timeline renders those hops as "Due back on" rather than "Returned on".
- Outputs count of closed transfers.

### Management Command: `send_reminders`

Daily command (`python manage.py send_reminders`) that sends reminder emails:
- **Booking return reminders**: ACCEPTED bookings with `end_date = tomorrow` — notifies **both sides**, one email each: the owner (`send_return_reminder_email` — "somebody's hold ends tomorrow", nothing asked of them) and the **borrower** (`send_return_due_email` — "tomorrow you take it back", naming the owner they owe it to, with a link to the listing).
- The borrower's half was missing until the 2026-08 design round: only the owner was told a loan was ending, so the one person who actually had to do something — carry the drill back — heard nothing. A lending library runs on that message.
- The fan-out is per recipient and swallows a failure with a warning on stderr, so one broken send costs neither the other side their reminder nor the rest of the run theirs (same reasoning as `send_digests`).
- Outputs count of reminder emails sent (two per due booking).

### Management Command: `send_digests`

Daily command (`python manage.py send_digests`) that sends digest emails:
- **Weekly digests**: sent on Mondays for collections with `digest_frequency = "WEEKLY"`. Lists things added in the past 7 days.
- **Monthly digests**: sent on the 1st of each month for collections with `digest_frequency = "MONTHLY"`. Lists things added in the previous month.
- Skips collections with no new things or no invitees.
- Outputs count of digest emails sent.

### Management Command: `cleanup_orphan_images`

On-demand command (`python manage.py cleanup_orphan_images`) that deletes **orphaned images from object storage** (#9) — uploads whose form was never submitted, so no DB row ever referenced them (the complement to `core.services.asset_cleanup`, which handles record *deletes*). Superuser-run (there is no in-app endpoint — the shell/Heroku access is the gate).

- **Dry-run by default.** It only lists what it would delete; pass `--commit` to actually delete. On Heroku, quote the inner command so the CLI doesn't eat the flag: `heroku run --app <app> "python manage.py cleanup_orphan_images --commit"`.
- **Cross-references every DB image field** — `Thing.thumbnail` + `Thing.gallery`, `User.photo`, `Collection.thumbnail` — so anything in use is kept.
- **Never touches `oiueei/seed/`** (the demo's shared image pool), even if unreferenced.
- **Age window:** only assets older than `--min-age-hours` (default 24, so an in-flight upload mid-form isn't mistaken for an orphan) and younger than `--max-age-days` (default 30, keeping it a recent sweep). Run regularly (e.g. weekly) so every orphan is caught within its window.
- Pages through `storage.iter_objects` (prefix `oiueei/`), deletes in batches of 100 via `storage.delete_many`, and prints a per-run summary (scanned / in use / seed / outside window / orphans / deleted). The batch is kept well under S3's own limit of 1000 so a failed batch costs a hundred orphans rather than a thousand; a failure is reported and the run continues.
- The age window reads S3's `LastModified`, which for these objects **is** the upload time — a key is random, written once and never rewritten. That is why an object must never be overwritten in place: it would reset the clock and hide the object from the sweep for another day.

### Management Command: `purge_expired_data`

Enforces the retention table (GDPR art. 5.1.e): one period per category of data, each a `RETENTION_*` setting, **0 = keep indefinitely**. It **is** the sixth link of the daily Heroku Scheduler chain (README § Scheduled jobs, HEROKU.md § Scheduled jobs) — a period nothing enforces is a paragraph, not a retention policy. What protects you from arming it blind is that it is **dry-run by default**: an operator sets their own periods, runs it once by hand, reads the counts, and only then adds `--commit` to the chain. `cleanup_orphan_images` is the one that genuinely stays out of the chain.

- **Dry-run by default**, like `cleanup_orphan_images`; `--commit` applies it. The dry-run prints exactly the counts the commit would take.
- **Idempotent**: every step selects only rows still in the "before" state, so a second run is a no-op and a half-finished run can just be run again.
- **`Event` is anonymised, not deleted** (`actor_code` blanked at 14 months). What expires is the link to a person, not the fact — the series survives as aggregate and stops being personal data, which is what art. 5.1.e asks for. Deleting it would throw away the history to achieve the same thing.
- **Warned before anything happens — inactive accounts** (24m): sends the inactivity email and stamps `User.inactivity_notified`, from which the grace period is later counted. Skips anyone already warned (the stamp is what makes it idempotent), staff/superusers, and anyone holding a live `COLLECTION_INVITE` — telling somebody invited three days ago that their two-year-old account is expiring is true and useless. **A failed send leaves the stamp unwritten** so the clock never starts from an email that never arrived. Owning a live group does *not* skip the warning; it changes what the warning says (`send_inactivity_warning_email(..., will_delete=False)`), because an account that will not be deleted must not be told that it will. Coming back clears the stamp — `User.update_last_activity()` does it, which is the whole promise of the email.
- **Warned before anything is taken**, at most `--max-warnings` per run (default 200). The first armed run on an established database finds every dormant account at once and sends synchronously, so an uncapped one is a single dyno bursting thousands of SMTP calls at its own provider. Deferring costs nothing: the mark is written only on a successful send, so whoever is not reached tonight is a candidate again tomorrow, and each grace period is counted from that person's own warning — nobody is deleted un-warned by the cap. `--max-warnings 0` lifts it.
- **Deleted — inactive accounts**, once the grace period from the warning has run out. Two independent things must still be true and either one saves the account: the stamp is at least `RETENTION_INACTIVE_WARNING_DAYS` old **and** the account is still inactive. Coming back clears the stamp *and* refreshes `last_activity`, so somebody who did what the email asked is out of the queryset twice over — deliberate redundancy on an irreversible step. **An account that owns a collection with members is never deleted here**: `Collection.owner` is CASCADE, so erasing the founder of a working library takes the collection, its things and its photos from everyone who was still using it — a harm to everybody except the person who was actually inactive, decided by a nightly job. Those codes are printed for a human instead. Erasure goes through `account_service.delete_account`, the one written-down map of what dies with an account, so it leaves the same audit line a user-requested erasure does.
- **Deleted — guest accounts nobody ever answered for** (60d, T6): `get_or_create(email=...)` writes a `User` row the moment an owner types an address, so an unanswered invitation leaves a stranger's email here indefinitely. Five conditions, each with its own negative test: no `last_activity`, in no collection's `invites` (membership is written on **accept**, so a row there is a real member who simply hasn't been back — the trap this step is most likely to fall into), owns no collection and no thing, has no live `COLLECTION_INVITE` RSVP, and is not staff/superuser (a `createsuperuser` account that never used the SPA matches everything else). Note the RSVP condition is *absence*, not expiry: `cleanup_rsvps` deletes expired rows daily, so by the time this looks there is nothing expired to find and `User.created` is what dates it.
- **Deleted**: `DailyActivity` (26m), `InAppNotification` (12m), `Report` (12m from `created` — the model has no "resolved" state to date from, and adding one would be a moderation feature rather than a retention decision).
- Periods are counted in **calendar months**, not 30-day blocks (`months_ago()`, day clamped to the target month's length). A person whose data goes six days early has a point.
- A commit run logs its counts to the `security` logger: automated erasure leaves the same trail a user-requested one does.

---

### Management Command: `backfill_events`

One-off, idempotent seed of the `Event` log from existing rows (users → `USER_JOINED` at `date_joined`, collections/things/bookings at their `created`; accepted bookings also get `HOLD_ACCEPTED`). Run **once**, the day tracking ships, before forward instrumentation accumulates. Kept out of migrations per repo convention. Re-running never double-counts (skips when an equal event already exists).

---

## Data Export Views (`core/views/export.py`)

Two downloads, one service. Both return a plain `HttpResponse` attachment rather than a DRF `Response`: what these serve is a **file** — it has a name, a disposition and a caching rule that a rendered JSON body doesn't carry. The tree itself, and the reasoning about what never leaves it, lives in [`export_service`](../services/CLAUDE.md#export_servicepy--data-portability-right-to-a-copy); these views are the HTTP layer around it — who may ask, how often, and what the browser may do with the answer.

Both set `Content-Disposition: attachment; filename="oiueei-{code}-{date}.json"` and `Cache-Control: private, no-store`, and both log to the `security` logger with the size of what they served: a sudden change in what an export weighs is the first sign it started carrying something new.

### AccountDataExportView

| | |
|---|---|
| **Endpoint** | `GET /api/v1/auth/export/` |
| **Permission** | `IsAuthenticated` |
| **Rate limit** | 10 requests per day per user |

Your own data, as one JSON file — the self-service half of the right the privacy policy used to answer with "write to me" (GDPR art. 20). The twin of [`AccountDeleteRequestView`](#accountdeleterequestview): the same account page offers both, in that order, because reading your copy before erasing it is the sane sequence and the legally solid one.

### CollectionDataExportView

| | |
|---|---|
| **Endpoint** | `GET /api/v1/collections/{collection_code}/export/` |
| **Permission** | `IsAuthenticated` + collection owner (`require_collection_owner`) |
| **Rate limit** | 10 requests per day per user |

A whole group as its owner runs it, other members' things included. **A member gets 403, not a smaller file**: there is no partial export by design — "some of the group, depending on who asks" is a second access-control model to keep correct forever, and what a member is entitled to is their own account copy.

Deliberately not folded into the account export: a collection of 4,000 things would bloat every personal download, this button belongs beside the stats CSV, and keeping them apart lets the account copy stay honestly framed as *your* data while this one is what it is — an operational copy of a group, carrying other people's details, which the page has to say out loud.

**Query budgets.** `test_query_counts.py` pins both exports as constant in what they carry (a 200-thing group costs the same queries as a 5-thing one) plus a size ceiling on the 200-thing case — the half a query count can't see, and the reason photos travel as URLs rather than bytes. An N+1 here isn't a slow page; it's a 30-second Heroku timeout on the one request somebody makes when they're already unhappy enough to be leaving.

---

## Middleware (`core/middleware.py`)

- **`SecurityHeadersMiddleware`** — adds CSP + Permissions-Policy to every response (all environments). The CSP names a violation collector in both syntaxes (`report-uri` and `report-to`, the latter resolved by the `Reporting-Endpoints` header) pointing at `csp_report` below. It also names the asset hosts, and **two of them, from two settings**: `img-src` gets `MEDIA_PUBLIC_BASE_URL` (where files are read from), `connect-src` gets that *and* `OBJECT_STORAGE_PUBLIC_URL` (the bucket, where a presigned `PUT` always goes — it does not follow a CDN). Deriving the second from the first is what made `MEDIA_PUBLIC_BASE_URL=https://cdn.example.com` forbid every upload while the images already stored kept loading; `test_upload.py::TestTheBrowserIsActuallyAllowedToUseTheTicket` asks the question the browser asks, so the two cannot drift apart again.
- **`DailyActivityMiddleware`** — records the authenticated user's daily activity (see [`DailyActivity`](../models/CLAUDE.md#dailyactivity)). Registered **innermost** so it can read the DRF-authenticated `request.user` *after* the view (there is no Django session — auth is JWT-cookie via DRF authenticators, so `request.user` only resolves once a view/permission touches it). A DatabaseCache key gates it to one write per user per day; failures are swallowed so tracking can never 500 a good response. Anonymous / non-DRF requests are skipped.

---

## Custom Permissions (`core/permissions.py`)

| Permission | Logic |
|-----------|-------|
| `IsThingOwner` | `obj.owner_id == request.user.code` |
| `IsCollectionOwner` | `obj.owner_id == request.user.code` |

---

## Security

### Authentication & Authorisation

1. **Invite-only registration, owner-controlled, with no open door** — there is no public self-registration. An account is created when a collection owner invites someone (`POST /collections/{code}/invite/`), or when a visitor joins a collection they were pointed at (`POST /auth/join/`, with a `share_token` from `/share/{token}` or the code of a PUBLIC collection). Both are somebody choosing to admit a specific person. `/login` (`POST /auth/request-link/`) only mails links to already-registered accounts and never creates users, and `/auth/join/` creates nothing without a valid target — so no request to this API mints an account that belongs to no group. A deployment that *wants* an open door adds one from its own URLconf (`DEPLOYMENT_URLCONFS`); it is not part of what is distributed.
2. **Magic link authentication** — Passwordless via email. RSVPs are one-time use and expire per action (magic links 24h; booking accept/reject 72h; collection invites ~30 days — `RSVP.expiry_hours_for`).
3. **JWT tokens** — HttpOnly cookie-based. Access tokens expire after 1 hour. Refresh tokens expire after 7 days. Tokens are rotated on refresh via `POST /api/v1/auth/refresh/`, old tokens blacklisted.
4. **CSRF (cookie auth)** — because the access token rides in a cookie, `CookieJWTAuthentication` runs DRF's CSRF check (`enforce_csrf`, mirroring `SessionAuthentication`) for **cookie-authenticated unsafe methods** — defence in depth behind the cookie's `SameSite=Lax`. Bearer-header auth is exempt (the header is never sent cross-site), so API clients and the Bearer-token test suite are unaffected. `MeView` GET sets the `csrftoken` cookie via `@ensure_csrf_cookie` (hit on every app load); the SPA reads it and sends it as `X-CSRFToken` on every unsafe request. The test client disables the check by default (`enforce_csrf_checks=False`), so only `test_csrf.py` (which opts in) exercises it.
5. **IDOR protection** — `can_view_user()` ensures users can only view profiles of people connected via collections.
6. **Custom DRF permissions** — `IsThingOwner` and `IsCollectionOwner` in `core/permissions.py`.
7. **Public collections (anonymous read)** — a collection with `visibility=PUBLIC` (and ACTIVE) is readable without authentication. The read endpoints `CollectionViewSet.retrieve`, `ThingViewSet.retrieve`, the FAQ list (GET on `ThingFAQListView`), `ThingTransferView` and `ThingCalendarView` are `AllowAny`, each gated by an **anonymous-safe** `can_view` (a `viewer_code(request)` helper passes the user's code, or `None` for a visitor, into the model guard — `None` matches PUBLIC collections only). Every *write/act* endpoint (reserve, ask a question, answer, add a thing, manage invites/visibility) still requires authentication plus membership/ownership, so an anonymous visitor may browse a public collection but must log in to act. INACTIVE things are excluded from the serialised `things` for any non-owner, the member roster serialises **codes only** for anonymous readers (names are for logged-in members; emails for the owner), and the collection *list* (`GET /collections/`) stays private (it returns only the caller's own collections).

**No member is named to an anonymous reader, by any of these endpoints.** The roster rule above is the whole rule, and it took three passes to actually be: the FAQ list still carried `questioner_name` and the journey still carried the name of everyone who had held the thing, so a group's membership stayed legible from the open web through a thing rather than through the collection. Both now withhold (`FAQSerializer.get_questioner_name`, `core/serializers/transfer.py::_may_read_names`), both fail closed on a request-less context, and both keep the *content* public — the question, the hop count, the travel story. The third door was the grid itself: in COMMUNITY mode every card carries `owner_name`, the member who **contributed** the thing, so a group's membership stayed enumerable from the open web after both other doors had closed. `ThingComputedFieldsMixin.get_owner_name` now withholds it from a signed-out reader **whenever the thing's owner is not the collection's owner** — the leak stated exactly, with no mode check to drift. The one name such a reader still gets is the **curator's**, the person who published the collection: `CollectionSerializer.get_owner_name` already serves it to them in the page header, so withholding it on that person's own listings would be theatre. They chose to publish; the member who contributed, the person who asked and the people who borrowed did not.

### Input Validation

1. **Image IDs** — Only alphanumeric characters, underscores, hyphens, dots and slashes; no traversal. Each field is also **bound to its own folder** (`ImageIdField(folder=…)` → `validators.validate_key_folder`): the upload ticket refuses to sign a write outside a known folder, but the key that lands on the model arrives in a *separate* request, so nothing tied the two together — a member could put a collection's welcome PDF into their own `photo` and republish a document its owner shared with one group. The rule is deliberately narrow, refusing only a key naming one of the **other** `storage.ASSET_FOLDERS`: a bare Cloudinary-era id, an `oiueei/seed/` fixture (the demo's shared pool legitimately backs every kind of row) and any unknown namespace still save, because the guard arrived years after the keys did and refusing them would strand rows whose photo works perfectly.
2. **Headlines** — HTML tags rejected to prevent XSS.
3. **Quantities** — Order quantities capped at 99.
4. **Dates** — Start dates must be today or future. End dates must be >= start dates.
5. **Email HTML** — All user content escaped via `django.utils.html.escape()` in `email_service.py`.

### Mass-upload guards (per collection)

Independent of the rate limits below, and **off unless the deployment sets thresholds** — the standalone default. Two counters per collection, things and invitees, each with:

- a **silent alarm** (`COLLECTION_THINGS_ALARM` / `COLLECTION_INVITES_ALARM`) that emails the **superusers** once and changes nothing. The owner is never told: a tripwire, not a warning, so a legitimate bulk import is not interrupted and someone probing the endpoint does not learn where the line sits.
- a **hard ceiling** (`COLLECTION_THINGS_BLOCK` / `COLLECTION_INVITES_BLOCK`) that refuses adds with **400**, checked against the whole batch so bulk cannot walk past it. A superuser lifts it per collection with `capacity_unblocked` in the admin — there is no API.

Enforcement points: things — `ThingViewSet.create` (before the row is created), `ThingBulkCreateView` (whole batch, all-or-nothing), `CollectionViewSet.add_thing` (so moving an existing thing is not the unguarded door). Members — `CollectionInviteView` and `CollectionBulkInviteView`, enforced where invitations are **sent** rather than accepted (refusing an invitee at the door would punish someone who did nothing wrong); the alarm fires from `_join_collection`, the single funnel every join path goes through.

**The ceiling counts what would land, not what was typed.** `adding` is the number of rows that genuinely move the counter, so both invite endpoints check *after* validation and dedup and exclude addresses that are **already members** — those sit inside the count the ceiling measures, and counting them again refused batches that added nobody (a re-invite at the ceiling now falls through to the accurate "already invited" 400). The thing paths count `len(validated)` for the same reason. All of it is gated on `Collection.capacity_ceiling()`, so a deployment with no thresholds runs no extra query.

**Concurrency.** `ThingBulkCreateView` re-checks under a `select_for_update()` on the collection row inside its transaction — one request there can carry up to `MAX_ROWS`, so two arriving together could otherwise land 200 rows through a ceiling of 100. The single-add paths accept a drift of at most one row per racing request and take no lock: a ceiling this coarse doesn't earn serialising every add to a busy COMMUNITY collection. The **invite** paths need no lock at all — they send invitations, they don't add members, so the count they read only moves when someone accepts, which is deliberately never refused.

### Rate Limiting

- `/auth/request-link/` — 5 requests per minute per IP **and** 5 per hour per account (email)
- `/auth/join/` — 5 requests per minute per IP **and** 5 per hour per account (email)
- Joins per **collection** — **unlimited unless the operator sets `COLLECTION_JOINS_PER_DAY`** (0/unset = off). The one door that needs no account, reached by a public collection code or a shared token; the two IP/email limits above cap one caller and one victim, this caps the relay
- `/auth/verify/{token}/` — 10 requests per minute per IP
- `/collections/{code}/invite/` POST — 30 requests per hour per user
- Invitation **emails** (single + bulk combined) — **unlimited unless the operator sets `INVITE_EMAILS_PER_DAY`** (counts emails, not requests, so the bulk fan-out can't multiply past it; 0/unset = off)
- `/things/{code}/request/` POST — 10 requests per hour per user
- `/things/{code}/faq/` POST — 20 requests per hour per user
- `/collections/{code}/broadcast/` POST — 5 requests per day per user
- `/collections/{code}/share-link/` POST — 30 requests per hour per user
- `/things/{code}/report/` POST — 10 requests per hour per user
- `/notifications/token/{t}/` — GET 20/min per IP, PATCH 10/min per IP
- `/things/` POST (single create) — 60 requests per hour per user (so the 10/h bulk cap can't be bypassed one-by-one into unbounded rows)
- `/collections/` POST (single create) — 30 requests per hour per user
- `/collections/{code}/add-thing/` POST — 60 requests per hour per user
- `/collections/{code}/join/` POST — 30 requests per hour per user (plus the per-collection daily ceiling)
- `/collections/{code}/leave/` POST — 30 requests per hour per user
- `/auth/delete-account/` POST — 3 requests per hour per user
- `/auth/export/` GET — 10 requests per day per user
- `/collections/{code}/export/` GET — 10 requests per day per user. Building an export is the heaviest read in the app; the cap is what keeps "download my data" from being a way to walk a server out one file at a time
- `/contact/` POST — 5 requests per hour per IP
- `/csp-report/` POST — 30 requests per hour per IP (violation reports; browser extensions make these noisy)
- `/health/` GET+HEAD — 60 requests per minute per IP. The only anonymous endpoint that reaches the database on every hit, so uncapped it is DB amplification rather than a monitor. Far above a real monitor's cadence (5 minutes = 0.2/m). It is a plain Django view, so it answers **429 itself** (`block=False` + `request.limited`) rather than letting `Ratelimited` surface as Django's 403 — DRF's exception handler doesn't run here

**Which IP a limit buckets on** is decided by `core.utils.get_client_ip` (wired in via `RATELIMIT_IP_META_KEY`), and by `TRUSTED_PROXY_COUNT`: how many proxies in front of the app are trusted to have appended to `X-Forwarded-For`. The entry is counted from the **right**, because only the tail of that header was written by a proxy we control — the rest is the caller's own text. Default `1` = the Heroku router. **A deployment with nothing trusted in front must set `0`**, or the header is entirely caller-supplied and one caller mints a fresh bucket per request, defeating every limit above. The chosen entry is validated as an IP before it is returned: django-ratelimit feeds it to `ipaddress.ip_network()`, so an unparseable value used to raise `ValueError` *inside the decorator* — a 500 on every limited endpoint from one header, before the view ran. Anything unparseable falls back to `REMOTE_ADDR`, then to a single shared bucket (`UNKNOWN_CLIENT_IP`), never to a fresh allowance.

### Secure Code Practices

1. **ID generation** — Uses `secrets.choice()` for cryptographically secure random IDs.
2. **SECRET_KEY** — Required from environment variable, not hardcoded.
3. **RSVP obfuscation + high-entropy links** — Email/magic links carry the RSVP's 26-char (~134-bit) `token` via `generate_token()`, never the 6-char PK or real object codes, so they resist both enumeration and brute force.
4. **Security logging** — Auth events logged with IP addresses.
5. **Production hardening** — HSTS, secure cookies, SSL redirect, custom admin path, JSON-only renderer.
6. **Data exports carry no credentials** — the two endpoints in `core/views/export.py` serve files people forward and leave on laptops, so `Collection.share_token` and every `RSVP.token` are absent from the bytes (pinned by tests that read the raw bytes, not the tree). They are `no-store` and owner-scoped: an account copy is only ever your own, and a collection copy is owner-only with no partial variant.

---

## Architecture Notes

### View Patterns

- All views use `get_object_or_404` for consistent 404 responses.
- `ThingViewSet` and `CollectionViewSet` use DRF `ModelViewSet` with `DefaultRouter`.
- `ThingUpdateSerializer` has `status` as read-only to prevent direct status manipulation. `type` is editable. Use `POST /api/v1/things/{code}/activate/` to set status ACTIVE (from INACTIVE), and `POST /api/v1/things/{code}/hide/` to set status INACTIVE (from ACTIVE only).
- `ThingSerializer` and `CollectionThingSummarySerializer` include `pending_booking` (first PENDING booking code, or null) and `pending_questions` (count of unanswered FAQs).
- Accept/reject actions can be performed via the unified RSVP endpoint (`VerifyLinkView`) for email links — **a POST commits, GET only previews** (booking decisions never fire from a bare GET) — or via authenticated `BookingActionView` endpoints for in-app use. Both paths reuse the same `accept_booking()`/`reject_booking()` service functions.
- All email links use RSVP codes as intermediaries to avoid exposing real object codes in URLs.
- Security events are logged to the `security` logger with IP addresses.

### Service Layer

Business logic is extracted into `core/services/`:
- `join_quota.py` — The per-collection daily cap on `POST /auth/join/` (`COLLECTION_JOINS_PER_DAY`), the one door that needs no account. Off by default.
- `creator_policy.py` — Whether this deployment lets an account open a collection in a given mode or offer a thing under a given verb (`CREATOR_POLICY`; open to everyone in the standalone). Enforced at five doors — collection create/update, thing create/update, bulk import — and served to the SPA as `capabilities` on `GET /auth/me/`. Gates *initiating*, not a member *contributing* an owner-allow-listed type to a COMMUNITY collection they were invited to (`community_contribution_types`).
- `email_service.py` — All email HTML composition and sending (21 `send_*` functions). Uses `django.utils.html.escape()`.
- `booking_service.py` — `accept_booking()`, `reject_booking()`, and `cancel_booking()` handle status transitions for Thing and BookingPeriod, wrapped in `transaction.atomic()`. The reservation-**request** side lives here too: `request_share_booking()`, `request_date_based_booking()`, `request_standard_booking()`, and `request_swap_booking()` (plus `resolve_rental_collection()` and the `send_*_request_notifications()` email/notification helpers). They raise `BookingRequestError(message, status_code)` on a rule violation; `ThingRequestView` catches it and returns `{"error": message}`.

### Utilities

- `core/utils.py`: `generate_id()`, `get_client_ip()`, `asset_url()` — `asset_url(key)` joins the stored key onto `MEDIA_PUBLIC_BASE_URL` via `core.services.storage.public_url`. It replaced a Cloudinary SDK call that asked for `fetch_format=auto`/`quality=auto`; an object store does not transform, so that job moved to the browser, which encodes to WebP before uploading.
- `core/validators.py`: `ImageIdField`, `SafeHeadlineField`, `SafeTextField`, `validate_image_id()`, `validate_headline()`
- `core/pagination.py`: `StandardResultsPagination` (max 100 items)
- `core/views/_helpers.py`: `viewer_code()`, `deny_if_cannot_view()`, `get_viewable_thing()`, `type_validity_error()`, `require_collection_owner()`, and **`body_dict(request)`** — `request.data` when the body is a JSON object, else `{}`. DRF parses a JSON *array* body into a `list`, which has no `.get`, so any view reading `request.data.get(...)` **before a serializer has run** answers 500 where it owes a 400. Use it on every such read; a non-object body then means "no fields given" and falls through to the view's own validation. Pinned by `core/tests/integration/test_array_body.py`.
