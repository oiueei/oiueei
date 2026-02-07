## What is OIUEEI?

An open-source web application for people to share their belongings with friends and others around. Users can create collections (wishlists, gift lists, items for sale) and share them with friends who can then reserve items or ask questions.

## Tech Stack

- **Backend**: Django REST Framework (this repo)
- **Frontend**: React (same repo, not yet implemented)
- **UI design**: oiueeiDS (not yet implemented)
- **Auth**: Magic link authentication (passwordless for users, password enabled for admin access)
- **Database**: SQLite (dev), PostgreSQL (prod)
- **Worker**: Cron Job / Heroku Scheduler (not yet implemented) - for booking expiration cleanup

## Data Models

| Model | Purpose |
|-------|---------|
| **User** | Users with magic link auth. Custom model with `user_code` as PK (6-char alphanumeric) |
| **Collection** | Lists of things owned by a user, can be shared via invites |
| **Thing** | Items in collections. Types: GIFT_THING, SELL_THING, ORDER_THING, RENT_THING, LEND_THING, SHARE_THING. `thing_available` controls visibility (True=visible to invites, False=owner only). `thing_status` controls reservation state (ACTIVE/TAKEN/INACTIVE) |
| **FAQ** | Questions/answers about things |
| **Theeeme** | Colour palettes (6 colours) for customising collections |
| **RSVP** | Magic link tokens (one-time use, 24h expiry) for auth and email actions |
| **BookingPeriod** | Unified booking/reservation model for all thing types (72h expiry). Handles: single-use (GIFT/SELL), repeatable orders (ORDER with delivery_date+quantity), and date-based calendar (LEND/RENT/SHARE with start_date+end_date) |

## Key Relationships

- Collection → User (owner via `collection_owner`)
- Collection → Theeeme (FK with PROTECT)
- Collection has `collection_invites` (list of user_codes who can view)
- Collection has `collection_things` (list of thing_codes)
- Thing → User (owner via `thing_owner`)
- FAQ → Thing (via `faq_thing`)
- BookingPeriod → Thing (via `thing_code`) - for all thing types
- BookingPeriod → User (requester via `requester_code`, owner via `owner_code`)

## API Endpoints

### Auth & RSVP Actions
| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/v1/auth/request-link/` | Request magic link |
| GET | `/api/v1/auth/verify/{rsvp_code}/` | Verify magic link or process any RSVP action |
| GET | `/api/v1/auth/me/` | Get authenticated user |
| POST | `/api/v1/auth/logout/` | Log out |
| GET | `/api/v1/rsvp/{rsvp_code}/` | Process any RSVP action (unified endpoint) |

### Users
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/v1/users/{user_code}/` | View profile |
| PUT | `/api/v1/users/{user_code}/` | Update own profile (owner only) |

### Collections
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/v1/collections/` | List own collections |
| POST | `/api/v1/collections/` | Create collection |
| GET | `/api/v1/collections/{code}/` | View collection |
| POST | `/api/v1/collections/{code}/` | Add thing to collection (owner only) |
| PUT | `/api/v1/collections/{code}/` | Update collection (owner only) |
| DELETE | `/api/v1/collections/{code}/` | Delete collection (owner only) |
| POST | `/api/v1/collections/{code}/invite/` | Invite user (owner only) |
| DELETE | `/api/v1/collections/{code}/invite/` | Remove invitee (owner only) |
| GET | `/api/v1/invited-collections/` | List collections where invited (guest only) |

### Things
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/v1/things/` | List own things |
| POST | `/api/v1/things/` | Create thing |
| GET | `/api/v1/things/{code}/` | View thing |
| PUT | `/api/v1/things/{code}/` | Update thing (owner only) |
| DELETE | `/api/v1/things/{code}/` | Delete thing (owner only) |
| POST | `/api/v1/things/{code}/request/` | Request reservation (guest only). Creates BookingPeriod, owner approves via RSVP. For LEND/RENT/SHARE requires `start_date` and `end_date`. For ORDER requires `delivery_date` and `quantity` |
| GET | `/api/v1/things/{code}/calendar/` | View booking calendar (LEND/RENT/SHARE). Owner sees full details, guest sees only blocked dates |
| GET | `/api/v1/invited-things/` | List things from invited collections (guest only) |

### Bookings (LEND/RENT/SHARE)
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/v1/my-bookings/` | List my booking requests |
| GET | `/api/v1/owner-bookings/` | List bookings for my things (owner only) |

**Note:** Reservation and booking accept/reject actions are handled via RSVP links sent by email. The owner receives a unique RSVP code for each action, accessed via `/api/v1/rsvp/{rsvp_code}/`. This prevents exposing real reservation or booking codes in URLs.

### FAQ
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/v1/things/{thing_code}/faq/` | List FAQs for a thing |
| POST | `/api/v1/things/{thing_code}/faq/` | Create question (invited users only, not owner) |
| GET | `/api/v1/faq/{faq_code}/` | View FAQ |
| POST | `/api/v1/faq/{faq_code}/answer/` | Answer FAQ (owner only) |
| POST | `/api/v1/faq/{faq_code}/hide/` | Hide FAQ (owner only) |
| POST | `/api/v1/faq/{faq_code}/show/` | Show FAQ (owner only) |

### Admin
- `/admin/` - Django Admin (requires password)

## Development Commands

```bash
# Run server
python manage.py runserver

# Run tests
pytest -v --cov=core --cov-fail-under=80

# Linting
black .
flake8 .

# Migrations
python manage.py makemigrations core
python manage.py migrate

# Create admin user
python manage.py createsuperuser
```

## Default Data

- Default Theeeme: "BAR_CEL_ONA"

## Important Notes

- **Superadmin must be created manually** after running migrations. Since users authenticate via magic link, you need to set the password manually via Django shell:
  ```bash
  python manage.py shell
  ```
  ```python
  from core.models import User

  # See all users
  User.objects.all()

  # Get your user (use the email you created)
  user = User.objects.get(user_email="your@email.com")

  # Set password and admin permissions
  user.set_password("your_password")
  user.is_staff = True
  user.is_superuser = True
  user.save()
  ```
  This is required to access `/admin/`. Regular users authenticate via magic link and don't need passwords.

- **Booking expiration cleanup** - PENDING bookings expire after 72 hours but require a scheduled job to mark them as EXPIRED. Call `BookingPeriod.expire_old_pending()` via cron/Heroku Scheduler. Example management command:
  ```python
  # core/management/commands/expire_bookings.py
  from django.core.management.base import BaseCommand
  from core.models.booking import BookingPeriod

  class Command(BaseCommand):
      def handle(self, *args, **options):
          count = BookingPeriod.expire_old_pending()
          self.stdout.write(f"Expired {count} bookings")
  ```
