"""The `CREATOR_POLICY` gate, over HTTP, at every door that opens onto it.

Two things are being protected here, and they pull in opposite directions:

**The standalone must stay ungated.** With the default policy every request in
this file has to behave exactly as it did before the setting existed. The
existing creation suites are the real proof of that — they were not touched —
and the first class restates it in one place so the intent is legible.

**A narrowed deployment must actually be narrowed, at every door.** The design
note named two call sites; there are five, because a verb and a mode can also
be reached by *editing* an existing row and by the bulk-CSV import. A gate on
creation alone would be walked around with one PATCH.

Grandfathering is deliberate throughout: the gate is on bringing that state
into existence, never on living in it. A deployment that narrows next year must
not freeze the collections and things people already own — an owner who could
no longer fix a typo on their own lending collection would be the product
punishing them for a policy change they had no part in.
"""

import pytest
from rest_framework import status

from core.models import Collection, Thing
from core.tests.sample_creator_policy import REQUEST_URL

RESTRICTED = "core.tests.sample_creator_policy.RestrictedCreatorPolicy"
BULK_URL = "/api/v1/collections/{code}/things/bulk/"


@pytest.mark.django_db
class TestTheStandaloneDoorIsOpen:
    """Default policy: everything the product offers, offered to everyone."""

    def test_a_community_collection_is_created_without_asking_anyone(self, authenticated_client):
        response = authenticated_client.post(
            "/api/v1/collections/",
            {"headline": "Mercadillo", "mode": "COMMUNITY"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.parametrize("thing_type", Thing.Type.values)
    def test_every_verb_is_available_to_a_plain_account(self, authenticated_client, thing_type):
        response = authenticated_client.post(
            "/api/v1/things/",
            {"type": thing_type, "headline": "A thing", "thumbnail": "img/x"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestANarrowedDeploymentRefusesAtCreation:
    @pytest.fixture(autouse=True)
    def _narrowed_deployment(self, settings):
        """Every test in this class runs against the restricted policy."""
        settings.CREATOR_POLICY = RESTRICTED

    def test_a_withheld_mode_is_refused_with_403_and_creates_nothing(self, authenticated_client):
        response = authenticated_client.post(
            "/api/v1/collections/",
            {"headline": "Mercadillo", "mode": "COMMUNITY"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert REQUEST_URL in str(response.data)
        assert not Collection.objects.filter(headline="Mercadillo").exists()

    def test_what_the_policy_allows_still_works(self, authenticated_client):
        response = authenticated_client.post(
            "/api/v1/collections/", {"headline": "My shelf", "mode": "PROPRIETARY"}, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_a_body_that_names_no_mode_is_judged_on_the_default_it_would_get(
        self, authenticated_client
    ):
        """PROPRIETARY is the model default, so omitting the field is not a bypass.

        With this policy the default is allowed and the request succeeds — what
        the test pins is that the *check ran on it*, which is what a policy
        withholding every mode depends on.
        """
        response = authenticated_client.post(
            "/api/v1/collections/", {"headline": "Unstated mode"}, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert Collection.objects.get(headline="Unstated mode").mode == Collection.Mode.PROPRIETARY

    def test_a_withheld_verb_is_refused_and_creates_nothing(self, authenticated_client):
        response = authenticated_client.post(
            "/api/v1/things/",
            {"type": "LEND_THING", "headline": "Ladder", "thumbnail": "img/x"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "lend thing" in str(response.data)
        assert not Thing.objects.filter(headline="Ladder").exists()

    def test_an_allowed_verb_still_works(self, authenticated_client):
        response = authenticated_client.post(
            "/api/v1/things/",
            {"type": "GIFT_THING", "headline": "Books", "thumbnail": "img/x"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_the_verb_is_judged_before_the_collection_is_looked_up(self, authenticated_client):
        """A refusal must not depend on the collection, nor reveal anything about it.

        Named collection does not exist. Answered 403 on the verb rather than
        404 on the collection: the person is not allowed to lend anywhere, so
        which collection they aimed at is not part of the answer — and probing
        this endpoint must not become a way to learn which codes exist.
        """
        response = authenticated_client.post(
            "/api/v1/things/",
            {
                "type": "LEND_THING",
                "headline": "Ladder",
                "thumbnail": "img/x",
                "collection_code": "NOPE99",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestTheGateCannotBeWalkedAroundByEditing:
    @pytest.fixture(autouse=True)
    def _narrowed_deployment(self, settings):
        """Every test in this class runs against the restricted policy."""
        settings.CREATOR_POLICY = RESTRICTED

    def test_switching_a_collection_into_a_withheld_mode_is_refused(
        self, authenticated_client, collection
    ):
        response = authenticated_client.patch(
            f"/api/v1/collections/{collection.code}/", {"mode": "COMMUNITY"}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        collection.refresh_from_db()
        assert collection.mode == Collection.Mode.PROPRIETARY

    def test_moving_a_thing_to_a_withheld_verb_is_refused(self, authenticated_client, thing):
        response = authenticated_client.patch(
            f"/api/v1/things/{thing.code}/",
            {"type": "RENT_THING", "thumbnail": "img/x"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        thing.refresh_from_db()
        assert thing.type == Thing.Type.GIFT_THING

    def test_a_collection_already_in_that_mode_stays_editable(
        self, authenticated_client, collection
    ):
        """Grandfathering: narrowing a deployment must not freeze what exists.

        The collection predates the policy (or the policy changed under it).
        Its owner edits the headline and does not touch the mode — the mode
        rides along in the payload, as a PUT from the edit form would send it.
        """
        collection.mode = Collection.Mode.COMMUNITY
        collection.save(update_fields=["mode"])

        response = authenticated_client.patch(
            f"/api/v1/collections/{collection.code}/",
            {"headline": "Renamed", "mode": "COMMUNITY"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        collection.refresh_from_db()
        assert collection.headline == "Renamed"
        assert collection.mode == Collection.Mode.COMMUNITY

    def test_a_thing_already_under_that_verb_stays_editable(self, authenticated_client, thing):
        thing.type = Thing.Type.LEND_THING
        thing.save(update_fields=["type"])

        response = authenticated_client.patch(
            f"/api/v1/things/{thing.code}/",
            {"headline": "Renamed", "type": "LEND_THING", "thumbnail": "img/x"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        thing.refresh_from_db()
        assert thing.headline == "Renamed"


@pytest.mark.django_db
class TestContributingToACommunityGroupIsNotInitiating:
    """The gate is on *initiating* — opening a group, offering a verb of your
    own. It is not on a member adding a thing to a COMMUNITY collection they
    were invited to, of a type its owner explicitly allow-listed.

    That owner is the vetted party: a deployment narrow enough to hold COMMUNITY
    creation behind a request vetted *them*, and putting the verb in
    `allowed_thing_types` is them opening their group to it. The member is
    acting under that, not around it.
    """

    @pytest.fixture(autouse=True)
    def _narrowed_deployment(self, settings):
        settings.CREATOR_POLICY = RESTRICTED

    @pytest.fixture
    def lending_group(self, user, user2):
        """A COMMUNITY collection `user` owns and opened to loans, `user2` an
        invited member of it. `user2` has asked nobody for anything."""
        coll = Collection.objects.create(
            owner=user,
            headline="Tool library",
            mode=Collection.Mode.COMMUNITY,
            allowed_thing_types=["LEND_THING"],
        )
        coll.invites.add(user2)
        return coll

    def test_an_invited_member_may_add_an_allow_listed_verb(
        self, authenticated_client2, lending_group
    ):
        response = authenticated_client2.post(
            "/api/v1/things/",
            {
                "type": "LEND_THING",
                "headline": "A ladder",
                "thumbnail": "img/x",
                "collection_code": lending_group.code,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert lending_group.things.filter(headline="A ladder").exists()

    def test_the_bulk_import_follows_the_same_rule(self, authenticated_client2, lending_group):
        response = authenticated_client2.post(
            BULK_URL.format(code=lending_group.code),
            {"rows": [{"type": "LEND_THING", "headline": "Drill"}]},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert lending_group.things.filter(headline="Drill").exists()

    def test_a_member_may_retype_their_contribution_into_an_allow_listed_verb(
        self, authenticated_client2, lending_group, user2
    ):
        thing = Thing.objects.create(owner=user2, headline="Was a gift", type="GIFT_THING")
        lending_group.things.add(thing)

        response = authenticated_client2.patch(
            f"/api/v1/things/{thing.code}/",
            {"type": "LEND_THING", "thumbnail": "img/x"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        thing.refresh_from_db()
        assert thing.type == Thing.Type.LEND_THING

    def test_a_verb_the_owner_did_not_allow_list_is_still_refused(
        self, authenticated_client2, lending_group
    ):
        """RENT is not in this collection's list, so the member has no standing
        to bring one in — the deployment policy answers, request URL and all."""
        response = authenticated_client2.post(
            "/api/v1/things/",
            {
                "type": "RENT_THING",
                "headline": "A drill",
                "thumbnail": "img/x",
                "collection_code": lending_group.code,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert REQUEST_URL in str(response.data)

    def test_an_empty_allowlist_is_not_a_blanket_yes(self, authenticated_client2, user, user2):
        """A COMMUNITY collection with no type restriction: the owner made no
        choice, so an un-vetted member stays on the deployment's open half."""
        coll = Collection.objects.create(
            owner=user, headline="Open group", mode=Collection.Mode.COMMUNITY
        )
        coll.invites.add(user2)

        response = authenticated_client2.post(
            "/api/v1/things/",
            {
                "type": "LEND_THING",
                "headline": "A ladder",
                "thumbnail": "img/x",
                "collection_code": coll.code,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not Thing.objects.filter(headline="A ladder").exists()

    def test_a_non_member_gets_nothing_from_the_exception(self, authenticated_client2, user, user2):
        """Not invited: the group is not theirs to contribute to. The refusal
        also does not confirm the collection exists — same 403 as a bad code."""
        coll = Collection.objects.create(
            owner=user,
            headline="Tool library",
            mode=Collection.Mode.COMMUNITY,
            allowed_thing_types=["LEND_THING"],
        )

        response = authenticated_client2.post(
            "/api/v1/things/",
            {
                "type": "LEND_THING",
                "headline": "A ladder",
                "thumbnail": "img/x",
                "collection_code": coll.code,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not Thing.objects.filter(headline="A ladder").exists()

    def test_the_owner_is_still_initiating_in_their_own_group(self, authenticated_client, user):
        """The owner adding a loan to their own COMMUNITY collection is offering
        a verb of their own — the exception is for the members they invited."""
        coll = Collection.objects.create(
            owner=user,
            headline="Tool library",
            mode=Collection.Mode.COMMUNITY,
            allowed_thing_types=["LEND_THING"],
        )

        response = authenticated_client.post(
            "/api/v1/things/",
            {
                "type": "LEND_THING",
                "headline": "A ladder",
                "thumbnail": "img/x",
                "collection_code": coll.code,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestTheBulkImportObeysTheSamePolicy:
    """The CSV path is the third way to create a thing, and the easiest to forget."""

    @pytest.fixture(autouse=True)
    def _narrowed_deployment(self, settings):
        """Every test in this class runs against the restricted policy."""
        settings.CREATOR_POLICY = RESTRICTED

    def test_a_row_with_a_withheld_verb_fails_the_whole_batch(
        self, authenticated_client, collection
    ):
        response = authenticated_client.post(
            BULK_URL.format(code=collection.code),
            {
                "rows": [
                    {"type": "GIFT_THING", "headline": "Fine"},
                    {"type": "RENT_THING", "headline": "Refused"},
                ]
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # All-or-nothing: the good row is not created either.
        assert not Thing.objects.filter(headline="Fine").exists()

    def test_the_refusal_names_the_row_so_the_importer_can_fix_it(
        self, authenticated_client, collection
    ):
        """Reported per row, not as a 403 for the batch.

        This endpoint's contract is that one response names every bad row. An
        importer told only "forbidden" about a 100-row CSV has to find the bad
        rows by bisection.
        """
        response = authenticated_client.post(
            BULK_URL.format(code=collection.code),
            {
                "rows": [
                    {"type": "GIFT_THING", "headline": "Fine"},
                    {"type": "RENT_THING", "headline": "Refused"},
                ]
            },
            format="json",
        )

        assert response.data["errors"] == [
            {
                "row": 1,
                "errors": {
                    "type": [
                        f"This deployment does not allow you to offer a "
                        f"rent thing. Request access at {REQUEST_URL}."
                    ]
                },
            }
        ]

    def test_a_batch_of_allowed_verbs_imports_as_before(self, authenticated_client, collection):
        response = authenticated_client.post(
            BULK_URL.format(code=collection.code),
            {"rows": [{"type": "GIFT_THING", "headline": "Fine"}]},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert Thing.objects.filter(headline="Fine").exists()


@pytest.mark.django_db
class TestWhatTheFrontendIsTold:
    """`GET /auth/me/` carries the capabilities the SPA builds its forms from.

    The endpoint the app already calls on every load, so no extra round-trip —
    and, more importantly, the same `capabilities()` the create endpoints refuse
    with. The tests that matter here are the ones that cross both: whatever this
    endpoint advertises has to be exactly what the create endpoints accept, or
    the user is offered a control that 403s when pressed.
    """

    def test_the_standalone_advertises_the_whole_product(self, authenticated_client):
        response = authenticated_client.get("/api/v1/auth/me/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["capabilities"] == {
            "collection_modes": list(Collection.Mode.values),
            "thing_types": list(Thing.Type.values),
            "request_url": None,
        }

    def test_the_user_payload_is_unchanged_beside_it(self, authenticated_client, user):
        """Additive: existing consumers of this endpoint keep working."""
        response = authenticated_client.get("/api/v1/auth/me/")

        assert response.data["code"] == user.code
        assert response.data["email"] == user.email

    def test_a_narrowed_deployment_says_so_and_says_where_to_ask(
        self, authenticated_client, settings
    ):
        settings.CREATOR_POLICY = RESTRICTED

        response = authenticated_client.get("/api/v1/auth/me/")

        assert response.data["capabilities"] == {
            "collection_modes": ["PROPRIETARY"],
            "thing_types": ["GIFT_THING", "SELL_THING"],
            "request_url": REQUEST_URL,
        }

    @pytest.mark.parametrize("policy", [None, RESTRICTED])
    def test_every_advertised_verb_is_actually_accepted(
        self, authenticated_client, settings, policy
    ):
        """The promise, checked against the door — under both policies.

        A capability list the create endpoint would refuse is worse than no list
        at all: the UI enables the control and the 403 arrives after the user
        has filled the form in.
        """
        if policy:
            settings.CREATOR_POLICY = policy

        advertised = authenticated_client.get("/api/v1/auth/me/").data["capabilities"]

        for index, thing_type in enumerate(advertised["thing_types"]):
            response = authenticated_client.post(
                "/api/v1/things/",
                {"type": thing_type, "headline": f"Thing {index}", "thumbnail": "img/x"},
                format="json",
            )
            assert response.status_code == status.HTTP_201_CREATED, thing_type

    @pytest.mark.parametrize("policy", [None, RESTRICTED])
    def test_nothing_left_off_the_list_slips_through(self, authenticated_client, settings, policy):
        """And the converse — the list is not merely a subset of what is allowed."""
        if policy:
            settings.CREATOR_POLICY = policy

        advertised = authenticated_client.get("/api/v1/auth/me/").data["capabilities"]
        withheld = set(Thing.Type.values) - set(advertised["thing_types"])

        for thing_type in withheld:
            response = authenticated_client.post(
                "/api/v1/things/",
                {"type": thing_type, "headline": "Withheld", "thumbnail": "img/x"},
                format="json",
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN, thing_type
