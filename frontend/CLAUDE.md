# OIUEEI Frontend Documentation

React frontend using HDS (Helsinki Design System) from npm with OIUEEI customization layer (fonts, colors, icons). Vite dev server on `localhost:3000`. All API requests are proxied to the Django backend on `localhost:8000`. All UI strings are externalised via `react-i18next` (British English, `src/i18n/locales/en.json`).

---

## Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | `HomePage` | Dashboard: My collections + Shared with me (collection Linkbox grid) |
| `/login` | `LoginPage` | Email input form for requesting a magic link |
| `/logout` | `LogoutPage` | Clears auth cookies and localStorage, redirects to `/login` |
| `/verify/:code` | `VerifyPage` | Processes magic link / RSVP verification |
| `/rsvp/:code` | `VerifyPage` | Alias for /verify/:code |
| `/magic-link/:code` | `VerifyPage` | Alias for /verify/:code |
| `/me` | `UserPage` | Own profile (fetches userCode from `/auth/me/` if needed) |
| `/me/edit` | `EditProfilePage` | Edit own profile |
| `/me/data` | `DataExportPage` | Self-service data portability (GDPR art. 20): states what the download carries and what it deliberately leaves out (the mirror of `DeleteAccountPage`), then one button — `GET /auth/export/` → blob → download, no confirmation step (unlike erasure, a copy is reversible by construction). Linked from `EditProfilePage` next to "delete account", and from the top of `DeleteAccountPage` itself — read before you erase is the sane order and the legally solid one |
| `/me/delete` | `DeleteAccountPage` | Right-to-erasure entry: states what is deleted / what stays, then emails the 24h confirmation link (`POST /auth/delete-account/`). Nothing is deleted here. Leads with a quiet notice pointing at `/me/data` first (S5, 2026-08) |
| `/me/notifications/:token` | `NotificationsPage` | Manage email preferences via a signed (`TimestampSigner`, ~1y TTL) token from the email footer link. Without `:token` redirects to `/me/edit`. |
| `/collections/new` | `CreateCollectionPage` | Create a new collection |
| `/collections/:code` | `CollectionPage` | Collection detail with things and invites. **Public route** — anonymous read when the collection is PUBLIC (gated server-side by `can_view`). |
| `/collections/:code/edit` | `EditCollectionPage` | Edit a collection |
| `/collections/:code/delete` | `DeleteCollectionPage` | Confirm and delete a collection |
| `/collections/:code/invites` | `ManageInvitesPage` | Manage collection invites |
| `/collections/:code/add` | `AddThingPage` | Add a thing to a collection |
| `/collections/:code/things/:thingCode` | `ThingPage` | Thing detail page with FAQs (from collection context). **Public route** — anonymous read on a PUBLIC collection. |
| `/collections/:code/things/:thingCode/edit` | `EditThingPage` | Edit a thing (from collection context) |
| `/things/:thingCode` | `ThingPage` | Thing detail page with FAQs (standalone). **Public route** — anonymous read on a PUBLIC collection. |
| `/things/:thingCode/edit` | `EditThingPage` | Edit a thing (standalone) |
| `/collections/:code/things/:thingCode/request` | `RequestThingPage` | Request page for date-based things — LEND/RENT (collection context) |
| `/things/:thingCode/request` | `RequestThingPage` | Request page for date-based things — LEND/RENT (standalone) |
| `/collections/:code/things/:thingCode/delete` | `DeleteThingPage` | Confirm and delete a thing (collection context) |
| `/things/:thingCode/delete` | `DeleteThingPage` | Confirm and delete a thing (standalone) |
| `/collections/:code/invites/remove` | `RemoveGuestPage` | Confirm and remove a guest from a collection |
| `/collections/:code/leave` | `LeaveCollectionPage` | Confirm and leave a collection you're an invited member of (self-unlink) |
| `/my-bookings` | `MyBookingsPage` | Lists user's booking requests with cancel option |
| `/owner-bookings` | `OwnerBookingsPage` | The owner's mirror: every request made **on their things**, answerable from here (accept / reject per row). Accepting a GIFT/SELL that isn't endless opens a confirmation `Dialog` first — that acceptance hands the thing over permanently (`thing_is_endless` on the booking serializer is what distinguishes it from an endless gift, which transfers nothing). Closes the asymmetry where the requester had a list and the owner had only the email, an inbox banner, or opening each collection. Uses the long-existing, previously uncalled `GET /api/v1/owner-bookings/`. Linked from HomePage, and only for users who own at least one thing — owning a *thing* is the test, not a collection, since a COMMUNITY member can be asked for something they contributed to someone else's group |
| `/shared` | `SharedThingsPage` | Everything the groups you belong to are sharing, newest first, from `GET /api/v1/invited-things/` — an endpoint that shipped documented and **uncalled**, the same asymmetry `/owner-bookings/` had. A member of five collections could only see what was in them by opening each in turn, which is also the question the weekly digest answers by email and the app could not answer at all. Reached from a quiet line under HomePage's "Shared with me" grid, deliberately **not** a fifth hero button (DESIGN §3) |
| `/share/:token` | `SharePage` | Public collection share-link landing: enter email, get magic link, join the collection identified by `:token` |
| `/collections/:code/join` | `JoinPage` (fetches the public collection itself so its name survives a refresh or a shared /join URL — `ThingLinkbox` is the only caller that passes it in navigation state, so the hero's own "Join to take part" link used to ask a stranger to join "Collection") | **Public route** — login-to-act landing for a PUBLIC collection. An anonymous visitor who clicks an action button (Claim / Buy / Rent / Borrow) on a public collection lands here; enters email → `/auth/join/` joins them to `:code` + magic link → after verifying they're dropped back on the collection, able to act. |
| `/contact` | `ContactPage` | **Public route** — the support channel (a locked-out user is the main case): name (optional) + reply email + message → `POST /api/v1/contact/` (forwarded to the operator, Reply-To = sender) → success `Notification`. Reached from the `ContactCorner` speech-bubble in every hero and the "trouble signing in?" line on LoginPage. Both this and `/collaborate` render the shared **`ContactFormPage`** component (`src/components/ContactFormPage.jsx` — the `MagicLinkJoinPage` pattern: per-page `docTitleKey`/`titleKey`/`introKey` + `kind` + optional footer children) |
| `/collaborate` | `CollaboratePage` | **Public route** — the collaborate door (design, product, code, beta-testing; open-source / social-economy folks): same shared form as `/contact` posting `kind: "collab"` (the operator's inbox subject differs). Linked from ContactPage |
| `/digest/mute/:token` | `DigestMutePage` | **Public route** — the one-click unsubscribe in every digest footer. Silences that one collection's summaries for that one member. The POST fires from JS on mount (never from the email's GET, so a link scanner can't unsubscribe anyone) against `POST /api/v1/digest/mute/{token}/`; no login, because this is the unsubscribe and it has to work for someone who forgot they have an account |
| `/legal` | `LegalPage` | **Public route** — commitment (manifesto), legal notice, privacy and basic terms, in the reader's language. Content lives in `src/legal/{es,ca,en}.js` (Markdown via `MarkdownText`): the standalone repo ships a generic operator-neutral text (each self-hoster is their own data controller and must fill in their identity); the official www.oiueei.com deploy branch replaces those files with the full RGPD/LSSI version. Linked from LoginPage (under the manifesto line) and the site footer |
| `/:userCode` | `UserPage` | Displays a user's public profile |
| `*` | `NotFoundPage` | 404 page for unknown routes |

**Public read of PUBLIC collections (anonymous visitors):** `/collections/:code`, `/collections/:code/things/:thingCode` and `/things/:thingCode` sit in the **public** route block (outside `RequireAuth`). The backend's `can_view` gates them, so only PUBLIC, ACTIVE collections are readable without a session. When unauthenticated, `CollectionPage` shows the thing **action buttons as usual** (via `ThingLinkbox`'s `loginToAct` prop — passed `!isAuthenticated`): the cards look the same as for a member, but each action's click (Claim / Buy / Rent / Borrow — the per-type verbs in `thingCard.action`) **navigates to `/collections/:code/join`** (`JoinPage`) instead of performing it. There the visitor enters their email → `/auth/join/` with the collection code joins them to the PUBLIC collection and emails a magic link; because the join stamps the collection as the RSVP `target_code`, verifying the link **drops them back on the collection** (`_handle_magic_link` returns `invited_collection`), now a member who can act. `ThingLinkbox` also still accepts a `canAct` prop (used elsewhere); `loginToAct` is the anonymous-on-public mode. **`ThingPage`, the standalone detail view, uses the same login-to-act pattern**: an anonymous visitor sees the reserve button (via `useThingActions`' `loginToAct` option, set to `!isAuthenticated && !!collectionCode`), and its click **navigates to `/collections/:code/join`** rather than showing an inline prompt. (The `JoinToAct` component now renders only inside `JoinPage`.) The owner sets a collection's PUBLIC/PRIVATE state with the **visibility toggle** in the Create/Edit forms (rendered by `CollectionForm`), defaulting by mode on create (COMMUNITY→public, PROPRIETARY→private); a Public/Private `Tag` is shown to the owner in the `CollectionPage` hero. **Anonymous intro (design round):** a signed-out visitor also gets a quiet one-line hint in the hero, right after the owner-attribution block — "This group shares its things on OIUEEI." + a "Join to take part →" link to `/collections/:code/join` (`collectionPage.anonIntro`/`anonIntroLink`, reusing the `.invite-nudge`/`.owner-link` classes) — so the top of the viral funnel names the product instead of relying on a visitor clicking an action button first.

---

## Page Titles

Every page sets `document.title` via `useEffect` for meaningful browser tab titles and bookmarks. Dynamic pages (CollectionPage, ThingPage, UserPage, etc.) update the title when data loads. Format: `{Page context} — OIUEEI`.

---

## Page Layout Pattern

All pages use a consistent `form-hero` + `Koros` layout (the HDS Hero component is not used):

```
form-page
├── form-hero          (full-width, theeeme color_03 background)
│   ├── form-hero-content  (max-width 1248px, text color from --hero-text-color CSS var using theeeme color_05)
│   │   └── [back link, title, description]
│   ├── ::after         (OIUEEI logo watermark, 40px — see below)
│   └── Koros          (HDS Koros component, type from user.koro preference, 60px height, fill = theeeme color_02)
└── page-container     (max-width 1248px, page content)
```

**Site footer (i14):** a global one-line colophon (`SiteFooter`, mounted once in `App.jsx` after `<main>`): "Made with ♥︎ in Zona Franca, Barcelona, Catalonia, Spain, EU" (`footer.madeIn`, ×3 locales). Painted with the viewer's theeeme `color_02` (same token as `.form-page`'s background) so there is no colour seam; `useLocation()` re-renders it per navigation so a theeeme change is picked up. The heart is U+2665+U+FE0E (text presentation — inherits colour, never a red emoji). **It also carries links** (`footer.legal` → `/legal` always; `footer.about` → `deployment/aboutPath` only where that deployment has a page saying what it is — upstream it is null and the link is absent, since a footer link to a 404 is worse than one link fewer). `/legal` is the page the privacy claims say to go and check, and every link to it used to sit behind a login or on a page only a joiner sees, so someone reading a public collection — the top of the whole funnel — could not reach it. Plain text links, not a nav block. **Deliberately not HDS `Footer`** (a recorded exception to DESIGN §1, not an oversight): that component is a full navigation block with link columns, a logo row and a back-to-top control — this is one line of colophon, and adopting it would import the site-map footer OIUEEI has no content for (DESIGN §3: ask what can be removed).

**Contact corner (i8):** every hero also carries `ContactCorner` (`src/components/ContactCorner.jsx`) — a quiet `IconSpeechbubbleText` link to `/contact` (44px target, `aria-label`/`title` from `contact.linkLabel`), rendered as the first child of `.form-hero-content` (so `--hero-text-color` resolves and it stays visible on dark theeemes, like the back link) and absolutely positioned against `.form-hero`: just left of the logo watermark at ≥768px, at the content column's right edge on photo/no-watermark heroes and below `breakpoint-m` (`.contact-corner` in App.css). Inserted in `PageLayout` plus the 8 manual-hero pages.

**OIUEEI logo in the hero (S9):** brand presence via `public/oiueei-logo.svg` (monochrome, 566×161 — the viewBox matches the art's real bounds; a 556×161 viewBox shipped initially and clipped the wordmark's last glyph, fixed in the 2026-07-13 round, S5), tinted with a CSS `mask` so it inherits whatever colour var is in scope — the same technique for both uses below).

- **Watermark** — every `form-hero` gets a `::after` pseudo-element (40px tall, ~138px wide, `App.css`), anchored to the right edge of the hero's *content column* at every width (`right: calc((100% - min(100%, 1248px)) / 2 + var(--spacing-s))`, matching `.form-hero-content`'s own centring math, not the raw viewport edge), filled `var(--hero-logo-color, var(--color-black-90))` — theeeme `color_02`, exposed via inline style on `.form-hero` itself (same mechanism as `--hero-text-color`) in `PageLayout.jsx` and the 8 pages that build a hero manually (`CollectionPage`, `HomePage`, `JoinPage`, `LoginPage`, `NotFoundPage`, `UserPage`, `VerifyPage`). Decorative only — a pseudo-element has no accessibility surface. Suppressed below `breakpoint-m` (767px, collision risk with wrapped hero text — unverified without a live viewport) via `.form-hero--photo::after`/`.form-hero--no-watermark::after` (see below).
- **Title replacement** — the one hero `<h1 class="form-hero-title">` whose text is the *literal* string "OIUEEI" (verified by grep across every locale: only `login.title` — `share.pageTitle` is "Join us on OIUEEI", `notFound.title` is "Page not found", neither qualifies) renders `.form-hero-title-logo` (80px, `var(--hero-text-color)` — white on `/login`) instead of the text, and the `<h1>` carries `aria-label={t('login.title')}` so the accessible name survives. That page's `.form-hero` also gets the `form-hero--no-watermark` modifier class so there's never a double logo.
- **Hero-photo pages (S7/S8)** — the watermark is suppressed there too (`.form-hero--photo::after { display: none }`): whether it stays legible over the diagonal-wedge/photo composition can't be confirmed without a screenshot, so this errs conservative rather than risk an illegible logo.

### Theeeme Color Roles

| Token | Role |
|-------|------|
| `color_01` | Primary button background + secondary button border |
| `color_02` | Body background + Koros SVG fill + hero logo watermark (`--hero-logo-color`) |
| `color_03` | Koros section background |
| `color_04` | Body text + secondary button text |
| `color_05` | Koros text (title, description, back-link) via `--hero-text-color` |
| `color_06` | Primary button text |

All buttons across the app use theeeme colors (`btnStyle` for primary, `btnSecondaryStyle` for secondary). Secondary buttons always have a white background; `color_01` drives the border and `color_04` the text.

Pages using this pattern: HomePage, CollectionPage, CreateCollectionPage, EditCollectionPage, EditProfilePage, ManageInvitesPage, MyBookingsPage, EditThingPage, ThingPage, RequestThingPage, DeleteThingPage, RemoveGuestPage, UserPage.

---

## Breakpoints

