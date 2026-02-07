# OIUEEI Models Documentation

This document describes the behaviour and business rules for each model in the OIUEEI application. It serves as a reference for Claude and other collaborators to understand the intended use cases.

---

## User

The `User` model represents a person who can own collections, be invited to others' collections, and create things.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_code` | CharField(6) | Auto | Primary key, 6-character alphanumeric ID |
| `user_email` | CharField(64) | **Yes** | Unique email address for authentication |
| `user_name` | CharField(32) | No | Display name |
| `user_created` | DateField | Auto | Date the user was created |
| `user_last_activity` | DateField | Auto | Date of last login/activity |
| `user_own_collections` | JSONField | No | List of collection_codes the user owns |
| `user_invited_collections` | JSONField | No | List of collection_codes the user has been invited to |
| `user_things` | JSONField | No | List of thing_codes the user owns |
| `user_headline` | CharField(64) | No | Short bio/tagline |
| `user_thumbnail` | CharField(16) | No | Cloudinary image ID for avatar |
| `user_hero` | CharField(16) | No | Cloudinary image ID for banner |

### Business Rules

1. **Email is mandatory and unique** - A user must have an email address, and no two users can share the same email. This is enforced at the database level with `unique=True`.

2. **Optional profile fields** - The `user_headline`, `user_thumbnail`, and `user_hero` fields are optional and default to empty strings.

3. **Multiple owned collections** - A user can create and own multiple collections. The `user_own_collections` field stores a list of collection codes.

4. **Multiple invited collections** - A user can be invited to multiple collections owned by others. The `user_invited_collections` field stores these invitations.

5. **Multiple things** - A user can create multiple things (items) for their own collections. The `user_things` field tracks what they own.

6. **Cannot create things for others' collections** - A user can only add their own things to their own collections. This is enforced at the view level, not the model level.

7. **Creation date is persisted** - The `user_created` field is automatically set to today's date when the user is created.

8. **Last activity is updated on login** - The `update_last_activity()` method should be called on each successful authentication to track when the user was last active.

### Methods

- `update_last_activity()` - Updates `user_last_activity` to today's date
- `has_perm(perm, obj)` - Returns True only for superusers
- `has_module_perms(app_label)` - Returns True only for superusers

### Authentication

Users authenticate via magic link (passwordless). The `UserManager` handles user creation:
- `create_user(user_email)` - Creates a regular user, validates email is provided
- `create_superuser(user_email)` - Creates a superuser with `is_staff=True` and `is_superuser=True`

### Related Models

- **Collection** - Users own collections via `collection_owner` field
- **Thing** - Users own things via `thing_owner` field
- **RSVP** - Magic link tokens reference users via `user_code`
- **BookingPeriod** - References users as `requester_code` and `owner_code`

---

## Collection

The `Collection` model represents a list of things (gifts, items for sale, lending items, etc.) owned by a user. Collections can be shared with other users via invites.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `collection_code` | CharField(6) | Auto | Primary key, 6-character alphanumeric ID |
| `collection_owner` | CharField(6) | **Yes** | User code of the owner |
| `collection_created` | DateTimeField | Auto | Timestamp when collection was created |
| `collection_headline` | CharField(64) | **Yes** | Title of the collection |
| `collection_description` | CharField(256) | No | Description of the collection |
| `collection_thumbnail` | CharField(16) | No | Cloudinary image ID for thumbnail |
| `collection_hero` | CharField(16) | No | Cloudinary image ID for banner |
| `collection_status` | CharField(8) | No | Status: ACTIVE (default) or INACTIVE |
| `collection_things` | JSONField | No | List of thing_codes in this collection |
| `collection_invites` | JSONField | No | List of user_codes who can view this collection |
| `collection_theeeme` | ForeignKey | **Yes** | Reference to Theeeme (colour palette) |

### Business Rules

1. **ACTIVE by default** - A collection starts with `collection_status="ACTIVE"`. The owner can deactivate it later.

2. **Owner manages all fields** - Only the owner can update the collection's headline, description, images, status, and theeeme.

3. **Only owner adds/removes things** - The `add_thing()` and `remove_thing()` methods modify `collection_things`. This is enforced at the view level.

4. **Only owner invites/revokes** - The `add_invite()` and `remove_invite()` methods modify `collection_invites`. Only the owner can call these.

