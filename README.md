# OIUEEI Project Context

## What is OIUEEI?

A web application for sharing belongings with friends. Users can create collections (wishlists, gift lists, items for sale) and share them with friends who can then reserve items or ask questions.

## Tech Stack

- **Backend**: Django REST Framework (this repo)
- **Frontend**: React (same repo, not yet implemented)
- **UI design**: oiueeiDS (not yet implemented)
- **Auth**: Magic link authentication (passwordless for users, password enabled for admin access)
- **Database**: SQLite (dev), PostgreSQL (prod)

## Data Models

| Model | Purpose |
|-------|---------|
| **User** | Users with magic link auth. Custom model with `user_code` as PK (6-char alphanumeric) |
| **Collection** | Lists of things owned by a user, can be shared via invites |
| **Thing** | Items in collections. Types: GIFT_ARTICLE, SELL_ARTICLE, ORDER_ARTICLE |
| **FAQ** | Questions/answers about things |
| **Theeeme** | Colour palettes (10 colours) for customising collections |
| **RSVP** | Magic link tokens (one-time use, 24h expiry) |
| **ReservationRequest** | Reservation requests pending owner approval (72h expiry) |

## Key Relationships

- Collection → User (owner via `collection_owner`)
- Collection → Theeeme (FK with PROTECT)
- Collection has `collection_invites` (list of user_codes who can view)
- Collection has `collection_articles` (list of thing_codes)
- Thing → User (owner via `thing_owner`)
- FAQ → Thing (via `faq_thing`)
- ReservationRequest → Thing (via `thing_code`)
- ReservationRequest → User (requester via `requester_code`, owner via `owner_code`)

## API Endpoints

### Auth
| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/v1/auth/request-link/` | Request magic link |
| GET | `/api/v1/auth/verify/{rsvp_code}/` | Verify magic link, get JWT |
| GET | `/api/v1/auth/me/` | Get authenticated user |
| POST | `/api/v1/auth/logout/` | Log out |

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
| POST | `/api/v1/things/{code}/reserve/` | Reserve without approval (guest only) |
| POST | `/api/v1/things/{code}/release/` | Release reservation |
| POST | `/api/v1/things/{code}/request/` | Request reservation with approval (guest only) |
| GET | `/api/v1/invited-things/` | List things from invited collections (guest only) |

### Reservations
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/v1/reservations/{code}/accept/` | Accept reservation (via email) |
| GET | `/api/v1/reservations/{code}/reject/` | Reject reservation (via email) |

### FAQ
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/v1/things/{thing_code}/faq/` | List FAQs for a thing |
| POST | `/api/v1/things/{thing_code}/faq/` | Create question |
| GET | `/api/v1/faq/{faq_code}/` | View FAQ |
| POST | `/api/v1/faq/{faq_code}/answer/` | Answer FAQ (owner only) |

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

- Default Theeeme: "Barcelona" (code: BRCLON) - greyscale palette

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