OIUEEI follows the official [HDS breakpoint tokens](https://hds.hel.fi/foundation/design-tokens/breakpoints/). HDS defines six breakpoints; OIUEEI uses four of them and intentionally skips `breakpoint-s` (576px) and `breakpoint-xxl` (1440px). Use only these exact `min-width` values in media queries — never use arbitrary pixel values.

| Token | Min-width | Container width | HDS grid columns | Margin |
|---|---|---|---|---|
| `breakpoint-xs` | 320px | 288px | 4 | 16px |
| `breakpoint-m` | 768px | 720px | 8 | 24px |
| `breakpoint-l` | 992px | 944px | 12 | 24px |
| `breakpoint-xl` | 1248px | 1200px | 12 | 24px |

The `page-container` and `form-hero-content` max-width is **1248px** (aligned with `breakpoint-xl`). The complementary `max-width: 767px` query (below `breakpoint-m`) is also valid for mobile-only overrides.

**Wide content scrolls inside itself, never the page body.** `hds-react` ships `.Table-module_container { height: inherit }` and no `overflow-x`, so a native `<table>` sizes to its content and pushes the body past the 288px xs container. Every HDS `Table` therefore sits in a **`.table-wrap`** (`overflow-x: auto`, App.css) — `MyBookingsPage`, `OwnerBookingsPage` and `ManageInvitesPage`, five in all. Markdown pipe tables in a bio have their own `.markdown-table-wrap` for the same reason. No `tabindex` on either: the rows carry links and buttons, so a keyboard reaches the off-screen columns by tabbing in.

---

## PWA

The app ships a web app manifest (`public/manifest.webmanifest`) plus icons (`public/oiueei-icon-192.png` / `-512.png` — the orange O over the engel/bus koros split), so OIUEEI can be installed from the browser ("Add to Home Screen"). The `purpose: maskable` slot points at a **separate** `public/oiueei-icon-512-maskable.png`: the same art scaled to 80% inside the maskable safe zone with the two brand colours bled out to the edges (generated by clamping the border pixels), so an Android launcher masking to a circle/squircle keeps the whole logo instead of clipping the koros waves. The plain `-512.png` stays full-bleed for the `any` purpose (and the 192 remains the crisp favicon/apple-touch source). `index.html` links the manifest, sets `theme-color`, and uses the 192px icon as favicon + `apple-touch-icon` (this also replaced the previously-broken `/vite.svg` favicon reference — the file never existed in `public/`). All colours are HDS tokens sampled from the icon itself: background `#ffe977` (engel), theme `#0000bf` (bus), the O `#fd4f00` (metro). In production Vite's `base: '/static/'` rewrites the `index.html` URLs and the manifest's icon `src`s are relative, so everything resolves under `/static/` via WhiteNoise. **No service worker** — installability only, no offline caching; kept deliberately minimal (DESIGN §7).

---

## Pages

### LoginPage (`src/pages/LoginPage.jsx`)

- **API:** `POST /api/v1/auth/request-link/` with `{ email }` and CSRF token
- Uses the standard `form-hero` + `Koros` layout with theeeme colors from localStorage (if available from a previous session).
- **Hero title is the OIUEEI logo (S9)**: the only hero `<h1>` in the app whose text is the literal string "OIUEEI" — it renders `.form-hero-title-logo` (an 80px masked `oiueei-logo.svg`, coloured via `--hero-text-color`) instead, with `aria-label={t('login.title')}` on the `<h1>` for the accessible name. The hero also carries `form-hero--no-watermark` to suppress the standard 40px logo watermark (see Page Layout Pattern) — no double logo.
- Leads with a one-sentence pitch (`login.pitch` i18n key), then a brief description of OIUEEI (`login.description` i18n key).
- Shows a licence paragraph with a link to the GitHub repository (`login.licence` i18n key — OIUEEI is open source under the EUPL-1.2 — rendered via `Trans` for the inline link).
- Shows a one-line manifesto under the licence paragraph (`login.manifesto`): "No ads, no trackers. Your data is not the product." A quiet muted link to `/legal` (`login.legalLink`) sits under it. Below the form, a "trouble signing in?" line (`login.loginHelp`) links to `/contact` — the locked-out user's lifeline.
- Sends a magic link to the provided email address.
- After submission, replaces the form with a `Notification` component:
  - `success` — Unified message displayed (backend returns 200 regardless of email existence for anti-enumeration)
  - `error` — Server or network error
- CSRF token is read from the `csrftoken` cookie via `getCsrfToken()`.

### VerifyPage (`src/pages/VerifyPage.jsx`)

- **API:** `GET /api/v1/auth/verify/{code}/` (resolve) and `POST` of the same URL (commit a booking decision).
- Fetches (GET) on mount using the `:code` route parameter.
- **Booking accept/reject — one-click auto-commit:** when the GET returns `requires_confirmation` (a `BOOKING_ACCEPT`/`BOOKING_REJECT` preview, no mutation), the page **immediately fires the committing `POST`** from within the load effect, showing the "Verifying…" screen until it resolves to the confirmed/rejected success screen. The owner's single click (opening the email link) is enough — no second on-page button. Safety is preserved because the commit only runs from **real JS execution**: an email link-scanner or prefetch does a bare GET, runs no JS, and so still can't decide a hold (the backend also refuses to commit on GET). A `committedRef` guard stops React 19 StrictMode's dev-only double-invoked effect from POSTing twice.
- **ACCOUNT_DELETE is the exception to the auto-commit**: when the GET preview's `action` is `ACCOUNT_DELETE`, the page renders a dedicated confirmation screen (account email, owned collection/thing counts, the what-stays line) and the committing POST only fires from the explicit **"Delete my account forever"** danger button — never from the load effect. On success it clears `userCode`/`seenWelcome`/`theeemeColors`/`koro` from localStorage and shows the goodbye screen (`verify.accountDeleted*`); a Cancel button exits to home/login.
- On `COLLECTION_REJECT` action: shows success `Notification` confirming the invitation was declined and the owner was notified. Shows "Go to login" button. No login/redirect.
- On success: stores `userCode` in `localStorage`. Auth tokens are set as HttpOnly cookies by the backend. **The destination comes from the backend's `landing` field** (see `core/views/CLAUDE.md` → VerifyLinkView): `collection` ⇒ `/collections/{data.collection}` (with `{ state: { fromInvite: true } }` when `data.invited_collection` is also present — i.e. the landing came from an invitation, which is what shows the collection's welcome box), `welcome` ⇒ `deployment/aboutPath` (upstream null, so it falls through to `/` — nothing here produces that landing anyway), anything else ⇒ `/`. It used to be decided here from `seenWelcome`, but `LogoutPage` clears that key, so every re-login looked like a first visit. `seenWelcome` now only suppresses `CollectionPage`'s first-time Welcome Linkbox.
- On failure: shows error `Notification` with helpful guidance and "Go to login" button (resolves dead-end for expired links). **A refusal carrying `retryable` is not one of those**: an approval blocked by the invitation quota or the member ceiling leaves the link working, so the page shows the server's own reason and `verify.refusalHelp` ("this link still works") instead of `verify.invalidOrExpired` + `expiredHelp`. Every other refusal here consumes its RSVP, which is why the expiry copy stays right for them.

### HomePage (`src/pages/HomePage.jsx`)