5. **Visible only to owner and invites** - The `can_view()` method returns True only if the user is the owner or is in `collection_invites`.

6. **Accepts all thing types** - A collection can contain things of any type: GIFT_THING, SELL_THING, ORDER_THING, RENT_THING, LEND_THING, SHARE_THING.

### Methods

- `add_thing(thing_code)` - Adds a thing to the collection (idempotent, no duplicates)
- `remove_thing(thing_code)` - Removes a thing from the collection
- `add_invite(user_code)` - Invites a user to view the collection (idempotent, no duplicates)
- `remove_invite(user_code)` - Revokes a user's invite
- `is_owner(user_code)` - Returns True if user is the owner
- `is_invited(user_code)` - Returns True if user is in the invites list
- `can_view(user_code)` - Returns True if user is owner OR invited

### Theeeme Relationship

- Collections have a **required** FK to Theeeme with `on_delete=PROTECT`
- This prevents deleting a Theeeme that is in use by any collection
- A default Theeeme ("BAR_CEL_ONA") is used when creating collections without specifying one

### Validations

| Field | Validation | Level | Error |
|-------|------------|-------|-------|
| `collection_headline` | Required | Serializer | 400 Bad Request |
| `collection_theeeme` | Must exist | Serializer (SlugRelatedField) | 400 Bad Request |
| `collection_things` | Thing must exist | View | 404 Not Found |
| `collection_things` | Thing must belong to owner | View | 403 Forbidden |
| `collection_owner` | From authenticated user | View | Always valid |
| `collection_invites` | User created if not exists | View (get_or_create) | Always valid |

### Related Models

- **User** - Owner via `collection_owner` field
- **Thing** - Things in the collection via `collection_things` array
- **Theeeme** - Colour palette via FK `collection_theeeme`

---

## Theeeme