- **APIs:** `GET /api/v1/auth/me/`, `GET /api/v1/collections/`, `GET /api/v1/invited-collections/`, `GET /api/v1/my-invitations/` (authenticated via HttpOnly cookies)
- Redirects to `/login` if no `userCode` in `localStorage`.
- Stores `userCode`, `theeemeColors`, `koro`, and `seenWelcome` in `localStorage` on successful fetch. `seenWelcome` suppresses the first-time Welcome Linkbox on `CollectionPage`.
- Displays greeting and a button row: "Create collection" (`/collections/new`, primary), "My profile" (`/me`, view own public profile — `home.myProfile`), and "My requests" (`/my-bookings`). "Edit profile" and "Log out" live only on the `/me` profile page, not here.
- **Inbox notifications**: renders `<InboxNotifications />` bare (every notification the user has — see Shared Components). It passes `onNetworkError` (the inbox's failed fetch feeds the offline banner like the four dashboard fetches do) and `reloadKey`, bumped by `reloadDashboard()` so a Retry / a returning connection re-fetches the inbox along with everything else.
- **Pending invitations**: fetches `GET /api/v1/my-invitations/` on mount. Shows one dismissible HDS `Notification` (type `info`) per pending invite, above the collections. Each notification shows the owner name as label, collection headline in bold, and "Accept invitation" / "Decline invitation" links pointing to `/verify/{accept_code}` and `/verify/{reject_code}`. Dismissed notifications are removed from local state only (RSVP remains until acted on).
- **My collections section**: shows own ACTIVE collections as `CollectionLinkbox` rows (`collections-grid` — a vertical stack of image-less, full-width rows, one per line at every breakpoint; see Shared Components). Each row shows headline and `{N} things · {N} guests`. Empty state links to `/collections/new`, plus a second **"See how it works"** button that follows `deployment/aboutPath` and is **absent upstream** — it pointed at `/welcome` until that route left with the demo, which made it a 404 on the very first screen a new account sees (`deployment.test.jsx` now pins both halves).
- **Inactive collections section**: shown below My collections when at least one own INACTIVE collection exists.
- **Shared with me section**: shows invited ACTIVE collections as `CollectionLinkbox` rows. Empty state shows a no-shared message.
- **Feedback line**: `<FeedbackLink />` at the foot of the page content.

### CollectionPage (`src/pages/CollectionPage.jsx`)

- **API:** `GET /api/v1/collections/{code}/`
- Redirects to `/login` if no `userCode` in `localStorage`.
- Handles 403 (not authorised) and 404 (not found) with specific error messages.
- Displays collection headline, description, and status. **Hero photo (S8):** when `collection.thumbnail_url` is present, the hero gets the `form-hero--photo` class and renders `HeroPhoto` (see Shared Components / UserPage's "Profile photo" note for the full ≥768px layered / <768px stacked behaviour) as a sibling of the wrapping `.form-hero-split`. The hero content itself (back link, title + mode/visibility tags, description, owner line, owner action buttons, share menu, invite nudge) sits inside that same `.form-hero-split`, unchanged — the photo composition sits behind/below it. No thumbnail ⇒ plain hero exactly as before (no `.form-hero-split` styling applies without the `--photo` modifier).
- **Things** are rendered using the `ThingLinkbox` component (see below).
- **"Edit collection" button** visible only to collection owner, links to `/collections/{code}/edit`.
- **"Add thing" button** visible to collection owner (always) and to invited users in COMMUNITY mode, links to `/collections/{code}/add`.
- **"Manage guests" button** visible only to collection owner, links to `/collections/{code}/invites`.
- **Community tag**: when `collection.mode === 'COMMUNITY'`, an HDS `Tag` with "Community" label is shown next to the headline.
- **Welcome Linkbox**: shown only when the user arrives from a COLLECTION_INVITE flow (`location.state.fromInvite`), `seenWelcome` is not set in `localStorage` (first-time users only), **and this deployment has an `aboutPath`** — upstream there is no such page, so the box never renders. Links to that path. Disappears after first click. The "Home" back link is hidden while the Welcome Linkbox is visible. Uses `linkbox-full-width` CSS class for 100% width.
- **Owner attribution**: guests see "Owner. {name}" below the description in the hero, linking to `/{owner_code}` (the owner's public profile). Uses `owner_name` from `CollectionSerializer`.
- **INACTIVE notice**: when the collection status is `INACTIVE` and the viewer is the owner, a `Notification` informs them "This collection is inactive. It is not visible to guests." Guests cannot access inactive collections (backend returns 403).
- **Inbox notifications (any member)**: `<InboxNotifications collection={code} />` at the top of the page content, above the banners, shown to the owner **and** any invited member (`isOwner || collection.is_member`). A hold request or a FAQ question is answered on the thing, so it must reach whoever owns *that* thing where it lives — not only on Home (O1). Scoped to the collection via the endpoint's `?collection=` filter, which the backend also always scopes to the requesting user, so a member only ever sees their own notifications (e.g. bookings on a COMMUNITY contribution they own) — never a co-member's or the owner's. Gating on membership rather than `isOwner` alone matters in COMMUNITY mode, where a thing's owner and the collection's owner can differ; it was owner-only until that gap surfaced (2026-09). An anonymous visitor on a PUBLIC collection renders nothing (`isOwner` and `is_member` are both false, and the endpoint is authenticated besides).
- **Pause banner**: when `collection.is_paused` is true, a fixed non-dismissible HDS `Notification` (type `alert`) is shown at the top of the page content area, with label `pause.bannerLabel` and body `collection.pause_message`. Shown to both owner and guests. `isPaused={collection.is_paused}` is passed to every `ThingLinkbox` so Hold buttons are disabled while paused.
- **Share menu**: directly under the owner action buttons in the hero, shown only to the owner. Renders `<ShareCollectionMenu>` (HDS `Select` with `IconEnvelope` / `IconShare` / `IconWhatsapp` icons, plus a QR action). It receives `isPublic={collection.visibility === 'PUBLIC'}`. For a **PRIVATE** collection it calls `POST /api/v1/collections/{code}/share-link/` on first interaction to lazily generate the public token and shares the `/share/{token}` join URL (recipient must enter their email to join). For a **PUBLIC** collection it **skips the token entirely** and shares the collection page directly (`${window.location.origin}/collections/{code}`) — anyone can read it without an account, so no email gate; a visitor who wants to *act* is asked to log in only then (login-to-act). Either way the resolved URL is cached in a `useRef` and dispatched to the chosen action: `mailto:`, `navigator.clipboard.writeText`, `https://wa.me/?text=`, or the QR dialog. Email subject/body and WhatsApp text are pre-filled with the collection headline and the URL, translated to the owner's language.
- **Digest switch (members only)**: under the owner attribution, shown when `collection.is_member` **and** `digest_frequency !== 'NONE'` — nothing to silence when the group sends no summary (DESIGN §3). One line of state plus a text `<button>` (`.digest-pref` / `.digest-pref-button`) that POSTs `{muted}` to `/api/v1/collections/{code}/digest/` and only moves the label once the server agrees, so a failure can't leave it lying. It is the per-group half of the email preferences: `User.notify_news` is the master switch on the profile, this narrows it to one collection — together they're what allow news to default ON without a pre-ticked opt-in (DESIGN §6).
- **Recommend a guest (members only)**: `RecommendGuest` in the hero, shown when `is_member` **and** `collection.allow_member_proposals`. A quiet one-line link that expands into email + optional note, posting to `/collections/{code}/invite/propose/`. The copy leads with "{owner} decides — nothing is sent to them until they say yes", because a member who walked away thinking they had invited somebody would have been misled by us. Called **recommend**, not invite or propose: the verb carries that you are putting your name behind the person, which the invitation itself will say if the owner agrees.
- **Broadcast section**: shown to the owner when the collection has invitees. A "Send a message to guests" button opens an inline form with just a message (TextArea, max 256) field — the subject is auto-generated server-side as `Hey! {collection}`. Its **helper line discloses the Reply-To** (`broadcast.replyToNotice`): the email carries the owner's own address so a reply is one tap, which makes this the one screen where a member learns an address the API otherwise never serves them. Said before the send, not after (DESIGN §6) — and said rather than switched off, because a broadcast with no reply path is a megaphone. Submits to `POST /api/v1/collections/{code}/broadcast/`. Shows success/error Notification inline. Closable via "Close" button.
- **Things section**: shows all non-inactive things for both owners and guests (responsive 3-column grid), **capped at `CARDS_PER_PAGE` (24) rendered cards** with a "Show N more things" button below (design round). The collection serialises *every* thing it holds and `COLLECTION_THINGS_BLOCK` is off by default, so a 200-item lending library used to mount 200 `ThingLinkbox`es — each with its own theeeme, localisation and booking view-model — on first paint (DESIGN §7; the photos were already `loading="lazy"`, so what this cuts is mount cost, not downloads). It is a **render** cap, not server pagination, because the tag chips count across the whole collection and a paginated payload would make those counts lie. Picking a tag resets the count.
- **"Leave the group" is no longer here.** It used to sit in the hero, third in a stack of unlabelled text links under the description (recommend → digest → leave) and the only destructive one of the three. It moved to the own profile's "My groups" list (`UserPage`) in the 2026-08 design round: leaving is something you do to your own membership, so it belongs with the rest of your account, next to the other memberships you might weigh it against. The route (`/collections/:code/leave`) and `LeaveCollectionPage` are unchanged.
- **Inactive things section**: below the Things section, when the payload carries at least one `INACTIVE` thing. Gated on the payload rather than `isOwner` (2026-09): the backend now sends an INACTIVE thing to the collection owner (every one) **and** to that thing's own owner (just theirs), so a COMMUNITY member's own contribution — a completed gift, or a listing they hid themselves — stays reachable here instead of only via its standalone `/things/{code}` URL. Lists all `INACTIVE` things the response carries using the same `ThingLinkbox` component, whose per-card owner-button-matrix already keyed off the thing's own `isOwner`.

### ThingLinkbox (`src/components/ThingLinkbox.jsx`)

Reusable component for rendering a thing as an HDS `Card`. Used by `CollectionPage` and `HomePage`.

- **Card**: the component uses HDS `Card` (a `<div>`-based container) instead of `Linkbox`, since it contains interactive elements (buttons, links). The thumbnail and headline are wrapped in `<Link>` components for navigation to `ThingPage` (`/collections/{code}/things/{thingCode}` or `/things/{thingCode}`). No `stopPropagation` hacks needed.
- **Community attribution** (before headline, COMMUNITY collections only): when `collectionMode === 'COMMUNITY'`, renders a `thing-card-meta` paragraph showing `owner_name` — linked to the member's profile (`/{thing.owner}`, `.thing-card-owner-link`) — and the creation date formatted as dd/mm. A **signed-out** reader is told there is a contributing member but not which one: the API withholds that name (it belongs to a group, not to the open web — same rule as the journey below), so the paragraph renders `common.aMember` ("A member") as **plain text, not a link** — the profile behind it is `IsAuthenticated`, so for that reader the link was only ever a door onto a 403 (`toLocaleDateString(i18n.language, { day: '2-digit', month: '2-digit' })`). Uses the `collectionMode` prop passed from `CollectionPage`.
- **Tags row** (before headline): HDS `Tag` components (rendered by the shared `ThingTags` component) in a flex row showing:
  - **Type** tag (always): Gift, Sale, Rental, Lend.
  - **New** tag (everyone, design round S7): shown for `NEW_THING_WINDOW_DAYS` (7) days after `thing.created`, excluding INACTIVE things ("newly available", not "recently created but hidden") — summer-yellow/black `TAG_THEMES.fresh`. Stateless (no per-user tracking, DESIGN §9): a pure function of `created` + `status`, matches the weekly digest cadence. Always leads the row, right after the type tag, even when `showType` is false.
  - **Requested** tag (owner only, `status === 'TAKEN'`): amber background.
  - **Inactive** tag (owner only, `status === 'INACTIVE'`): grey background.
  - **Pending questions** tag (owner only, `pending_questions > 0`): amber background — uses the `pending_questions` serializer field (count of unanswered FAQs).
- Displays the photo (when a thing has more than one photo — cover `thumbnail_url` + `gallery_urls` — it renders `<ImageCarousel variant="card" to={thingPath}>` so you can browse in-card; a single photo, or none, falls back to the static thumbnail/placeholder with `srcSet` for @2x/@3x), headline, description, and info rows with HDS icons for type (`IconTicket`), price (`IconEuroSign`), deposit (`IconLock`, LEND/RENT only when set — S6 2026-08, distinct icon and copy from price so "10 €" next to "50 €" reads as a fee plus a returnable guarantee, not one 60 € cost), availability (`IconCalendar` — for date-based types LEND/RENT the live indicator: `availability.IMMEDIATE` when available today, else the `next_available` day/month date or `availability.noneSoon`; static enum hint otherwise), location (`IconLocation`), condition (`IconShield`), and transfer count (`IconHome`, shown when `thing.transfer_count > 0` — uses type-specific i18n keys: `transfers.lendCount`, `transfers.rentCount` based on `thing.type`). Uses a plain `<div>` container (not HDS Card) to avoid style conflicts with HDS Tag components.
- **Owner bookings display**: read from the thing's own **`bookings`** serializer field (owner-only), which `useThingBooking` seeds once per thing code. It only falls back to `GET /api/v1/things/{code}/calendar/` when that field is absent. It used to fetch unconditionally, once per card — 30 items meant 30 parallel requests for the owner (DESIGN §7). The seed is guarded by a ref rather than an effect dependency: the parent hands back a fresh `thing` object after every accept/reject, and re-seeding from it would overwrite the list `handleBookingAction` just updated, making the decision visibly undo itself. Shown for date-based types (LEND/RENT) and for any TAKEN thing (GIFT/SELL with a pending request). Shows future pending and confirmed bookings with requester name, request date, date ranges, and status. Bookings with no dates (GIFT/SELL) are always shown regardless of date. The active pending booking is tracked in local `activePendingCode` state (initialised from `thing.pending_booking`, then synced to the first PENDING from the calendar on load) and marked bold with `*` when multiple pending exist.
- **Heading level is the caller's** (`headingLevel`, default `3`): the card's headline is a heading in the *page's* outline, not the card's, so only the caller knows what is correct. `CollectionPage` puts its grids under an `<h2>` section heading ("Things", "Inactive things"), so 3 is right there. `SharedThingsPage` is a single-section page whose grid sits directly under the page `<h1>` — left at 3 it skipped a level, and axe's `heading-order` flagged it once that page finally got an axe pass (2026-08). It passes `headingLevel={2}`. `CollectionPage` and `SharedThingsPage` are the only two components that render this one.
- **Themed buttons**: all buttons use theeeme colors (`btnStyle` for primary, `btnSecondaryStyle` for secondary). Secondary buttons always have a white background (`--background-color: white`); the theeeme `color_01` is used for the border, and `color_04` for the text.
- **Owner button matrix** (based on `thing.status`):
  - `ACTIVE` (no pending hold): "Edit" (**primary**), "Delete" (secondary). "Delete" is suppressed when pending bookings exist. There is no dedicated "Hide" button — hiding a thing is done by setting it `INACTIVE` from `EditThingPage`.
  - `ACTIVE` (date-based with pending hold): "Confirm hold" (primary) + "Cancel hold" (secondary) targeting `activePendingCode`, then "Edit" (secondary).
  - `TAKEN`: "Confirm hold" (primary), "Cancel hold" (secondary), "Edit" (secondary). After each accept/cancel, `activePendingCode` advances to the next pending.
  - `INACTIVE`: "Reactivate" (primary, calls `POST /api/v1/things/{code}/activate/`), "Edit" (secondary), "Delete" (secondary, navigates to `DeleteThingPage` with `{ state: { backPath, backLabel } }`).
- **Reservation button** logic (non-owners). The label is computed once (`buttonLabel`) so a disabled button always states its reason (P1-2):
  - `ACTIVE`: enabled button showing the per-type action verb (`thingCard.action.{type}`, default `thingCard.hold`).
  - `TAKEN`: disabled. Label is "Waiting for confirmation" to the viewer holding the pending booking (`thing.my_pending_booking` or local `requested`), and "Not available" (`thingCard.notAvailable`) to everyone else.
  - **Paused**: when `isPaused`, disabled and labelled "Paused" (`thingCard.paused`).
  - `INACTIVE`: not shown (guests cannot see INACTIVE things).
  - `isPaused` prop: passed from `CollectionPage` via `collection.is_paused`. Disables all Hold buttons for non-owners.
- **Reservation request** adapts to thing type:
  - `GIFT_THING`, `SELL_THING` — button submits directly via `POST /api/v1/things/{code}/request/`, no extra fields.
  - `LEND_THING`, `RENT_THING` — button navigates to `RequestThingPage` for date selection.
- **Back navigation**: passes `{ state: { backPath, backLabel } }` to RequestThingPage and ThingPage based on context (collection headline or home).

### ThingPage (`src/pages/ThingPage.jsx`)

Detail page for a thing with full information and FAQs section.

- **APIs:** `GET /api/v1/things/{thingCode}/` (detail), `GET /api/v1/things/{thingCode}/faq/` (FAQs), `POST /api/v1/things/{thingCode}/faq/` (ask question), `POST /api/v1/faq/{faqCode}/answer/` (answer), `POST /api/v1/faq/{faqCode}/hide/` and `/show/` (toggle visibility), `GET /api/v1/things/{thingCode}/transfers/` (transfer history), `POST /api/v1/things/{thingCode}/report/` (report the listing)
- Accessible from `/collections/:code/things/:thingCode` (collection context) or `/things/:thingCode` (standalone). **Public route** — an anonymous visitor can read a thing in a PUBLIC, ACTIVE collection (gated server-side by `can_view`); no redirect to `/login`.
- **Anonymous login-to-act**: for a signed-out visitor the reserve / answer buttons are shown (via `useThingActions`' `loginToAct` option) but each click **navigates to `/collections/:code/join`** (`JoinPage`) instead of acting — the same pattern as `ThingLinkbox` on `CollectionPage`. (The old inline `JoinToAct` box was removed.) Member-only sections (FAQ ask form, report footer) stay hidden until they log in.
- **Tags row** (before headline): same HDS `Tag` components as ThingLinkbox (type, Taken, Inactive, Pending questions).
- Displays photos, headline, description, creation date, fee, deposit (LEND/RENT only), availability, location, and condition — same `ThingInfoRows` component as `ThingLinkbox`, see its icon/copy note above. Photos render via `ImageCarousel` when the thing has more than one (cover `thumbnail_url` + `gallery_urls`); a single photo shows as a plain image.
- **Live availability** (date-based types LEND/RENT): read from the `available_today` / `next_available` serializer fields (computed from the booking calendar). When available today it shows the **same label as SELL things**, `t('availability.IMMEDIATE')` ("Immediate"/"Inmediata") — no green styling; otherwise the `next_available` date as day/month (e.g. "14/6") via `availability.nextAvailable`, or `availability.noneSoon` ("No"). Replaces the static `availability` enum row for date-based types only; non-date types keep the static enum hint. Also surfaced on `RequestThingPage` (above the date pickers, prefixed with the availability label).
- **Back link**: shows collection headline or "Home" depending on navigation context (via `location.state.backLabel`).
- **Owner bookings display**: fetches `GET /api/v1/things/{thingCode}/calendar/` for date-based types (LEND/RENT) and for any TAKEN thing (GIFT/SELL). Same logic as ThingLinkbox: filters past bookings, syncs `activePendingCode` to the first PENDING from the calendar, shows bookings list with requester name, request date, date ranges, and status. Active pending booking is bold; starred when multiple pending exist.
- **Owner actions:** Full parity with ThingLinkbox button matrix:
  - `ACTIVE` (no pending): "Edit" (**primary**) + "Delete" (secondary, suppressed when pending bookings exist). No "Hide" button — hiding is setting the thing `INACTIVE` via `EditThingPage`.
  - `ACTIVE` (date-based with pending): "Confirm hold" + "Cancel hold" + "Edit" (secondary).
  - `TAKEN`: "Confirm hold" (primary) → "Cancel hold" (secondary) → "Edit" (secondary). `activePendingCode` advances to next pending after each action.
  - `INACTIVE`: "Reactivate" (primary) + "Edit" (secondary) + "Delete" (secondary).
  - Delete navigates to `DeleteThingPage` with `{ state: { backPath, backLabel } }`.
- **Reservation:** Non-owners see the "Hold" button. GIFT/SELL submit directly via `POST .../request/`; date-based (LEND/RENT) types navigate to `RequestThingPage` with `{ state: { backPath, backLabel } }`.
- **FAQs section:**
  - Lists all FAQs with question, `questioner_name`, and answer. Hidden FAQs shown with reduced opacity (owner only).
  - **Owner:** inline `TextArea` to answer unanswered questions, "Hide"/"Show" toggle button per FAQ.
  - **Non-owner:** `Fieldset`-wrapped form to ask a new question.
- **Journey section** (below FAQs): fetches `GET /api/v1/things/{thingCode}/transfers/` on mount. Shown only when `total_transfers > 0`. Displays the journey with journey count (unique homes), current holder name, and a timeline of transfers (from → to, lent date, returned date). An empty `from/to_user_name` means one of two things, and the viewer's own session is what tells them apart — so `holderLabel()` picks the copy: for a **signed-in** reader it is a deleted account (right to erasure) and the timeline renders `common.formerMember` ("Former member"); for a **signed-out** one the API withheld every name (a thing in a PUBLIC collection is readable with no account, and a group's membership is not for the open web), so it renders `common.aMember` ("A member"). Reusing "Former member" there would tell a stranger that everyone who has held the thing has left — a claim about real people they cannot check. Pinned by `test/journeyDueBack.test.jsx`.
- **Report footer** (#12): a quiet supplementary `Button` with `IconAlertCircleFill` (`.thing-report-footer`), shown only to logged-in non-owners. Clicking **expands an inline confirm right below the button** (`.thing-report-confirm`, `aria-expanded` on the button — no modal): "Report this listing?" + a note that the owner is told *someone* reported it, never who, and Report/Cancel actions. Confirming `POST`s `/api/v1/things/{thingCode}/report/` and shows a thank-you Toast (`thingPage.reportThanks`). The backend records an anonymous `Report` (moderation log) and sends the owner an anonymous `THING_REPORTED` notification + email. Reporting is authenticated-only and idempotent per member.

### RequestThingPage (`src/pages/RequestThingPage.jsx`)

- **APIs:** `GET /api/v1/things/{thingCode}/` (detail), `GET /api/v1/things/{thingCode}/calendar/` (blocked periods for date-based types), `POST /api/v1/things/{thingCode}/request/` (submit request)
- Accessible from `/collections/:code/things/:thingCode/request` (collection context) or `/things/:thingCode/request` (standalone).
- Redirects to `/login` if no `userCode` in `localStorage`.
- **Back link**: uses `location.state.backPath` and `location.state.backLabel` passed from ThingLinkbox or ThingPage.
- **Page title**: `Hold: {thing.headline}` with fee display when present.
- **Form fields** adapt to thing type:
  - `LEND_THING`, `RENT_THING` — `DateInput` for start and end dates with blocked-date validation. **Rental rules (#7):** when the thing's collection defines `rental_durations` (from `ThingSerializer`), the free start/end pickers are replaced by a **duration `Select`** (the collection's fixed lengths) + a single **pickup `DateInput`**; the return date is derived (`pickup + length`, shown as "Return by …" — a one-week rental picked up on a Wednesday returns the NEXT Wednesday, so a single allowed weekday stays satisfiable). The pickup picker (`isPickupDisabled`, via `utils/rental.js`) disables days whose weekday — or the computed return day's weekday — isn't in `rental_weekdays`, and any day whose range overlaps a booking. The request POSTs `collection_code` so the backend applies the right collection's rules.
- **Date validation**: `minDate` today, `maxDate` today + 90 days. Blocked dates fetched from calendar API. The DateInputs display **DD/MM/YYYY** (`DISPLAY_DATE_FORMAT` from `utils/rental.js`); field state holds the display string and converts to ISO at the consumption boundaries (`displayToIso` for the POST body and the derived return date, which renders back via `isoToDisplay`). When the collection offers a **single** fixed rental length, it is preselected so the pickup picker is usable straight away.
- **Buttons**: Cancel (navigates back) + Hold (submits request).
- On success: shows an inline HDS `Notification` ("You're all set! We've let the owner know — they'll get back to you soon.") with a "Back to {backLabel}" button. Does not navigate automatically.
- On error: toast notification (top-right, auto-close).

### DeleteThingPage (`src/pages/DeleteThingPage.jsx`)

- **API:** `GET /api/v1/things/{thingCode}/` (to display headline), `DELETE /api/v1/things/{thingCode}/` (to confirm delete)
- Accessible from `/collections/:code/things/:thingCode/delete` or `/things/:thingCode/delete`.
- Redirects to `/login` if no `userCode` in `localStorage`.
- **Back link**: uses `location.state.backPath` and `location.state.backLabel` passed from ThingLinkbox, ThingPage, or EditThingPage.
- **Page title**: `Delete: {thing.headline}` in the hero.
- **Buttons**: Delete (primary, theeeme `btnStyle`) + Cancel (secondary, navigates back). No form fields.
- On success: navigates to `backPath`.
- On error: toast notification (top-right, auto-close).

### RemoveGuestPage (`src/pages/RemoveGuestPage.jsx`)

- **API:** `DELETE /api/v1/collections/{code}/invite/` with `{ user_code: guestCode }` body
- Accessible from `/collections/:code/invites/remove`.
- Redirects to `/login` if no `userCode` in `localStorage`. Redirects to invites page if `guestCode` state is missing.
- **State**: receives `{ guestCode, guestName, backLabel }` from `ManageInvitesPage`.
- **Page title**: `Remove: {guestName}` in the hero. Back link always goes to `/collections/:code/invites`.
- **Buttons**: Remove (primary, theeeme `btnStyle`) + Cancel (secondary, navigates back).
- On success: navigates to `/collections/:code/invites`.
- On error: toast notification (top-right, auto-close).

### LeaveCollectionPage (`src/pages/LeaveCollectionPage.jsx`)

- **API:** `POST /api/v1/collections/{code}/leave/` (no body).
- Accessible from `/collections/:code/leave` (protected route). Reached from the **"Leave the group"** button in the `CollectionPage` hero, shown to invited members (`collection.is_member && !isOwner`); the button passes `{ state: { headline } }`.
- Confirmation page (same pattern as `RemoveGuestPage`/`DeleteThingPage`): shows the collection headline, a warning, and **Leave the group** (primary) + **Cancel** (secondary, back to the collection).
- On success: navigates to Home (`/`) — for a PRIVATE collection the user has just lost access. On error: toast.
- The backend removes the user from `invites` and notifies the owner (`MEMBER_LEFT` in-app). The owner and non-members never see the button (`is_member` gate).

### MyBookingsPage (`src/pages/MyBookingsPage.jsx`)

- **API:** `GET /api/v1/my-bookings/`, `POST /api/v1/bookings/{code}/cancel/` to cancel
- Redirects to `/login` if no `userCode` in `localStorage`.
- Lists all booking requests made by the current user.
- Each booking card shows: thing type tag, status label (HDS `StatusLabel`, semantic — Pending/Confirmed/Rejected/Cancelled/Expired), thing headline (linked to thing page), owner name, dates, and creation date.
- PENDING bookings show a "Cancel request" button. Non-pending bookings are grouped under "Past requests".
- Accessible from HomePage via "My requests" button.

### NotFoundPage (`src/pages/NotFoundPage.jsx`)

- Catch-all 404 page for unknown routes.
- Uses the standard `form-hero` + `Koros` layout with theeeme colors from localStorage (or defaults).
- Shows a "Page not found" title and message with a button to go home or login.

### SharePage (`src/pages/SharePage.jsx`)

- **API:** `POST /api/v1/auth/join/` with `{ email, share_token }`.
- Public route at `/share/:token`. The owner has previously generated this token via the `ShareCollectionMenu` in CollectionPage; anyone with the link can land here and join the collection.
- Renders the shared `MagicLinkJoinPage` component (see Shared Components) with its own copy, and sends `share_token` in the POST body. A deployment that adds an open door of its own renders the same component with its own namespace.
- Invalid / revoked / inactive-collection tokens return 200 with the same magic-link response (anti-enumeration). **Nothing is created** for an invalid token — no account, no magic link — and the response is byte-identical to the valid case (see `JoinView` in `core/views/CLAUDE.md`).
- Uses the standard `form-hero` + `Koros` layout with theeeme colours from localStorage (or defaults when the recipient has no prior session).

### LogoutPage (`src/pages/LogoutPage.jsx`)

- Calls `POST /api/v1/auth/logout/` **via `apiFetch`** to clear auth cookies on the backend. It used a raw `fetch` with no `X-CSRFToken` header, so the POST was rejected by `CookieJWTAuthentication.enforce_csrf` (403) before `LogoutView` ran: the cookies survived, the refresh token was never blacklisted, and the session resurrected on the next page load — while the `.finally()` navigated to `/login` and made it *look* logged out. `LogoutView` now authenticates nothing either, so the request can't fail (see `core/views/CLAUDE.md`).
- Clears `userCode` and `seenWelcome` from `localStorage`.
- Navigates to `/login` immediately.

### AddThingPage (`src/pages/AddThingPage.jsx`)

- **API:** `POST /api/v1/things/` with `collection_code` in body
- Redirects to `/login` if no `userCode` in `localStorage`.
- Simple form with h1 title + `form-grid` layout:
  - `Select` for thing type. The select is filtered down to `collection.allowed_thing_types` when that field is non-empty (PROPRIETARY collections set this on Create/Edit). When the allowlist contains a single type, it is pre-selected so downstream fields show right away. **Type explainer (design round O2):** directly under the type `Select` (when `showTypeSelector`), an icon-only `InfoPopover` (`.info-popover-row info-popover-row--end` so the (i) sits flush right; accessible name `typeInfo.title` = "What each type means") whose panel lists one line per option — `<b>{label}</b> — {typeInfo.<VALUE>}` — built from the same already-filtered `typeOptions` the Select uses, so it never explains a type the collection can't hold. It tells a first-timer what separates the four types — a gift is kept, a sale has a price, a rental is paid and by dates, a loan comes back. Immediately after the type selector: `ToggleButton` for "Sin límite / Endless" (shown only for GIFT/SELL types). `TextInput` for headline (required, max 64), `TextArea` for description. `NumberInput` for fee (required for SELL/RENT types — `FEE_TYPES` — hidden for others). Right after it, a **deposit** `NumberInput` for LEND/RENT types only (`DATE_TYPES`, S6 2026-08) — optional, no default, its own icon and label on the ficha (`IconLock` vs `IconEuroSign`) so a RENT thing's price and deposit never read as one number; edits that switch the type away from LEND/RENT send `deposit: null` explicitly, since the server judges the row that lands, not the payload (`core/serializers/CLAUDE.md`). For GIFT/SELL/LEND types (`DETAIL_TYPES`): `Select` for availability, `TextInput` for location (max 32), `Select` for condition. `ImageUpload` for thumbnail (last, before button, folder `oiueei/things`).
  - "Create" button below the form. Validates on submit.
- On success: navigates to `/collections/{code}`.
- On error: toast notification (top-right, auto-close).

### EditThingPage (`src/pages/EditThingPage.jsx`)

- **API:** `GET /api/v1/things/{thingCode}/` to load, `PATCH /api/v1/things/{thingCode}/` to save, `DELETE /api/v1/things/{thingCode}/` to delete
- Accessible from `/collections/:code/things/:thingCode/edit` or `/things/:thingCode/edit`.
- Same fields as AddThingPage (type, then `ToggleButton` for Endless immediately after type for GIFT/SELL, headline, description, fee, deposit for LEND/RENT, availability/location/condition for `DETAIL_TYPES`, `ImageUpload` for thumbnail last). Pre-populates all fields including existing `thumbnail_url` for preview.
- "Save" button (primary, full width) and "Delete" button (secondary, full width) below the form. Delete navigates to `DeleteThingPage` with `{ state: { backPath: returnPath, backLabel: returnLabel } }`.
- On success: navigates back to collection or home.

### EditProfilePage (`src/pages/EditProfilePage.jsx`)

- **API:** `GET /api/v1/auth/me/` to load, `GET /api/v1/theeemes/` to list themes, `PUT /api/v1/users/{userCode}/` to save
- **Back link**: dynamic via `location.state.backPath` / `location.state.backLabel` (defaults to `← Home` / `/`).
- Simple form with h1 title + `form-grid` layout:
  - `TextInput` for the **public name** (`editProfile.nameLabel` "Nombre público" + `nameHelper` stating it's how everyone will see them — chosen pseudonymity, one field), `TextArea` for headline (short "Bio", max 64), `TextArea` for `about` (long free-form Markdown profile content, max 2000, "Markdown supported" helper), `ImageUpload` for the profile `photo` (folder `oiueei/users`), `TheeemeSelector` for theeeme (visual colour swatch grid from API), `KoroSelector` for koro (visual Koros SVG preview grid). All five are saved with the profile via the single PUT.
  - **Language `Select`** — switches the UI immediately (`i18n.changeLanguage`, as it always did) **and** saves `User.language` with the profile, so OIUEEI's emails follow the interface. It is the strongest level of the email language hierarchy: it beats the collection's language and the deployment default (see `core/services/CLAUDE.md`).
  - **The profile-load effect is mount-once, deliberately** (S7): its dependency array is `[userCode, navigate]`, not `[userCode, navigate, t, i18n]` — `t`/`i18n` get a new identity on every `i18n.changeLanguage()` call (fired by this same Select), so including them re-ran the effect on every language change, re-fetched `/auth/me/`, and clobbered every unsaved field — including the language pick itself — with the server's stale copy (the user couldn't leave their saved language). An `eslint-disable-next-line react-hooks/exhaustive-deps` documents why.
  - **Email preferences section** (h2 heading + `notifications.intro` paragraph + `form-grid`): three HDS `ToggleButton` components (wrapped in `.toggle-left`) — "Sign-in links and invitations" (always checked, `disabled`, renders black pill, Cat. 1), "Activity between users" (`notify_activity`, Cat. 2), and "News and announcements" (`notify_news`, Cat. 3). Each has a sub-label helper text rendered as a `<span>` inside the label prop. Preferences are saved together with profile fields via a single Save button.
  - "Save" button below the preferences section.
  - **Download my data** — a quiet muted link above the delete-account one, to `/me/data` (S5, 2026-08). Portability before erasure, in that order.
  - **Delete account** — a quiet muted link (border-top separated, below Save) to `/me/delete`. An entrance, not a trigger: the deletion has its own page and still requires the emailed confirmation.
- Pre-populates all fields (including `notify_activity`/`notify_news`) from the current user profile.
- On success: navigates to `/`.

### DeleteAccountPage (`src/pages/DeleteAccountPage.jsx`)

- **API:** `POST /api/v1/auth/delete-account/` (rate limited 3/h server-side).
- Accessible from `/me/delete` (protected route), reached via the quiet link at the bottom of EditProfilePage.
- `PageLayout` page that states the erasure map before anything happens: **what is deleted** (account, collections, things + photos, pending requests — permanently) and **what stays** (questions on other people's things and transfer-history hops, anonymised as "Former member" — `deleteAccount.*` i18n namespace).
- One HDS `Button variant="danger"` ("Send me the confirmation email") requests the emailed 24h link and swaps into a success `Notification` ("Check your email"). Errors (429 / server / network) render inline and keep the button.
- **Nothing is deleted on this page.** The deletion commits on `VerifyPage` when the emailed link is opened and its explicit confirm button pressed (see VerifyPage's ACCOUNT_DELETE note).

### DataExportPage (`src/pages/DataExportPage.jsx`)

- **API:** `GET /api/v1/auth/export/` (rate limited 10/day server-side).
- Accessible from `/me/data` (protected route), reached from `EditProfilePage` (a quiet link above "delete account") and from the top of `DeleteAccountPage` (a notice pointing here first).
- `PageLayout` page mirroring `DeleteAccountPage`'s shape: **what you take** (11 items, one per top-level export key — profile, the groups you own, the groups you're in, your things, bookings, questions, proposals, transfers, notifications, reports, activity) and **what you don't** (the 8 points `EXPORT_TOOL.md` specifies — credentials, other people's data, other people's things beyond a name, reports about your things, photos-as-links, emails, server logs, anything already deleted).
- One HDS `Button` ("Download my data") calls the endpoint, then `downloadBlob` under the server-set filename (`filenameFromResponse`). 429 → `common.tooManyAttempts`; any other failure → `dataExport.error`; a thrown request → `common.connectionError`. No confirmation step: unlike erasure this is reversible by construction.
- **No confirmation dialog, unlike DeleteAccountPage** — downloading a copy takes nothing away from anyone, so the extra step that erasure needs (an emailed link, an explicit second click) would only be friction here.

### NotificationsPage (`src/pages/NotificationsPage.jsx`)

- **API:** `GET /api/v1/notifications/token/{token}/`, `PATCH /api/v1/notifications/token/{token}/`.
- Accessible from `/me/notifications/:token` — a signed (`TimestampSigner`, ~1y TTL) token is included in the footer of every Cat. 2 / Cat. 3 email for unauthenticated preference editing.
- **Without `:token`**: redirects immediately to `/me/edit` (preferences are now embedded in EditProfilePage).
- **Token mode**: no `userCode` required in localStorage, no BackLink. Invalid tokens render a `Notification type="error"` with a fallback message and no form.
- **Form:** three HDS `ToggleButton` components (wrapped in `.toggle-left`):
  1. "Sign-in links and invitations" — always checked, `disabled`, renders black pill (Cat. 1, cannot be toggled).
  2. "Activity between users (recommended)" — controls `notify_activity` (Cat. 2).
  3. "News and announcements (optional)" — controls `notify_news` (Cat. 3).
  Each toggle has a sub-label helper text rendered as a `<span>` inside the label prop.
- Save button persists via `PATCH /api/v1/notifications/token/{token}/`. On success shows an inline `Notification type="success"` ("Preferences saved.").
- Uses the standard `form-hero` + `Koros` layout with theeeme colours from localStorage when available.

### ManageInvitesPage (`src/pages/ManageInvitesPage.jsx`)

- **API:** `GET /api/v1/collections/{code}/` to load invites, `POST /api/v1/collections/{code}/invite/` to invite, `DELETE /api/v1/collections/{code}/invite/` to remove
- Accessible from `/collections/:code/invites`.
- Simple page with h1 title:
  - Lists current invites by name/email. Pending invites show "Pending" label with "Resend" and "Remove" buttons. Owner sees "Remove" button per accepted invite.
  - Owner sees email input + "Invite" button below the guest list.
- Resend is an immediate API call. Remove navigates to `RemoveGuestPage` with `{ state: { guestCode, guestName, backLabel } }`.
- Resend cleans up old RSVPs and creates fresh ones.

### EditCollectionPage (`src/pages/EditCollectionPage.jsx`)

- **API:** `GET /api/v1/collections/{code}/` to load, `PATCH /api/v1/collections/{code}/` to save
- Accessible from `/collections/:code/edit`.
- **Two-tier form (progressive disclosure, design round O1)** with h1 title. The **visible** tier (a `form-grid`) carries the happy path and anything that can block submit: `TextInput` for headline (required), `TextArea` for description (+ their `LocalizedInfo` hint), `Select` for status (ACTIVE/INACTIVE), the mode `RadioButton` group, and the `CollectionForm` identity cluster (visibility toggle + the recommend-a-guest toggle + the allowed-thing-types multi-select — the mode-gated swap/share toggles went with those types). Everything **optional-with-a-safe-default** folds into a single collapsed HDS `Accordion` ("More options", `createCollection.advancedTitle`, `language="en"`, closed on load, heading tinted with theeeme `color_04` via the `--header-color` theme token), in this order: tags editor (`TagInput` + `LocalizedInfo variant="tags"`), **rental rules** (`RentalRulesFields`), digest `Select` (None/Weekly/Monthly), collection-language `Select`, thumbnail `ImageUpload`, welcome-doc `PdfUpload`. Nothing inside the accordion is required or can block submit (`validate()` only checks headline + description length + "pick at least one type", all visible), so the form is completable without ever opening it.
  - **Identity cluster** (`CollectionForm`): the visibility `ToggleButton` (`.toggle-left` wrapper) plus a `Select multiSelect` for allowed thing types — default empty, so the user must explicitly pick at least one, validated live after the first submit attempt. The list is the same in both modes: mode decides WHO may add a thing, not which types. Save fails with 400 from the backend if narrowing would orphan existing things — the response detail names the offending types and is surfaced via Toast.
  - **Rental rules (#7):** `RentalRulesFields` (extracted from `CollectionForm` in O1) via `utils/rental.js`, rendered inside the accordion — a `Select multiSelect` for rental lengths plus a `[L M X J V S D]` **weekday chip row** (`.weekday-chips`, accessible toggle `<button>`s with `aria-pressed` + full-name `aria-label`, narrow letters via `Intl`) for pickup/return days. They save `rental_durations` (days) + `rental_weekdays` (0=Mon…6=Sun). Below the weekday chips, a `TextArea` for `deposit_policy` (S6, D5, 2026-08) — how deposits work in this group, in the owner's own words; empty by default, localizable like every other owner text (`LocalizedInfo variant="policy"`), and deliberately not a per-thing toggle since the amount already lives on each thing.
  - "Save" button below the form (outside the accordion), then "Delete" button below that (navigates to `DeleteCollectionPage`).
- **Pause section** below the Delete button (separated by a border):
  - When NOT paused: `TextArea` for a custom message to guests + "Pause collection" button (disabled until message is non-empty). Submits `PATCH { pause_message: message }`.
  - When paused: shows the current message in a styled `<blockquote>` + "Resume collection" button. Submits `PATCH { pause_message: "" }`.
  - Both actions are independent PATCHes from the main Save; no page reload.
  - Shows success toast on pause/resume.
- **Stats download** below the Pause section (same border/spacer pattern, design round): a secondary "Download stats (CSV)" button (`GET /api/v1/collections/{code}/stats/` → blob → `{code}-stats.csv`), with an inline error `Notification` on failure. Moved here from the CollectionPage hero — an admin tool belongs with the collection's other owner-only settings, not in a hero button slot shown on every visit.
- **Collection data export** directly under the stats download (S5, 2026-08): a second secondary button, `GET /api/v1/collections/{code}/export/` → blob → the server-set filename (via `filenameFromResponse`, `src/utils/downloadBlob.js`), same 429/error handling shape. A copy line under it says out loud that this is the whole group, not the CSV summary above, and that it carries other members' emails — an owner should know what they're about to have on their laptop before they click. Owner-only server-side; a member reaching this page by URL gets the same 403 the endpoint always returns.
- Pre-populates all fields from the current collection data, including existing `thumbnail_url` for preview.
- On save: navigates to `/collections/{code}`.

### CreateCollectionPage (`src/pages/CreateCollectionPage.jsx`)

- **API:** `POST /api/v1/collections/`
- **Back link**: dynamic via `location.state.backPath` / `location.state.backLabel` (defaults to `← Home` / `/`).
- **Two-tier form (progressive disclosure, design round O1)** — identical structure to EditCollectionPage above, minus the status select (Create has none). **The digest select is now present in both** — it used to be Edit-only, which was survivable while `digest_frequency` defaulted to `NONE` and is not now that it defaults to `WEEKLY`: a new collection mails its members, so its owner has to see the field at the moment they create the group. Same options, order and `editCollection.*` keys as Edit, so the one field doesn't read differently on the two screens. The **visible** tier: headline, description (+ `LocalizedInfo`), the mode `RadioButton` group (per-option inline description, `createCollection.modeProprietaryDesc`/`modeCommunityDesc`), and the `CollectionForm` identity cluster. The collapsed **"More options" `Accordion`** holds: tags editor (`TagInput` + `LocalizedInfo variant="tags"`), `RentalRulesFields`, collection-language `Select`, thumbnail `ImageUpload`, welcome-doc `PdfUpload`.
  - **Identity cluster** (`CollectionForm`): the visibility `ToggleButton` (`.toggle-left` wrapper) plus a `Select multiSelect` for allowed thing types — default empty, so the user must explicitly pick at least one, validated live after the first submit attempt. The list is the same in both modes: mode decides WHO may add a thing, not which types. Save fails with 400 from the backend if narrowing would orphan existing things — the response detail names the offending types and is surfaced via Toast.
  - **Rental rules (#7):** `RentalRulesFields` via `utils/rental.js`, in the accordion — a `Select multiSelect` for rental lengths plus a `[L M X J V S D]` **weekday chip row** for pickup/return days. They save `rental_durations` (days) + `rental_weekdays` (0=Mon…6=Sun). Same `deposit_policy` `TextArea` as EditCollectionPage.
  - "Create" button below the form (outside the accordion).
- On success: navigates to `/collections/{code}`.

### UserPage (`src/pages/UserPage.jsx`)

- **API:** `GET /api/v1/users/{userCode}/`
- Also serves as `/me` route: when no `userCode` param, fetches `/api/v1/auth/me/` to resolve own code.
- Redirects to `/login` if no `userCode` in `localStorage`.
- Handles 403 (no permission) and 404 (user not found) with specific error messages.
- Uses the standard `form-hero` + `Koros` layout with theeeme colors (own profile uses `theeeme_colors` from API, other profiles fall back to localStorage).
- Hero: BackLink, spacer, headline as Heading M subtitle, name as h1 title, "Member since" date.
- **Profile photo:** when `user.photo_url` is present, rendered via the shared `HeroPhoto` component (see Shared Components). **≥768px** keeps the original **layered** composition, pixel-identical: the photo (`.hero-photo-wrap`) is a full-bleed background (z0); a `color_03` `Koros` wedge (`.hero-photo-diag`) sits above it (z1) — a large solid fill block plus the `Koros` wave rotated 135° as one unit, anchored at the hero centre (`translateY` sizes the wedge) — carving a diagonal so the text reads on the colour band while the photo shows through the wedge; the content (`.form-hero-split` → title/name/buttons) sits on top (z2). The decorative Koros keeps its natural 85px height (no override) so its fill meets the block with no gap; both are `aria-hidden` and filled with theeeme `color_03`. **<768px** switches to a stacked "image bottom" hero (HDS reference pattern): `.form-hero-split` flows normally above on the `color_03` band, `.hero-photo-diag` is hidden, `.hero-photo-top-koros` (a second `Koros`, `display:none` by default so it never shows ≥768px) appears biting the photo's top edge (`margin-bottom: -14px`, same overlap technique as the bottom `.form-hero-koros`), and `.hero-photo-wrap`/`.hero-photo` switch from `position: absolute` to a plain full-width `static` block (`height: 260px`, `object-fit: cover`). The photo gets an `alt` of the user's name. When absent, the plain hero is unchanged at every width.
- **About box:** when `user.about` is present, a "{{userPage.aboutHeading}}" section in the page container renders the Markdown via the shared `MarkdownText` component (no new dependency). Shown on both own and other profiles.
- **Own profile:** shows "Edit profile" and "Log out" buttons in the hero. Owned collections are not listed — those are on the HomePage (`/`).
- **"My groups" (own profile only, design round):** a `.membership-list` of the collections you are a *member* of (`GET /api/v1/invited-collections/`), one `.membership-row` each — the group's name on the left, a quiet **"Leave the group"** link on the right (`/collections/:code/leave`, passing the resolved headline in navigation state). This is where leaving moved to from the collection hero; see `CollectionPage` above for why. A failed fetch simply renders no section — it must never take the profile down with it.
- **Other profiles:** shows "Collections in common" section with shared collections (where both users are connected as owner/invite) as `CollectionLinkbox` rows (image-less, full-width — see HomePage's "My collections section" note and Shared Components).

---

## Shared Modules

### API Service (`src/services/api.js`)

- `apiFetch(url, options)` — Centralised fetch wrapper. Uses `credentials: 'include'` for cookie-based auth, sets `Content-Type: application/json` for requests with body. On 401: silently attempts token refresh via `POST /api/v1/auth/refresh/`. Only `userCode` is stored in localStorage (for ownership checks).

### File downloads (`src/utils/downloadBlob.js`)

`downloadBlob(blob, filename)` — hands an already-fetched `Blob` to the browser as a download. There is no declarative way to do it (a `<a download>` needs a URL that exists only after the response), so it is a dozen lines of imperative DOM, and both ways a copy of them drifts are invisible in the happy path: an object URL that is never revoked pins the blob in memory for the life of the tab, and an anchor left in the body is a stray focusable element between the page's real controls. **The caller keeps the request and its failure copy** — what a 429 should say differs per page, and this function never sees the response. Used by `EditCollectionPage` (the stats CSV, the collection export) and by anything else that offers a file.

`filenameFromResponse(res, fallback)` (S5, 2026-08) — reads the `Content-Disposition` filename off a response, or `fallback` if it's missing. Shared so the two data-export downloads (`DataExportPage`, `EditCollectionPage`'s collection export) read the server-set `oiueei-{code}-{date}.json` name identically rather than each guessing their own — the stats CSV still builds its own name client-side (`{code}-stats.csv`), since that endpoint never set the header.

### Owner content in one text per language (`src/utils/localized.js`)

The mirror of `core/utils.py::parse_localized` / `resolve_localized` — and it must **stay** a mirror: if the two sides disagreed on what counts as a map, a card would show raw braces for content whose email reads as words. `parseLocalized(value)` returns the `{lang: text}` map or `null` (strict: a JSON object, keys ⊆ `es`/`ca`/`en`, all values non-empty strings — everything else is prose and renders verbatim). `localizedText(value, lang)` resolves it (`lang` → `es` → the first language written, so nobody ever faces JSON), and **`useLocalized()`** binds it to the reader's language — the frontend twin of the email service's `L`:

```jsx
const L = useLocalized();
<h1>{L(thing.headline)}</h1>
```

Every site that renders owner content calls it: `ThingLinkbox`, `ThingPage`, `CollectionLinkbox`, `CollectionPage` (which resolves once and hands the words to its children — cards, share menu, back labels, **and its own tag-filter bar chips**, S6: the raw string stays the filter key — `includes`, `effectiveTag ===`, the React `key` — only the chip label resolves), `HomePage` (inbox payloads + pending invitations), `MyBookingsPage`, `OwnerBookingsList`, `RequestThingPage`, the delete/leave confirms, `ThingTags` and the tag pickers, plus every `document.title`. The **edit forms are the exception**: they show the *raw* value, because that is what the owner is editing — only their title and back label resolve. `localizedCounter(value, limit)` is the form counter: `18/64` for plain text, `es 18/64 · ca 17/64` for a map (each language gets the whole limit — the rule the server enforces), plus an `over` flag the forms turn into an inline error.

### Custom Hooks

- **`useThingBooking`** (`src/hooks/useThingBooking.js`) — The lower-level booking **engine**: owns the reservation state, the owner-calendar fetch (`AbortController`-guarded, re-runs by `thing.code`), and the three async handlers (`handleRequest`, `handleActivate`, `handleBookingAction`). The card-vs-page differences are options (`initialActivePending`, `initialRequested`, `fetchOnEndless`, `bookingKeepsStatus`, `activateSuccessMessage`). **`collectionCode`** is sent in the request POST body: a thing can live in several collections, and the one the requester was browsing is what decides where the owner's notification appears — `ThingLinkbox` passes its `collectionCode` (or `thing.collection_code`), `ThingPage` the same code it uses for login-to-act; the standalone `/things/:code` page has none and the backend falls back to its own approximation. `RequestThingPage` (dates) already posted it for the rental rules. Returns `{ submitting, requested, bookingAction, bookingActionVerb, activating, bookings, activePendingCode, handleRequest, handleActivate, handleBookingAction }`.
- **`useThingActions`** (`src/hooks/useThingActions.js`) — The **view-model** layer wrapping `useThingBooking`, shared by `ThingLinkbox` and `ThingPage` so the owner-button-matrix / reserve-button logic lives in one place. Derives the type flags (`isOwner`, `isCollectionOwner`, `isDateBased`, `needsPage`, `canDelete`, `hasPendingBookings`) and the reserve button's `showButton` / `buttonDisabled` / `loginButtonDisabled` / `buttonLabel` — plus everything `useThingBooking` returns. The genuine differences are options: `isPaused` (card on a paused collection; the page passes false), `canAct` (the page passes `isAuthenticated`), `loginToAct` (anonymous-on-public — buttons show but each click routes to `/collections/:code/join`), `collectionOwner`, `collectionCode` (forwarded to `useThingBooking`, above), and the `useThingBooking` seeds. `bookingKeepsStatus` (`needsPage || is_endless`) is derived here so callers don't repeat it. Signature: `useThingActions(thing, userCode, options)`.
- **`useCapabilities`** (`src/hooks/useCapabilities.js`) — What this deployment lets the signed-in account create: the `capabilities` block on `GET /auth/me/` (`{collection_modes, thing_types, request_url}` — see `core/services/CLAUDE.md`). One request per signed-in account, shared by every form that asks and keyed by `userCode` so it cannot outlive a logout. **Null until known and null on failure**, and every caller reads null as "no restriction" and offers the whole catalogue: this is a courtesy to the user, never the gate — the gate is the server, which refuses regardless of what the browser managed to fetch. **A failure is not cached** (a non-OK status counts as one): failing open is deliberate, remembering the failure was not, since one offline blip would otherwise keep every later form in that session offering what the deployment refuses, ending in a 403 nobody could have predicted. An answer *without* the field does cache — that is a real answer, meaning no restrictions. Contract pinned in `test/capabilities.test.jsx`. `isOfferable(capabilities, kind, value, current)` is the predicate the four forms filter their options with; `current` (the value being edited) is **always** offered even when the policy no longer allows it, mirroring the server, which only judges a *change* — a form that hid the current answer would display one thing and submit another.
- **`useJoin`** (`src/hooks/useJoin.js`) — The shared `/auth/join/` submit behind the email-capture doors: `MagicLinkJoinPage` (`/share/:token`, plus any a deployment adds) and `JoinToAct` (inside `JoinPage`). They stay separate components because they render very differently — boxed page vs unboxed hero body with inline errors — but the request was byte-identical in both and had already drifted. Owns `email` / `loading` / `status` / `message` plus the CSRF header, the `language` field (so a brand-new user's first magic link speaks the language of the page they typed on), the 429 branch, the `seenWelcome` reset, and a **ref-based** re-entry guard — a `loading`-state guard is useless against a second submit in the same tick, which runs the previous render's closure and still sees `false`. Options: `sentMessageKey` / `errorMessageKey` (the copy differs per door) and `extraBody` (`JoinToAct`'s `collection_code`, `SharePage`'s `share_token`). Returns `{ email, setEmail, loading, status, message, submit }`.

### Shared Components

- **`ButtonLink`** (`src/components/ButtonLink.jsx`) — A control that navigates and looks like a button: one `<a>`, one tab stop. Replaced 25 `<Link><Button>` pairs, which put one interactive element inside another. Built on HDS `Link` + `useButtonStyles`; see **A link that looks like a button** below for the three things about it that are load-bearing. Props: `to`, `state`, `fullWidth`, `style` (the theeeme tokens), and anything else, which reaches the `<a>`.
- **`StatusRegion`** (`src/components/StatusRegion.jsx`) — A `role="status"` live region for a message that appears in response to something the reader did. **It renders unconditionally and the condition stays inside it** (`<StatusRegion>{saved && <Notification …/>}</StatusRegion>`): a live region only announces changes made inside a region that already existed, so wrapping the message at the moment it appears looks identical, passes axe, and announces nothing. Polite, not assertive, and one region can therefore hold either outcome of a slot that swaps between success and error. Not for a message that *is* the page.
- **`BackLink`** (`src/components/BackLink.jsx`) — Reusable `← {label}` back navigation link. Props: `to`, `label`.
- **`Toast`** (`src/components/Toast.jsx`) — Reusable toast notification wrapping HDS `Notification`. Props: `toast` (`{ type, message }`), `onClose`. Renders at `position="top-right"` with auto-close.
- **`LoadingSpinner`** (`src/components/LoadingSpinner.jsx`) — Wrapper around HDS `LoadingSpinner` component.
- **`MarkdownText`** (`src/components/MarkdownText.jsx`) — Renders the small Markdown subset owners can write (bold, italic, `-`/`1.` lists, `[text](url)`, GFM pipe tables, `#`–`###` headings capped so a bio can't outrank the page) as sanitised HTML via `dangerouslySetInnerHTML`. Used for thing and collection descriptions, user `about` bios and `LegalPage` (which passes `headingBase={2}` so the outline doesn't skip a level). **The invariant to know before touching it:** `markdownToHtml` escapes each line *once*, up front, and `renderInline` then works on already-escaped text — it must never escape again. Doing so turned a `&` in a link's query string into `&amp;amp;`, which the browser resolves back to a literal `&amp;`, quietly sending readers to a different URL. For the same reason each generated `<a>` is parked behind a NUL-delimited placeholder while the bold/italic passes run (they would otherwise splice an `<em>` into an href containing `*…*`), and `escapeHtml` strips NUL so typed text cannot forge one. `sanitizeUrl` (also exported, reused by `ThingPage`) allows only http/https and returns `#` otherwise.
- **`MagicLinkJoinPage`** (`src/components/MagicLinkJoinPage.jsx`) — Shared join landing page, rendered by `SharePage` (and by whatever door a deployment adds): a `PageLayout` hero + email form that POSTs to `/api/v1/auth/join/` (with `language: i18n.language`, so a brand-new user's very first magic link already speaks the language they were reading the page in — `JoinToAct` sends it too) and swaps into a sent/error `Notification` (with the "you can close this tab" line on success). Props: `ns` (i18n namespace for the form strings and the `{ns}-email` input id — `'share'` here; a deployment supplies its own through `deploymentI18n`), `docTitleKey` / `titleKey` / `descriptionKey` (full i18n keys — their names differ per page), `extraBody` (extra POST fields, e.g. SharePage's `share_token`). `JoinToAct` (JoinPage's variant of the same flow) deliberately stays separate — it renders unboxed inside another page's hero and reports errors inline.
- **`FeedbackLink`** (`src/components/FeedbackLink.jsx`) — Quiet one-line alpha-feedback prompt ("Something odd? An idea? Tell me →") linking to whatever form the deployment set via the `VITE_FEEDBACK_URL` build-time env var (e.g. a Heroku config var picked up by the `heroku-postbuild` build). **Renders nothing without it** — the same `null`-upstream pattern as `deployment/popInPath`/`aboutPath` (S2, 2026-08): sending a self-hoster's users' feedback to CA's own Tally form by default was service-layer policy leaking into the product, silently and without Tally appearing anywhere in that deployment's own legal text. `README.md`'s own "Try it" section links CA's form directly and is unaffected — that is CA inviting people to try *his* deployment, not code that ships to anyone else's. Rendered at the foot of HomePage (`.feedback-link`, muted `--color-black-60`).
- **`InboxNotifications`** (`src/components/InboxNotifications.jsx`) — The inbox: one dismissible HDS `Notification` per in-app notification, keyed by `type` (label + body via the `home.*` i18n keys it was born with; payload headlines resolve through `useLocalized`). Owns its own fetch and its dismiss (`DELETE /api/v1/inbox/{code}/`, optimistic). `notificationLink()` returns a `{to, label}` deep link to the object that originated it: `BROADCAST` to the collection (`home.viewCollection`), and **anything carrying a `thing_code` to that thing** (`home.viewThing`) — so a hold request lands the owner on the page where they answer it, and `THING_REPORTED` keeps its old `/things/{code}` target (it carries no collection). A response body that isn't a list degrades to "no notifications" rather than taking the page down with it. **`localizedPayload` also fills in every person-name key** (`owner_name`, `questioner_name`, …) with `common.aMember`: the backend sends the bare `name`, never `display_name`, because that fallback is the person's email address and the reader here is a co-member not entitled to it (L2, `core/services/CLAUDE.md`) — so somebody who never filled in a profile arrives as `''`, and every one of these strings interpolates the name mid-sentence. One funnel, so a builder cannot forget. Props: `collection` (optional code → `GET /api/v1/inbox/?collection=`, the owner-only per-collection view on `CollectionPage`; omitted on Home = everything), `reloadKey` (bump to re-fetch), `onNetworkError` (must be stable — it is a fetch-effect dependency).
- **`ApprovalNotice`** (`src/components/ApprovalNotice.jsx`) — The one line a narrowed deployment owes someone looking at a shorter list than the product has: "some options need approval here: Rental, Loan — Request access →", or, when `request_url` is null, "not available on this deployment" **with no link** (somewhere to ask means "not yet"; nowhere to ask means "not here", and pointing at a page that does not exist is worse than the shortened list it was meant to explain). Props: `kind` (`'collection_modes'`|`'thing_types'`) and `catalogue`, the already-labelled options the form *would* offer if nothing were withheld — it diffs that against `useCapabilities()` and names the difference in the same words the control used, never the raw `COMMUNITY`/`LEND_THING` value. **Renders nothing upstream**, where the policy withholds nothing, and nothing while the answer is unknown. Rendered under the mode radio group in `CreateCollectionPage`/`EditCollectionPage` and under the type selector in `ThingForm` (via its optional `typeCatalogue` prop — the types the *collection* would take, so the notice never offers to get approval for a verb the owner's own allowlist rules out anyway). Deliberately not an HDS `Notification`: nothing has gone wrong, and an alert box would read as an error the reader caused.
- **`CollectionModeField`** (`src/components/CollectionModeField.jsx`) — The collection-mode radio group, shared by `CreateCollectionPage` and `EditCollectionPage`. An HDS `SelectionGroup` (the fieldset/legend that makes two radios one question) holding one `RadioButton` per mode with its own description wired through `aria-describedby`, plus `ApprovalNotice` for whatever this deployment withholds. Props: `idPrefix`, `label`, `options` (the modes to offer), `catalogue` (every mode the product has), `value`, `onChange` — called with the mode string. **Which options exist stays with the callers**: Create offers what the deployment allows, Edit also offers the mode the collection is already in, since the server judges only a *change*. Replaced a hand-rolled `<fieldset>` duplicated across the two pages; see the SelectionGroup quirks below for the two things that shape its children.
- **`ThingTags`** (`src/components/ThingTags.jsx`) — Shared tag row for thing type, status, pending questions, and the thing's **owner-defined tags** (`thing.tags`, rendered with `TAG_THEMES.custom`). Props: `thing`, `isOwner`. Uses `TAG_THEMES` from constants.
- **`ThingReportFooter`** (`src/components/ThingReportFooter.jsx`) — The quiet "report this listing" footer on `ThingPage` (logged-in non-owners). Owns its open/submitting state + the report POST; expands an inline confirm (`.thing-report-confirm`, `aria-expanded`, no modal) and reports feedback via `onToast`. Props: `thingCode`, `onToast`.
- **`ThingFaqSection`** (`src/components/ThingFaqSection.jsx`) — The FAQ block on `ThingPage`: question list (owner sees hidden ones + answer / hide-show controls), a "Load more" pager, and the ask-a-question form for logged-in non-owners. Self-contained — owns its FAQ list + form state and fetches its own FAQs on mount (by `thingCode`). Props: `thingCode`, `isOwner`, `isAuthenticated`, `btnStyle`, `btnSecondaryStyle`, `tc`, `onToast`.
- **`TagInput`** (`src/components/TagInput.jsx`) — Chip-style free-text editor for the collection owner to define the collection's tag vocabulary. `TextInput` + "Add" (and Enter) appends a removable HDS `Tag` (via `onDelete`); trims, dedupes case-insensitively, caps at 12 tags / 32 chars each (mirrors the backend `_normalize_tags`). A label may itself carry **one text per language** (O6), so the cap is 32 **per language**, the native `maxLength` is gone (it would have truncated a map mid-JSON) and an over-long label is refused inline; the **raw string stays the value** (the vocabulary stores it and a thing's tags are checked against it) — only the chip resolves, with the languages it carries in its `title`. Props: `tags`, `onChange`, `label`, `placeholder`, `helperText`, `max`. Used in CreateCollectionPage, EditCollectionPage. The thing forms (Add/EditThingPage) instead use an HDS `Select multiSelect` populated from the collection's `tags` / `collection_tags` to assign a subset to a thing.
- **`ImageUpload`** (`src/components/ImageUpload.jsx`) — Single-image upload using HDS `FileInput`. Gets a short-lived upload ticket from `POST /api/v1/upload/ticket/`, resizes and re-encodes the image client-side (≤1216px, WebP), `PUT`s it straight to object storage, and calls `onChange(key)`. Shows a preview with a Remove button when an image is present; the FileInput is hidden while a preview exists. Button label and accept hint are translated via i18n. Button colours follow the current theeeme. Props: `id`, `label`, `value` (storage key), `onChange`, `currentUrl`, `folder` (default `oiueei/users`), `helperText`. Used in AddThingPage, EditThingPage, and EditProfilePage (profile photo). The client-side resize-to-1216px helper lives in `src/utils/resizeImage.js` and is shared with `GalleryUpload`. **A size check runs after that resize** (`IMAGE_MAX_BYTES`, 10 MB, mirroring `core/views/upload.py`): the resize is what makes a 30 MB phone photo a few hundred kilobytes, so checking the *original* would refuse exactly the files this is for. What survives at full size is a format the browser could not decode, and it fails with `UploadTooLargeError` and its own message (`upload.imageTooLarge`) rather than the generic `upload.uploadError` after a pointless round trip. Courtesy only — the real cap is signed into the ticket, like `PdfUpload`'s. Keep the two numbers equal.
- **`PdfUpload`** (`src/components/PdfUpload.jsx`) — Single-PDF upload for a collection's **welcome & rules document**. Same ticketed direct-to-bucket path as `ImageUpload` (`src/utils/uploadPdf.js` → `POST /api/v1/upload/ticket/` with `kind: 'document'`, so the ticket only permits a PDF), but **no resize** — a document is not a photo. The **5 MB** check with its inline error (`upload.pdfTooLarge`) is now a *courtesy*, refusing an oversized file instantly instead of after a round trip: the real cap is signed into the ticket server-side (`DOCUMENT_MAX_BYTES`), where a client cannot skip it. It used to be the only cap there was, because `max_file_size` was not a signable Cloudinary parameter (signing it broke every document upload — S3). Keep the two numbers equal. `FileInput` with `accept=".pdf,application/pdf"` and the `upload.addFileGeneric` button label; once a file is present the input is replaced by a link to it (`upload.pdfView`) plus a Remove button. Props: `id`, `label`, `onChange` (called with the storage key, or `''` on remove), `currentUrl`, `folder` (default `oiueei/documents` — the server forces this folder for document-mode tickets regardless, S4), `helperText`. Rendered in CreateCollectionPage + EditCollectionPage under the thumbnail, saving `welcome_doc`. Every member who joins the collection for the first time is emailed the document as a link (see `core/models/CLAUDE.md` → `Collection.welcome_doc`).
- **`GalleryUpload`** (`src/components/GalleryUpload.jsx`) — Multi-image upload for a thing's extra photos (the `gallery` field). Same ticketed upload + client resize as `ImageUpload` (folder `oiueei/things`), max 8 images, and the same post-resize size check with the same specific message. Renders a thumbnail row with remove buttons. Items are `{publicId, url}` pairs so the parent can preview and submit `items.map(i => i.publicId)`. Props: `items`, `onChange`. Used in AddThingPage, EditThingPage.
- **`CollectionLinkbox`** (`src/components/CollectionLinkbox.jsx`) — A collection row (HDS `Linkbox`, deliberately **no thumbnail** — S8) used by HomePage's three collection grids and UserPage's "Collections in common". Rendered inside `.collections-grid` (`display:flex; flex-direction:column` — a vertical stack of full-width rows at every breakpoint, not a multi-column grid; the global `max-width:400px` Linkbox cap is neutralised the same way `linkbox-full-width` does elsewhere). Props: `collection` (`{code, headline, things?, invites?}`), `showInfo` (shows the "{N} things · {N} guests" line — the Home grids pass counts, the profile grid omits it).
- **`HeroPhoto`** (`src/components/HeroPhoto.jsx`) — The photo block for a `.form-hero.form-hero--photo` hero (see the UserPage "Profile photo" note above for the full ≥768px/<768px behaviour). Render as a sibling of `.form-hero-split`, inside `.form-hero.form-hero--photo`. Props: `photoUrl`, `alt`, `koroType` (the viewer's koro preference), `color03` (the hero's `color_03` theeeme token name, for the wedge/wave fill). Generic — no page-specific classes — used unchanged by both `UserPage` (profile photo) and `CollectionPage` (collection thumbnail, S8).
- **`LocalizedInfo`** (`src/components/LocalizedInfo.jsx`) — The quiet hint + `InfoPopover` that tells an owner they may write **one text per language** (O6): a headline, a description or a tag label can *be* an inline `{lang: text}` map (`{"es": "Las cosas de mamá", "ca": "Les coses de mama"}`) and every member reads their own. Rendered under the description in the thing and collection forms (`variant="text"` — it covers headline *and* description, so there is one hint per field group rather than one per input, DESIGN §3), under the tag editor in the collection forms (`variant="tags"`), and under `RentalRulesFields`' deposit-policy `TextArea` (`variant="policy"`, S6 2026-08 — its own wording rather than reusing `text`, which names "the title or the description" specifically). The panel carries a copy-pasteable example (`.localized-example`, `user-select: all`). Props: `id`, `variant` (`text` | `tags` | `policy`).
- **`InfoPopover`** (`src/components/InfoPopover.jsx`) — Generic (i) icon button that reveals an info panel on hover/focus/click, closing on mouse-leave/blur/**Escape**. The panel appears on hover and on focus, so WCAG 2.1 AA §1.4.13 requires it to be **dismissible** without moving the pointer or the focus — it was not, until 2026-08, and could sit over the field below it with no way out for a keyboard user. A `document`-level Escape listener (live only while the panel is up, and not stopping propagation, so an ancestor dialog still gets its own Escape) closes it and leaves focus on the button; the next hover, focus or click opens it again, so a dismissal is never sticky. **Unlike `TooltipButton` below it needs no separate `dismissed` flag**: that bubble has no toggle of its own and must tell "not hovered" apart from "dismissed", whereas here `open` already *is* the button's disclosure state, so closing is the dismissal and `aria-expanded` stays truthful for free. **The positioning class (`.info-popover-panel`) lives on the wrapper `<div id={id}>`, never passed as `className` to the HDS `Notification`** — Notification's rendered root already carries HDS's own `position: relative` at the same selector specificity as a single custom class, so which one wins the cascade depends on style-injection order (the original bug: BulkInviteCsv's popover sometimes rendered in flow instead of absolutely positioned, squeezing the layout). `aria-controls` is only set while open (axe-valid — a collapsed trigger never references an absent id). Pair with the `.info-popover-row` class (`display:flex; justify-content:space-between`) so the icon sits flush at the row's right edge, keeping the `right: 0`-anchored panel inside the viewport. Props: `title` (panel label + button's accessible name), `children` (panel body), `id` (panel id, referenced by `aria-controls`). Used by `BulkInviteCsv`, `BulkAddCsv`, `ThingForm` and `LocalizedInfo`.
- **`TooltipButton`** (`src/components/TooltipButton.jsx`) — An icon-only HDS `Button variant="supplementary"` that reveals its label in a bubble on hover/focus. **Not** an HDS `Tooltip`: that component renders its own fixed `IconQuestionCircle` trigger and takes the panel content as `children`, so it cannot host an action — and both callers here are actions inside `Table` cells (`MyBookingsPage`'s cancel, `ManageInvitesPage`'s resend/remove). The Button is HDS; only the bubble is ours, and it meets the three WCAG 1.4.13 conditions for hover/focus content: **dismissible** (a `document`-level Escape listener, live only while the bubble is up, hides it without moving pointer or focus — a wrapper-level handler would only ever fire for the keyboard case, since a mouse user hovering the button has focus elsewhere; the dismissal resets on the next reveal so it can never silently disable the affordance), **hoverable** (no `pointer-events: none` — the pointer may travel onto it) and **persistent** (nothing times out). The bubble is `aria-hidden`: it repeats the button's own `aria-label` verbatim, so exposing both would announce the label twice. Styles live in `.tooltip-button` / `.tooltip-button-bubble` (App.css). Props: `tooltip`, `onClick`, `disabled`, `children` (the icon).
- **`BulkAddCsv`** (`src/components/BulkAddCsv.jsx`) — CSV/ZIP bulk-add of things (F-9). Accepts either a plain `.csv` or a `.zip` (CSV + image files). Parses the CSV client-side with **PapaParse** (`header:true`, lower-cased headers), maps the recognised columns (type, headline, description, fee, availability, location, condition, `deposit` — LEND/RENT only, D4, S6 2026-08), plus `tags` (a single cell holding a `|`-separated list — pipe, not comma, since `;`/`,` clash with CSV field delimiters across locales) and `photo` (a filename, ZIP only). For a ZIP it lazy-loads **JSZip** (dynamic `import()` → separate bundle chunk), finds the CSV + images by basename, and on import uploads each referenced photo via the shared `uploadImage` helper (`src/utils/uploadImage.js`, same ticketed upload + 1216px WebP re-encode as `ImageUpload`/`GalleryUpload`), then sends the resulting storage key as `thumbnail` per row. POSTs `{rows}` to `POST /api/v1/collections/{code}/things/bulk/` (atomic all-or-nothing; server rejects HTML, line breaks and `=+-@` spreadsheet-formula injection per field, and validates `tags` against the collection vocabulary + `thumbnail` as a path-safe storage key). Client-side guards: ≤100 rows, every row needs a `headline`, every referenced `photo` must exist in the ZIP. The visible section is just a short help line, the `FileInput`, and an `InfoPopover` (i) — the long column reference, tags/ZIP-photo explanation, `EXAMPLE_CSV` and the "Download example (ZIP)" link all live inside the popover. Props: `collectionCode`, `onImported(count)`. Rendered in AddThingPage in its own `#bulk-add` section, which `/collections/{code}/add#bulk-add` (the collection empty state's "add many" link) scrolls to.
- **`BulkInviteCsv`** (`src/components/BulkInviteCsv.jsx`) — CSV bulk-invite of collection guests. Parses a CSV (`email` required, `name` optional) client-side with PapaParse, previews the addresses, then POSTs to the best-effort batch endpoint `POST /collections/{code}/invite/bulk/`; valid new addresses are invited and emailed, the rest come back as skipped with a reason (invalid/duplicate/already a member/already invited), shown in the result summary. The CSV format reference (`formatTitle`/`formatBody` + an example table) lives in an `InfoPopover` next to the short help line. Props: `collectionCode`, `onInvited()`. Rendered in ManageInvitesPage.
- **`ImageCarousel`** (`src/components/ImageCarousel.jsx`) — Lightweight image carousel ("Image pagination"). Prev/next arrows only (HDS `IconAngleLeft`/`IconAngleRight`, black icons; **`aria-disabled`, never `disabled`** — black-40 — at the first/last image, non-cyclic. A real `disabled` on the button that currently holds focus makes the browser drop focus to `<body>`, which costs the reader their tab position *and* takes focus out of the group where the arrow-key handler lives, so clicking to the last photo silently killed the keyboard. Kept focusable, announced as unavailable; `go()` clamps, so the handler no-ops), plus touch swipe and keyboard arrows. No autoplay, no dots; per-slide `aria-label` ("image X of N"). Rendered when a thing has more than one photo (cover `thumbnail_url` first, then `gallery_urls`); a single photo falls back to a plain `<img>`. Used by `ThingPage` (`variant="detail"`) and by `ThingLinkbox` on the collection grid (`variant="card"` — matches the card cover sizing). Props: `images` (URL array), `alt` (thing headline), `variant` (`detail`|`card`), `to` (optional route — when set the image links to the thing while the arrows only change the photo).
- **`TheeemeSelector`** (`src/components/TheeemeSelector.jsx`) — Visual theeeme picker. Renders a grid of buttons; each button shows three 20 px circular swatches (`color_01`, `color_02`, `color_03`) and the theeeme name, with a checkmark when selected. `aria-pressed` and `aria-label` for accessibility. Props: `theeemes` (array from API), `value` (selected code), `onChange`. Used in EditProfilePage.
- **`KoroSelector`** (`src/components/KoroSelector.jsx`) — Visual koro picker. Renders a grid of buttons; each button shows a live `<Koros>` SVG preview (white fill on black background, 50 px tall, scaled to fit) and the koro label. Props: `value` (selected type string), `onChange`. Used in EditProfilePage.
- **`ShareCollectionMenu`** (`src/components/ShareCollectionMenu.jsx`) — Owner-only share menu rendered in the CollectionPage hero. HDS `Select` with four share options (`IconEnvelope` for email, `IconShare` for copy-link, `IconWhatsapp` for WhatsApp, `IconCamera` for a QR dialog). URL resolution depends on the `isPublic` prop: **private** collections call `POST /api/v1/collections/{code}/share-link/` lazily on first interaction and share the `/share/{token}` join link; **public** collections skip that call and share the collection URL directly (`${window.location.origin}/collections/{code}`) — no email gate, since public collections are anonymously readable. The resolved URL is cached via `useRef` and dispatched: `mailto:` for email, `navigator.clipboard.writeText` + Toast for copy, `https://wa.me/?text=` for WhatsApp, an HDS `Dialog` with a `qrcode.react` QR for the QR action — `qrcode.react` is `React.lazy`-loaded inside a `Suspense`, so it ships in its own chunk instead of `CollectionPage`'s, and only loads once the owner opens the QR dialog. For **PRIVATE** collections the menu also offers **Rotate link** and **Stop sharing** — each opens a consequence-confirm `Dialog`, then `POST {rotate: true}` / `DELETE`s the share token so the owner can pull back a bearer credential they've handed out (DESIGN §9); PUBLIC collections omit these (no token to revoke). The Select's value is reset on every change so it acts as a one-shot menu rather than a form input. Strings live in the `shareMenu` i18n namespace. Props: `collectionCode`, `collectionHeadline`, `ownerName`, `isPublic`.

### What this deployment adds (`src/deployment/`)

The frontend half of the backend's `DEPLOYMENT_URLCONFS` / `CREATOR_POLICY` extension points. **Upstream exports nothing but empties** — the app renders exactly as it did before the indirection existed. A deployment with pages of its own **replaces the whole directory** instead of editing `App.jsx`, `LoginPage.jsx`, `SiteFooter.jsx` or the locale files: those are files upstream keeps changing, and editing them buys a merge conflict on every update, while a directory it owns outright has none. (The same trick already worked by accident for `src/legal/{lang}.js`; here it is deliberate.)

| Export | Consumed by | Meaning |
|---|---|---|
| `deploymentRoutes` | `App.jsx` | `[{path, Component}]`, `Component` usually `lazy(() => import(...))` like every other route. Mounted **above** `path="*"` — a route declared after the catch-all renders the 404 page instead, and nothing else about the app looks wrong |
| `popInPath` | `LoginPage` | Where the "new here?" button goes, or `null` for **no button at all** — the honest answer upstream, where the only ways in are an invitation and a share link |
| `aboutPath` | `SiteFooter`, `CollectionPage`, `VerifyPage`, `HomePage` | A page saying what this deployment *is*, or `null` for none. Null upstream: what OIUEEI is belongs in the README, and an operator's own pitch belongs to the operator. It decides the footer's about link, the first-time box on a freshly-joined collection, the dashboard empty state's second button, and where `landing: "welcome"` sends a new visitor (home, when there is no such page) |
| `faqPath` | `LoginPage` | Where this deployment's help/FAQ page lives, or `null` for none. Linked from `/login`, the door with the most traffic — a FAQ answers questions about a *particular* deployment (who operates it, what it lets people create, how to ask for something it holds back), so it has no home upstream. Rendered right under the "trouble signing in?" line, same `null`-means-no-link shape as `aboutPath` (S4, 2026-08) |
| `deploymentI18n` | `i18n/index.js` | `{lang: bundle}`, deep-merged into the `translation` namespace — but **only for a language whose own file is already in memory**, and re-applied on every i18next `loaded` event. Both halves are load-bearing and each was a bug: registering a bundle for a language that has *not* loaded makes i18next consider it present and never fetch its chunk (a deployment that translated three strings into Spanish got those three and the rest of the UI in English, permanently — the `es` bundle went from 60 keys to 1); and registering only at startup loses the deployment's strings the moment `es`/`ca` land, since an incoming bundle merges over what is there. Pinned by `src/test/i18nDeployment.test.js` |

Covered by `src/test/deployment.test.jsx`, which mocks the module — upstream's values are the empty ones, so that is the only way to exercise a replacement from this repository.

### Constants (`src/constants/things.js`)

Central source of truth for thing type definitions. Display labels are handled by i18n — use `t('types.GIFT_THING')` etc.
- `TYPE_VALUES` — Array of type value strings (no labels — labels come from i18n).
- `DATE_TYPES` — Types requiring start/end dates (`LEND_THING`, `RENT_THING`).
- `FEE_TYPES` — Types with a fee field (`SELL_THING`, `RENT_THING`).
- `DETAIL_TYPES` — Types with availability/location/condition fields (`GIFT_THING`, `SELL_THING`, `LEND_THING`).
- `AVAILABILITY_VALUES` — Array of availability value strings (labels from i18n).
- `CONDITION_VALUES` — Array of condition value strings (labels from i18n).
- `TAG_THEMES` — Theme objects for status tags (taken, inactive, pending).

---

## Internationalisation (i18n)

All UI strings are externalised via `react-i18next`. No hardcoded strings in components.

- **Setup:** `src/i18n/index.js` initialises i18next with `i18next-browser-languagedetector` (detection order `localStorage` → `navigator`, the chosen language cached in `localStorage`), falling back per `fallbackLng` for unsupported languages. **English (the fallback) is bundled eagerly** in `resources` so the first paint is always translated; Spanish and Catalan load on demand through a tiny custom i18next backend (`partialBundledLanguages: true`, `load: 'currentOnly'`) — see Locale files.
- **Supported languages:** English (`en`), Spanish (`es`), Catalan (`ca`).
- **Retired languages:** Brazilian Portuguese (`pt-BR`), European Portuguese (`pt-PT`), Basque (`eu`), and Galician (`gl`) were dropped from `supportedLngs`/`resources` 2026-07 (paused, not deleted — the locale JSONs are recoverable from git history). `fallbackLng` is an object mapping each retired code (plus bare `pt`) to `['es']`, with `default: ['en']` for any other unsupported browser language.
- **Locale files:** `src/i18n/locales/{lang}.json` — one JSON file per language with ~690 keys organised by namespace (common, titles, login, verify, home, collectionPage, thingPage, types, availability, condition, etc.). Only `en.json` ships in the main bundle; `es.json`/`ca.json` (~35 kB each) are **code-split into their own Vite chunks** via the backend's `import()` of the locale JSON and fetched only when that language is active (a non-English visitor briefly sees English before the chunk lands — `react: { useSuspense: false }`, so no spinner).
- **`html[lang]`:** updated dynamically in `App.jsx` via `i18n.on('languageChanged', ...)` — but that runs after React mounts, so the very first paint (and every crawler) used to see the static `lang="en"` in `index.html` regardless of the visitor's actual language. `public/detect-lang.js` (A3, 2026-08) closes that gap: a synchronous, dependency-free script loaded via `<script src="/detect-lang.js">` (an **external** file — CSP's `script-src 'self'` has no `'unsafe-inline'` in production, `core/middleware.py`, so an inline block would be silently dropped) that mirrors `i18next-browser-languagedetector`'s own priority (saved `i18nextLng` in `localStorage`, then `navigator.languages`) and `src/i18n/index.js`'s `fallbackLng` map, so it never disagrees with what i18next settles on once it loads. Tested by sandbox-evaluating the real file's source (`src/test/detectLang.test.js`), since it can import nothing a browser wouldn't have yet.
- **Usage:** every page and component imports `useTranslation` and calls `t('namespace.key')`. Select options are built inline: `TYPE_VALUES.map(v => ({ label: t('types.' + v), value: v }))`.
- **Initialisation:** `import './i18n'` in `App.jsx` (before HDS imports).

---

## Analytics

OIUEEI ships with **no third-party analytics**. There is no SDK, no event-tracking service, no consent banner, no opt-out toggle. See [DESIGN.md §9](../DESIGN.md#9-user-data-is-never-a-product) for the underlying principle.

---

## Testing

Smoke tests and automated accessibility checks using vitest + testing-library + jest-axe.

- **Run tests:** `npm test` (single run) or `npm run test:watch` (watch mode).
- **Config:** `vite.config.js` — `test` block with jsdom environment, `src/test/setup.js` as setup file.
- **Setup:** `src/test/setup.js` — imports `@testing-library/jest-dom`, initialises i18n mock, provides `localStorage`, `CSS.supports`, and `ResizeObserver` polyfills for jsdom.
- **Smoke tests:** `src/test/smoke.test.jsx` — renders every page component with mocked API responses and runs `jest-axe` to detect WCAG violations. Covers all 29 page components.
- **i18n mock:** `src/test/i18n-mock.js` — initialises i18next with the real `en.json` for test rendering.
- **Linting (A5, 2026-08):** `eslint.config.js` runs `jsx-a11y.flatConfigs.strict`, not `recommended` — matching the ratchet culture elsewhere in this repo (coverage, dependency audit): a stricter floor than the framework default, checked automatically rather than hoped for. Switching it turned up exactly two findings, both `no-static-element-interactions` on the same deliberate idiom: `InfoPopover` and `TooltipButton` wrap a real, fully keyboard-accessible HDS `Button`/`<button>` in a plain `<span>`/`<div>` that only listens for the child's focus/blur bubbling up, to control a hover/focus-revealed panel's visibility. The wrapper is never itself a keyboard target, so the rule's fix (give it a role and full keyboard support) would be solving a problem that isn't there; both carry a scoped `eslint-disable-next-line` immediately above the tag, with the reasoning inline rather than silent.

---

## Tech Stack

- **React 19** + **Vite 7** + **React Router 8**

**Import from `react-router`, never `react-router-dom`.** v8 consolidated the two packages — there is no `react-router-dom@8` — so the dependency is `react-router` alone and every `import { Link, useNavigate, … } from 'react-router'`. Test files that stub the router (`vi.mock`) must name the same specifier, or the mock silently applies to nothing. The upgrade came from the 2026-08 security round: it is what closed GHSA-qwww-vcr4-c8h2 and let the audit gate's allowlist go back to empty. It also raised the React floor — react-router 8 peer-depends on `react >= 19.2.7`, so `react`/`react-dom` moved to `^19.2.8` with it.
- **hds-react** — Helsinki Design System React components (npm `^6.0.5`)
- **hds-design-tokens** — HDS CSS custom property tokens (npm `^6.0.5`)
- **hds-core** — HDS core CSS and base styles (npm `^6.0.5`)

### The dependency audit gate (`scripts/audit-gate.mjs`)

CI runs `node scripts/audit-gate.mjs` instead of `npm audit --audit-level=high`. Same threshold — it fails on any high or critical advisory — but it can accept a named one, which plain `npm audit` cannot. Without that, a single unfixable finding leaves only two options: a permanently red pipeline, or dropping the whole gate to `critical` and silently ceasing to guard every other high.

An allowlist entry requires **both** conditions, written into the script next to the id: the advisory has **no published fix**, and its vulnerable path **cannot be reached from this app**. It also records what would let it be deleted. A high with a fix we simply haven't applied must never be listed. The script also flags an entry that no longer matches anything (fixed or withdrawn upstream) so the list doesn't rot — as a message, not a failure, since a greener audit must not turn the build red.

The decision is a pure function (`evaluateAudit(report, allowlist)`); running npm, printing and exiting sit around it, and importing the module runs nothing. That split exists so `scripts/audit-gate.test.js` can exercise the gate itself — a gate nobody tests can quietly stop guarding, and the failure looks exactly like a green build. The suite pins what blocks (unlisted high/critical), what doesn't (moderate/low, listed entries), that listing one advisory never stops the others blocking, that a stale entry is reported but never fails the build, that `npm audit`'s non-zero exit on findings is normal while a scanner that **couldn't run** is fatal, and that every real allowlist entry carries all three justifications.

**Currently allowed: nothing** — `ALLOWED` is `{}`, and that is the state to keep it in. The only entry it ever held was **GHSA-qwww-vcr4-c8h2** (react-router RSC-mode CSRF), accepted because the fix, react-router `8.3.0`, was unpublished and npm's only suggestion was a downgrade to 7.11.0 that reintroduced four advisories 7.18.2 had fixed. 8.3.0 shipped, so the debt was paid the way an allowlist entry is meant to be — by taking the upgrade and deleting the entry, not by re-justifying it. When the list is empty, `every real entry justifies itself on both counts` iterates nothing, so a companion test pins the bar itself against entries that must fail it; keep that pairing if you ever add an entry back.

### `overrides` in `package.json`

Four transitive pins, all security patches for packages we don't depend on directly. Scope each to its parent rather than pinning globally, so an unrelated consumer isn't dragged to the same version:

| Override | Why |
|---|---|
| `@typescript-eslint/typescript-estree` → `minimatch@9.0.9` | pre-existing |
| `eslint-plugin-jsx-a11y` → `brace-expansion@1.1.18` | high DoS in `<1.1.18`; stays on the 1.x line, since `minimatch@3` needs `^1.1.7` |
| `jsdom` → `undici@7.29.0` | five advisories in `<7.29.0`. **This pin is itself what holds the version** — when bumping, check the advisory floor, not just that it installs |
| `@eslint/eslintrc` → `js-yaml@4.3.1` | high quadratic-CPU in `!!omap` resolution (GHSA-5p4m-2wfm-xmqj, `>=4.0.0 <4.3.1`). Stays on the 4.x line (`v4-legacy`, which is where the fix was published): eslintrc wants `^4.1.1`, so v5 would be a needless major for a dev-only dependency |
| `postcss` → `^8.5.25` (top level) | high path traversal in `sourceMappingURL` auto-loading (`<=8.5.17`). Top-level is safe here: `hds-react` and `vite` both want `^8`. **Do not take npm's suggested fix** — it downgrades `hds-react` to 5.2.2 and undoes the HDS 6 upgrade |

Never run `npm audit fix --force` in this repo: its "fixes" include major downgrades of `hds-react`.

### HDS Select quirks

Every `<Select>` must say which language HDS should speak, because its own
assistive wording ("choose one", "2 selected options", "clear current
selection") defaults to **Finnish**. In HDS 5 that was the `language="en"` prop,
and this file said so for a year. **HDS 6 moved it inside `texts`** —
`texts={{ label: …, language: 'en' }}` — and ignores the prop silently: the
component still renders, the page still looks right, and the only thing that
changes is what a screen reader reads out. Fourteen Selects spent the HDS 6
upgrade announcing themselves in Finnish, and no axe rule catches it (none
compares the language of an `aria-label` against the page's). `src/test/
selectLanguage.test.jsx` now renders one such form *and* sweeps the source for
the dead prop, since the failure is invisible on screen.

`'en'` is the honest value everywhere: HDS ships fi/sv/en, and none of this
product's three locales is among the other two.

`language="en"` is still right on `DateInput` and `Accordion`, which do honour
it — verified, not assumed.

Additional API notes: `value` is an array (`[{ label, value }]`), `onChange`
receives an array (`(sel) => sel[0].value`), error text uses the `error` prop
(string), not `errorText`.

### HDS ToggleButton quirks (v5)

Four non-obvious behaviours:

1. **`onChange` receives the current value, not the new one.** Always negate: `onChange={(val) => setState(!val)}`.
2. **`style` prop targets the inner `<button>`, not the flex container.** Flex layout overrides via `style` have no effect. Use `<div className="toggle-left">` wrapper instead — the `.toggle-left` CSS class in `App.css` reverses the flex direction to put the pill on the left.
3. **`disabled + checked` renders light grey by default.** Overridden to `--color-black-90` in `App.css` via `.toggle-left button[aria-pressed="true"][disabled]`.
4. **Multi-line labels (title + `<br/>` + long helper) wrap the pill onto a new row.** HDS's inline container allows wrap by default; a long helper makes the label wider than the available row and the pill drops below. Fixed in `.toggle-left` with `flex-wrap: nowrap; align-items: flex-start` on the container plus `flex-shrink: 0` on the inner button.

### Links — three kinds, and why HDS `Link` is not used yet

> Superseded in part by **A link that looks like a button** below: the 2026-08-30
> keyboard round found a fourth kind this list missed — a router `Link` wrapped
> around an HDS `Button`, 25 of them — and they are now `ButtonLink`, built on HDS's
> own `Link`. So this app does import HDS `Link` after all, just not yet for kind 3
> (external links), where the reasoning below still stands.

HDS ships a `Link` component and this app imports it **nowhere**, which under DESIGN §1 needs a reason rather than a silence. Reviewed 2026-08-17; the reason is that "link" here means three different things:

1. **Internal navigation** — react-router's `Link`, and it has to be: an HDS `<a>` would reload the SPA. This is the overwhelming majority, and it is not a deviation at all (HDS has no router).
2. **Generated HTML** — `MarkdownText` builds `<a href=…>` as a **string** and injects it. A React component cannot go there without rewriting the whole renderer, and that renderer is where the escaping invariant lives (see `MarkdownText`). Off the table.
3. **External links in JSX** — 6 sites (`FeedbackLink`, `ApprovalNotice`, `PdfUpload`, `LoginPage` ×2, `EditProfilePage`), all `<a target="_blank" rel="noopener noreferrer">`. **This is the one HDS `Link` should own**, and the one place it would add something real: `external` + `openInNewTab` render the outbound icon and announce the new tab, which none of the six do today.

What has kept (3) from happening is not the component, it is that it is a **copy change in three languages**: HDS's `openInNewTabLabel` defaults to Finnish (`"(avautuu uudessa välilehdessä)"`, the same trap as `Select`'s `language="fi"`), so adopting it means three new i18n keys ×3 locales plus a visible label and icon appearing next to six links — including two inside `<Trans>` placeholders. That is a design decision with visible consequences, not a refactor, so it belongs to a design pass with someone looking at it, not to a pre-release cleanup.

### HDS SelectionGroup quirks

Two, and the first one fails **silently** — both learned the expensive way while replacing the hand-rolled `<fieldset>` in `CollectionModeField`:

1. **It does not flatten its children.** `{options.map(...)}` arrives as a single child that *is* an array, `isValidElement` rejects it, and the whole group renders empty — a fieldset with a legend and no radios, no error anywhere. Pass one flat array instead: `{[...optionFields, <Extra key="…" />]}`.
2. **It re-wraps every child in a `<div key={child.props.id}>`.** A child without an `id` prop gets `key: undefined`, so React logs a missing-key error for each one. Children that are wrappers rather than HDS controls therefore carry an `id` they have no other use for.

It also owns the vertical rhythm (`--spacing-row`, a grid `gap`), so per-option margins are its job, not the caller's.

### HDS accessibility bugs we carry

Found in the **2026-08-30 keyboard round**, all in `hds-react@6.0.5`, all verified
against the shipped bundle rather than the docs. The decision each time was the
same and it is deliberate: **stay on HDS, work around it only where the workaround
is itself an HDS API, and wait for upstream on the rest.** Delete an entry here
when a release fixes it — do not let one rot into a permanent local fork.

**1. `Linkbox` announces as a region, not a link.** It renders
`<div role="region" tabindex="0">` with the real `<a>` inside at `tabindex="-1"`,
and activates it from an `onKeyPress` handler. So the card *is* reachable (one tab
stop) and Enter *does* follow it — but it is announced as "region", it never appears
in a screen reader's list of links, **Space does not activate it**, and `onKeyPress`
is a deprecated React alias. HDS's own documentation site renders the identical
markup, so this is theirs, not a misuse. **Not worked around** — the only fix is to
stop using the component, which costs more than the defect. Affects the collection
grids on `HomePage` and `UserPage` (`CollectionLinkbox`).

**2. A deletable `Tag` has no name for what it does.** v6 makes the *whole chip* the
control — one `<div role="button">` named from its own text — and there is no
`deleteButtonAriaLabel` prop any more. A screen reader announces "button, Vintage"
and nothing about removal. **Worked around**: `TagInput` passes its own `aria-label`
(the rest props land on that div, last in the `Object.assign`, so it wins). Pinned by
`TagInput.test.jsx`.

**3. Nine components hard-code their focus ring to `var(--color-coat-of-arms)`**
instead of reading `--color-focus-outline` the way the rest of HDS does —
`DatePicker` days, `DialogHeader`'s close and title, `Linkbox`, `Notification`'s
label, `Table`'s sort button, `ToggleButton`. They also set `outline: none` and draw
their own `box-shadow`, at a specificity a global rule cannot reach, so the two-tone
ring in `App.css` does not apply to them. See the focus-ring comment there for why a
single colour fails; `#0072c6` clears 3:1 on only 31 of the 48 theeeme surfaces.

**4. Icons carry no `aria-hidden`.** `IconFoo` renders a bare decorative `<svg>`, so
**every** call site has to add `aria-hidden="true"` itself (or a label, when the icon
is the only content). There is no default and no lint rule; the audit found two that
had been missed.

**5. An inline `Notification` is announced by nobody.** It gets `role="alert"`
**only** when it is positioned — a toast. Inline, it gets no role at all, so of the
42 in this app exactly one was ever announced: press Save, have it fail, and a
screen reader said nothing. That is WCAG 4.1.3 Status Messages, level AA. The role
cannot be supplied from outside either — HDS spreads rest props *before* its own
`role: … : void 0`, so passing one is erased. **Worked around** two ways, by shape:
a message that is *appended* to the page goes inside `StatusRegion`, a live region
that renders unconditionally so it pre-dates its own content; a message that
*replaces* the form gets HDS's `autofocus`, which both rescues the focus the
vanished submit button was holding and gets the message read. A load error that
*is* the page needs neither — it is read in document order.

**6. `Link`'s new-tab and external-domain labels default to Finnish**
(`"avautuu uudessa välilehdessä"`, `"Siirtyy toiseen sivustoon."`) — the same trap as
`Select`'s `language`, and just as invisible, since it only changes what is announced.
Any adoption of `Link` with `openInNewTab` or `external` **must** pass
`openInNewTabLabel` / `openInExternalDomainAriaLabel` in all three locales.

### A link that looks like a button: `ButtonLink`

`Button` always renders `<button>` — there is no `as` or `href` prop, and wrapping it
in a router `<Link>` produces nested interactive elements: **two tab stops for one
control**, announced "link… button", with the `<a>` taking the focus ring while the
`<button>` carries the look. `jsx-a11y` has no rule for it and **axe reports no
violation**, which is how 28 of them accumulated.

HDS's own answer is `Link`'s `useButtonStyles`, which swaps the link class for
`hds-button hds-button--primary` — the real button CSS, same `--computed-*` token
chain. `src/components/ButtonLink.jsx` wraps it, and **25 call sites across 11 files
now use it**:

```jsx
<ButtonLink to={editPath} fullWidth style={btnSecondaryStyle}>{t('common.edit')}</ButtonLink>
```

Three things about it are load-bearing:

- **There is no `variant` prop.** What makes a button secondary here is the token
  set (`btnSecondaryStyle`), not HDS's variant class, so the same element serves
  both. HDS's own `hds-button--secondary` is a hashed CSS-module name we could not
  address even if we wanted it.
- **`fullWidth` is ours** (`.button-link--full`, one declaration) — `Link` has no
  such prop, and the base class already centres the label.
- **The `<a>` it renders IS the button** — `hds-button--primary`'s background,
  border and padding sit on the `<a>` itself, with a `<span>` inside for the
  label. So a rule that removes the `<a>`'s box (`display: contents`, `display:
  none`) paints none of that and drops it out of the a11y tree. This bit the
  card grid: `.thing-card-buttons a { display: contents }` was added in 2026-03
  to flatten the then-`<Link><Button>` wrapper, and the 2026-08 migration left
  it stripping the card's primary "Edit" to a bare text link. Removed, with a
  source-sweep guard in `ButtonLink.test.jsx`.
- **Only a plain left click is intercepted.** A cmd/ctrl/shift/alt or middle click
  falls through to the real `href`, so open-in-new-tab keeps working. Losing that is
  the usual price of hand-rolling this, and it is exactly what a real link buys.
  Pinned by five cases in `ButtonLink.test.jsx`.

This flips the element's role, so a test looking for `getByRole('button')` on one of
these has to look for `link`. Seven assertions moved when the 25 landed, and each got
stronger for it: "this is a link" says more than "this is a button".

One caveat for anyone counting these: **a regex will undercount them.** The sweep that
found the first 23 missed two more whose `<Link>` held a ternary rather than a `<Button>`
directly. The runtime invariant found those; grep did not.

## OIUEEI Customization Layer

The project consumes HDS directly from npm and applies three local overrides:

- **Fonts** (`src/fonts/oiueei-fonts.css`) — the **Curiosa** variable font (`public/fonts/curiosa/Curiosa-Variable.woff2`, weight + italic axes), declared via `@font-face` honestly as `font-family: "Curiosa"` and served by Vite at `/fonts/curiosa/`. The HDS `--font-default` token's *value* is overridden to `"Curiosa", Arial, sans-serif` in `src/styles/oiueei-theme.css` — the token *name* is kept, so all HDS components resolve it transparently. The font binary is gitignored (licence); a clone without it falls back to Arial / system sans.
- **Colors** (`src/styles/oiueei-theme.css`) — CSS custom property overrides for the "Theeemes" color palette, imported after `hds-design-tokens` to take precedence.
- **Logos & brand assets** (`src/assets/`) — OIUEEI logos, placeholders, and favicon.

## Key Configuration (`vite.config.js`)

- **React deduplication** — Aliases `react` and `react-dom` to frontend's `node_modules` to prevent dual-copy hook errors (some HDS internal deps declare React 17 peer dep)
- **Proxy** — `/api` requests forwarded to `http://localhost:8000`
- **Dev server** on port 3000
- **Code splitting** — every page is `React.lazy`-loaded in `App.jsx` (the `Routes` block is wrapped in a `Suspense` whose fallback is `LoadingSpinner`), so each route ships as its own chunk and page-only deps (papaparse, qrcode, jszip) load on demand. `build.rollupOptions.output.manualChunks` further splits `vendor-react` and `vendor-hds` from app code for long-term caching (`chunkSizeWarningLimit` is raised to **650 kB** because the shared `hds-react` chunk is **~622 kB raw / ~161 kB gzipped** — measured 2026-08-17, and it grows by a few kB each time a new HDS component is adopted: 585 → 614 on the 6.0.4 → 6.0.5 upgrade, 615 → 622 on taking `SelectionGroup`. Tree-shaking does work — `CookieConsent`, `Hero`, `Footer`, `Pagination`, `Stepper`, `Tabs` and `Breadcrumb` are absent from the built chunk — so the size is what we genuinely use).

## Authentication Flow

1. User enters email on `/login`
2. Backend sends magic link email pointing to `localhost:3000/verify/{rsvp.token}` — the high-entropy token, never the 6-char RSVP code
3. `/verify/:code` calls the backend, which sets JWT tokens as HttpOnly cookies on the response
4. `userCode` is stored in `localStorage` (for ownership checks only — auth tokens are never in localStorage)
5. Authenticated pages use `credentials: 'include'` to send cookies automatically. On 401, `apiFetch` silently attempts token refresh via `POST /api/v1/auth/refresh/`
6. `userCode` is used to determine ownership (e.g. hide reservation button on own things)
7. CSRF cookie is obtained on app load via a GET to `/api/v1/auth/me/`