The `Theeeme` model represents a colour palette for customising collections. Each theeeme has 6 colours.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `theeeme_code` | CharField(6) | Auto | Primary key, 6-character alphanumeric ID |
| `theeeme_name` | CharField(16) | **Yes** | Name of the theeeme |
| `theeeme_01` | CharField(6) | **Yes** | Hex colour code (without #) |
| `theeeme_02` | CharField(6) | **Yes** | Hex colour code (without #) |
| `theeeme_03` | CharField(6) | **Yes** | Hex colour code (without #) |
| `theeeme_04` | CharField(6) | **Yes** | Hex colour code (without #) |
| `theeeme_05` | CharField(6) | **Yes** | Hex colour code (without #) |
| `theeeme_06` | CharField(6) | **Yes** | Hex colour code (without #) |

### Business Rules

1. **Each collection has a theeeme** - Collections are personalised with a `collection_theeeme` FK.

2. **Default theeeme is BAR_CEL_ONA** - When creating a collection without specifying a theeeme, the default "BAR_CEL_ONA" (code: JMPA01) is used.

3. **Theeeme must exist before assignment** - The `theeeme_code` is validated via `SlugRelatedField` before persisting to a collection. Returns 400 Bad Request if not found.

4. **Only collection owner can change theeeme** - The `collection_theeeme` can only be updated by the `collection_owner`. Returns 403 Forbidden for non-owners.

5. **Protected deletion** - Theeemes cannot be deleted if any collection references them (`on_delete=PROTECT`).

### Default Theeeme

| Field | Value |
|-------|-------|
| `theeeme_code` | JMPA01 |
| `theeeme_name` | BAR_CEL_ONA |
| `theeeme_01` | FFCA2C |
| `theeeme_02` | CB4E22 |
| `theeeme_03` | 827F2A |
| `theeeme_04` | 2B9A9E |
| `theeeme_05` | 4F3B28 |
| `theeeme_06` | FFF2EB |

### Related Models

- **Collection** - References theeeme via `collection_theeeme` FK

---

## FAQ

The `FAQ` model represents a question and answer about a thing. Invited users can ask questions, and only the thing owner can answer or hide them.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `faq_code` | CharField(6) | Auto | Primary key, 6-character alphanumeric ID |
| `faq_thing` | CharField(6) | **Yes** | Reference to Thing.thing_code |
| `faq_created` | DateTimeField | Auto | Timestamp when FAQ was created |
| `faq_questioner` | CharField(6) | **Yes** | User code of who asked the question |
| `faq_question` | CharField(64) | **Yes** | The question text |
| `faq_answer` | CharField(256) | No | The answer text (empty until answered) |
| `faq_is_visible` | BooleanField | No | Whether FAQ is visible (default: True) |

### Business Rules

1. **FAQ linked to Thing** - Each FAQ is related to a thing via `faq_thing`.

2. **Things can have multiple FAQs** - Things store FAQ codes in `thing_faq` JSONField array.

3. **Only invited users can ask** - Only users in `collection_invites` (of the collection containing the thing) can create FAQs.

4. **Questioner is tracked** - The `faq_questioner` is set to the user who creates the FAQ.

5. **Owner cannot ask questions** - The `collection_owner` (thing owner) cannot create FAQs about their own things. Returns 400 Bad Request.

6. **Only owner can answer** - Only the thing owner can call `/faq/{code}/answer/`. Returns 403 Forbidden for others.

7. **Default visible** - New FAQs have `faq_is_visible=True` by default.

8. **Only owner can change visibility** - Only the thing owner can hide/show FAQs via `/faq/{code}/hide/` or `/faq/{code}/show/`.

9. **Email to owner on question** - When an invited user asks a question, the owner is notified by email.

10. **Owner has two options** - Owner can either answer the question or hide it (set `faq_is_visible=False`).

11. **Email to questioner** - When owner answers or hides a FAQ, the questioner is notified by email.

### Methods

- `has_answer()` - Returns True if `faq_answer` is not empty
- `answer(answer_text)` - Sets the answer and saves

### Visibility Rules

- **Owner** sees all FAQs (visible and hidden)
- **Invited users** see only visible FAQs (`faq_is_visible=True`)
- **Questioner** can see their own hidden FAQ

### Related Models

- **Thing** - FAQ is about a thing via `faq_thing`
- **User** - Questioner via `faq_questioner`

---

## RSVP

The `RSVP` model is the central intermediary for all email-based actions. It serves two primary purposes:
1. **Magic link authentication** - Passwordless login via email
2. **Action intermediary** - All email links use RSVP codes to avoid exposing real codes (booking_code, reservation_code, etc.) in URLs

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `rsvp_code` | CharField(6) | Auto | Primary key, 6-character alphanumeric ID |
| `rsvp_created` | DateTimeField | Auto | Timestamp when RSVP was created |
| `user_code` | CharField(6) | **Yes** | User code of the recipient |
| `user_email` | CharField(64) | **Yes** | Email address of the recipient |
| `rsvp_action` | CharField(20) | No | Action type (default: MAGIC_LINK) |
| `rsvp_target_code` | CharField(6) | No | Target object code (reservation_code, booking_code) |
| `collection_code` | CharField(6) | No | Collection code for COLLECTION_INVITE action |
| `rsvp_context` | JSONField | No | Additional context data for the action |

### Action Types

| Action | Description |
|--------|-------------|
| `MAGIC_LINK` | Passwordless authentication (default) |
| `COLLECTION_INVITE` | Invitation to view a collection |
| `BOOKING_ACCEPT` | Accept a booking (all thing types) |
| `BOOKING_REJECT` | Reject a booking (all thing types) |

### Business Rules

1. **No passwords in the app** - Regular users authenticate via magic link, not password.

2. **Auth based on email** - Users identify themselves by email address.

3. **Magic link with magic-code** - A 6-character alphanumeric code is sent via email.

4. **Click to login** - Clicking the magic link verifies the RSVP and returns a JWT token.

5. **RSVP codes obfuscate URLs** - Email links use `rsvp_code` instead of exposing real codes like `booking_code` or `reservation_code`.

6. **One-time use** - RSVPs are deleted after being used (verified).

7. **24h expiry** - RSVPs expire after `MAGIC_LINK_EXPIRY_HOURS` (default 24 hours).

8. **RSVP contains all info** - The RSVP stores all information needed to complete the action (`rsvp_target_code`, `rsvp_context`).

9. **RSVP for ALL email communications** - Every email that requires user action must use an RSVP as intermediary.

10. **Never expose real codes** - Email URLs must never contain `booking_code`, `reservation_code`, `thing_code`, etc. Always use `rsvp_code`.

### Methods

- `is_valid()` - Returns True if not expired (within 24h of creation)
- `create_for_booking(action, booking, owner_email)` - Factory method for booking RSVPs

### Email Flow Examples

**Booking Request (all thing types):**
1. Guest requests thing → Creates `BookingPeriod`
2. System creates 2 RSVPs: `BOOKING_ACCEPT` and `BOOKING_REJECT`
3. Email to owner contains links: `/rsvp/{accept_rsvp_code}` and `/rsvp/{reject_rsvp_code}`
4. Owner clicks link → RSVP processed → Booking accepted/rejected → RSVP deleted

**Collection Invite:**
1. Owner invites guest → Creates RSVP with `COLLECTION_INVITE` action
2. Email to guest contains link: `/rsvp/{rsvp_code}`
3. Guest clicks link → RSVP processed → User added to collection → JWT returned → RSVP deleted

### API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth/request-link/` | POST | No | Request magic link |
| `/auth/verify/{rsvp_code}/` | GET | No | Verify magic link, get JWT |
| `/rsvp/{rsvp_code}/` | GET | No | Process any RSVP action |

### Related Models

- **User** - RSVP references user via `user_code`
- **Collection** - RSVP references collection via `collection_code` (for invites)
- **BookingPeriod** - RSVP references booking via `rsvp_target_code`

---

## BookingPeriod

The `BookingPeriod` model is the unified reservation/booking model for all thing types. It handles requests for GIFT, SELL, ORDER, LEND, RENT, and SHARE things.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `booking_code` | CharField(6) | Auto | Primary key, 6-character alphanumeric ID |
| `booking_created` | DateTimeField | Auto | Timestamp when booking was created |
| `thing_code` | CharField(6) | **Yes** | Reference to Thing.thing_code |
| `thing_type` | CharField(12) | No | Type of thing (default: GIFT_THING) |
| `requester_code` | CharField(6) | **Yes** | User code of who made the request |
| `requester_email` | CharField(64) | **Yes** | Email of the requester |
| `owner_code` | CharField(6) | **Yes** | User code of the thing owner |
| `start_date` | DateField | No | Start date (required for LEND/RENT/SHARE) |
| `end_date` | DateField | No | End date (required for LEND/RENT/SHARE) |
| `delivery_date` | DateField | No | Delivery date (required for ORDER_THING) |
| `quantity` | PositiveIntegerField | No | Quantity ordered (required for ORDER_THING) |
| `status` | CharField(8) | No | Status: PENDING, ACCEPTED, REJECTED, EXPIRED |

### Thing Type Constants

```python
DATE_BASED_TYPES = ["LEND_THING", "RENT_THING", "SHARE_THING"]  # Require dates
SINGLE_USE_TYPES = ["GIFT_THING", "SELL_THING"]  # Thing becomes INACTIVE after acceptance
REPEATABLE_TYPES = ["ORDER_THING"]  # Thing stays ACTIVE, can be ordered again
```

### Business Rules

1. **Unified model for all thing types** - BookingPeriod handles all reservation scenarios regardless of thing type.

2. **Date-based bookings (LEND/RENT/SHARE):**
   - `start_date` and `end_date` are required
   - Multiple non-overlapping bookings allowed for same thing
   - Thing stays ACTIVE after acceptance
   - Dates block other bookings while PENDING (72h) or ACCEPTED

3. **Single-use bookings (GIFT/SELL):**
   - `start_date` and `end_date` are null
   - Thing status changes to TAKEN when request is made
   - Thing becomes INACTIVE after acceptance
   - User added to `thing_deal` list

4. **Repeatable bookings (ORDER):**
   - `delivery_date` and `quantity` are required
   - `start_date` and `end_date` are null
   - Thing stays ACTIVE after acceptance
   - Multiple orders allowed (same user can order multiple times)
   - Same user can have multiple pending orders

5. **72h expiry** - PENDING bookings expire after `BOOKING_EXPIRY_HOURS` (default 72h).

6. **Overlap detection** - For date-based types, `has_overlap()` checks for conflicts with PENDING and ACCEPTED bookings.

### Methods

- `is_valid()` - Returns True if not expired (within 72h) and status is PENDING
- `is_date_based()` - Returns True if thing_type requires dates
- `is_single_use()` - Returns True if thing becomes unavailable after acceptance
- `is_repeatable()` - Returns True if thing can be ordered again
- `accept()` - Sets status to ACCEPTED
- `reject()` - Sets status to REJECTED
- `expire()` - Sets status to EXPIRED

### Class Methods

- `has_overlap(thing_code, start_date, end_date, exclude_booking_code)` - Check for date conflicts
- `get_blocked_periods(thing_code)` - Get all PENDING/ACCEPTED bookings for a thing
- `expire_old_pending()` - Batch expire old PENDING bookings

### Related Models

- **Thing** - Booking is for a thing via `thing_code`
- **User** - Requester via `requester_code`, owner via `owner_code`
- **RSVP** - RSVP references booking via `rsvp_target_code`

---

## Thing

The `Thing` model represents an item in a collection. Things can be gifts, items for sale, items for order, rentals, loans, or shared items.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `thing_code` | CharField(6) | Auto | Primary key, 6-character alphanumeric ID |
| `thing_type` | CharField(16) | No | Type of thing (default: GIFT_THING) |
| `thing_owner` | CharField(6) | **Yes** | User code of the owner |
| `thing_created` | DateTimeField | Auto | Timestamp when thing was created |
| `thing_headline` | CharField(64) | **Yes** | Title of the thing |
| `thing_description` | CharField(256) | No | Description of the thing |
| `thing_thumbnail` | CharField(16) | No | Cloudinary image ID for thumbnail |
| `thing_pictures` | JSONField | No | Array of Cloudinary image IDs |
| `thing_status` | CharField(8) | No | Status: ACTIVE, TAKEN, INACTIVE |
| `thing_faq` | JSONField | No | Array of faq_codes for this thing |
| `thing_fee` | DecimalField | No | Price/fee (for SELL/RENT types) |
| `thing_deal` | JSONField | No | Array of user_codes who reserved |
| `thing_available` | BooleanField | No | Visibility flag (default: True) |

### Visibility vs Reservation Status

**IMPORTANT:** `thing_available` and `thing_status` serve different purposes:

| Field | Purpose | Values |
|-------|---------|--------|
| `thing_available` | **Visibility control** | `True` = visible to owner + invites, `False` = visible only to owner |
| `thing_status` | **Reservation state** | `ACTIVE` = can be reserved, `TAKEN` = pending confirmation, `INACTIVE` = no longer available |

**Visibility (`thing_available`):**
- `True`: Thing is visible to the owner AND all users in `collection_invites`
- `False`: Thing is visible ONLY to the owner (hidden from all invites)

**Reservation Status (`thing_status`):**
- `ACTIVE`: Available for new reservation requests
- `TAKEN`: Awaiting owner confirmation (not available for new requests)
- `INACTIVE`: Completed or disabled, no longer available

These fields are **independent**: A thing can be `thing_available=True` but `thing_status=INACTIVE` (visible but not reservable), or `thing_available=False` but `thing_status=ACTIVE` (hidden but technically reservable if someone had the link).

### Thing Types

Things are divided into 3 categories:

| Category | Types | Description |
|----------|-------|-------------|
| **Single-use** | GIFT_THING, SELL_THING | One reservation, then INACTIVE |
| **Repeatable** | ORDER_THING | Multiple reservations allowed |
| **Date-based** | LEND_THING, RENT_THING, SHARE_THING | Calendar-based availability |

### Status Values

| Status | Description |
|--------|-------------|
| `ACTIVE` | Available for reservation |
| `TAKEN` | Reservation pending owner approval |
| `INACTIVE` | No longer available (accepted or disabled) |

### Business Rules - Single-Use Things (GIFT/SELL)

1. **Only invited users can request** - User must be in `collection_invites` to request a thing.

2. **Owner cannot request own thing** - Returns 400 Bad Request if owner tries to request.

3. **Reservation flow:**
   - Thing starts as `ACTIVE`
   - Invited user requests → status changes to `TAKEN`
   - Owner receives email with RSVP accept/reject links
   - **If accepted** → status changes to `INACTIVE`, requester added to `thing_deal`
   - **If rejected** → status changes back to `ACTIVE`
   - Requester receives email notification of decision

4. **No duplicate pending requests** - Same user cannot have multiple pending requests for same thing.

5. **Cannot request TAKEN thing** - Other users cannot request while status is `TAKEN`.

6. **72h expiry** - Pending bookings expire after 72 hours, thing returns to `ACTIVE`.

### Business Rules - Repeatable Things (ORDER)

1. **Required fields** - `delivery_date` (future date) and `quantity` (positive integer) are required.

2. **Multiple requests allowed** - Different users can request the same thing.

3. **Same user can order again** - Unlike single-use, same user can make multiple orders.

4. **Thing stays ACTIVE** - Status doesn't change after acceptance.

5. **Accept/reject flow via RSVP** - Owner receives email with accept/reject links. Requester notified of decision.

6. **Validation:**
   - `delivery_date` must be today or in the future
   - `quantity` must be at least 1

### Business Rules - Date-Based Things (LEND/RENT/SHARE)

1. **Required fields** - `start_date` and `end_date` required in request.

2. **Thing stays ACTIVE always** - Status never changes. Availability is controlled by calendar, not status.

3. **No overlapping bookings** - System returns 409 Conflict if dates overlap with PENDING or ACCEPTED bookings.

4. **Multiple bookings allowed** - Different non-overlapping date ranges can be booked by different users.

5. **Adjacent bookings allowed** - Bookings can be back-to-back (one ends day N, next starts day N+1).

6. **Date validation:**
   - `start_date` must be today or in the future
   - `end_date` must be on or after `start_date`
   - Same-day booking allowed (`start_date == end_date`)

7. **Calendar endpoint** - `/things/{code}/calendar/` returns blocked periods:
   - Owner sees: `booking_code`, `requester_code`, `start_date`, `end_date`, `status`
   - Guest sees: `start_date`, `end_date`, `status` (no requester info)
   - Only PENDING and ACCEPTED bookings shown (not REJECTED/EXPIRED)

8. **Email flow:**
   - Request created → Owner receives email with dates + RSVP accept/reject links
   - Accept → Requester receives confirmation email with dates
   - Reject → Requester receives rejection email with dates
   - Dates become available again after reject (REJECTED bookings ignored in overlap check)

9. **72h expiry** - PENDING bookings expire and dates become available again.

### Methods

- `is_owner(user_code)` - Check if user is the owner
- `can_view(user_code)` - Check if user can view (owner or invited)
- `reserve(user_code)` - Add user to `thing_deal`, set `thing_available=False`
- `release(user_code)` - Remove user from `thing_deal`
- `add_faq(faq_code)` - Add a FAQ to this thing
- `remove_faq(faq_code)` - Remove a FAQ from this thing

### Related Models

- **User** - Owner via `thing_owner`
- **Collection** - Thing belongs to collections via `collection_things` array
- **FAQ** - FAQs about this thing via `thing_faq` array
- **BookingPeriod** - Reservations via `thing_code`

### API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/things/` | Yes | List own things |
| POST | `/things/` | Yes | Create thing |
| GET | `/things/{code}/` | Yes | View thing (owner or invited) |
| PUT | `/things/{code}/` | Yes | Update thing (owner only) |
| DELETE | `/things/{code}/` | Yes | Delete thing (owner only) |
| POST | `/things/{code}/request/` | Yes | Request reservation (invited only) |
| GET | `/things/{code}/calendar/` | Yes | View booking calendar (LEND/RENT/SHARE) |
| GET | `/invited-things/` | Yes | List things from invited collections |

---

## Security Considerations

### Authentication & Authorization

1. **Invite-only registration** - Users cannot self-register. They must be invited to a collection first (which creates their account).

2. **Magic link authentication** - Passwordless via email. RSVPs expire after 24 hours and are one-time use.

3. **JWT tokens** - Access tokens expire after 1 hour. Refresh tokens expire after 7 days. Tokens are rotated on refresh.

4. **IDOR protection** - Users can only view profiles of users connected via collections (owner or invitee relationship).

### Input Validation

1. **Image IDs** - Only alphanumeric characters, underscores, and hyphens allowed. Prevents path traversal and injection.

2. **Headlines** - HTML tags rejected to prevent XSS. Uses bleach for sanitization.

3. **Quantities** - Order quantities capped at 99 to prevent abuse.

4. **Dates** - Start dates must be today or future. End dates must be >= start dates.

### Rate Limiting

- `/auth/request-link/` - 5 requests per minute per IP
- `/auth/verify/{code}/` - 10 requests per minute per IP

### Secure Code Practices

1. **ID generation** - Uses `secrets.choice()` for cryptographically secure random IDs.

2. **SECRET_KEY** - Required from environment variable, not hardcoded.

3. **RSVP obfuscation** - Real codes (booking_code, thing_code) never exposed in URLs. Always use RSVP codes as intermediaries.

4. **Security logging** - Auth events logged with IP addresses for audit trail.

---
