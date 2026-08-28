"""
Matchmaker servisi testleri.
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from events.models import Event
from jams.models import GameJam, JamApplication, SuggestedTeam
from jams.services import reset_matchmaker, run_matchmaker


class MatchmakerTests(TestCase):
    def setUp(self):
        simdi = timezone.now()
        self.event = Event.objects.create(
            title="Eşleştirme Jam", slug="eslestirme-jam", description="x",
            event_type=Event.EventType.GAME_JAM, status=Event.Status.PUBLISHED,
            start_date=simdi, end_date=simdi + timedelta(days=2), location="Kampüs",
        )
        self.jam = GameJam.objects.create(
            event=self.event, application_deadline=simdi, max_team_size=4,
        )

    def _basvuru(self, ad, rol, team_status=JamApplication.TeamStatus.LOOKING,
                 status=JamApplication.ApplicationStatus.PENDING):
        return JamApplication.objects.create(
            jam=self.jam, full_name=ad, email=f"{ad.lower()}@example.com",
            jam_role=rol, team_status=team_status, status=status,
            kvkk_accepted=True,
        )

    def test_groups_different_roles_into_one_team(self):
        self._basvuru("Ali", "Developer")
        self._basvuru("Veli", "2D Artist")
        self._basvuru("Ayse", "Game Designer")

        takimlar = run_matchmaker(self.jam)

        self.assertEqual(len(takimlar), 1)
        self.assertEqual(takimlar[0].members.count(), 3)

    def test_respects_max_team_size(self):
        for i, rol in enumerate(["Developer", "2D Artist", "3D Artist", "Game Designer", "Sound Designer"]):
            self._basvuru(f"Kisi{i}", rol)

        takimlar = run_matchmaker(self.jam)

        self.assertEqual(takimlar[0].members.count(), 4)   # max_team_size=4

    def test_rejected_applicants_are_excluded(self):
        self._basvuru("Ali", "Developer")
        self._basvuru("Veli", "2D Artist")
        self._basvuru("Red", "3D Artist", status=JamApplication.ApplicationStatus.REJECTED)

        takimlar = run_matchmaker(self.jam)

        isimler = {u.full_name for u in takimlar[0].members.all()}
        self.assertNotIn("Red", isimler)

    def test_only_looking_applicants_are_matched(self):
        self._basvuru("Ali", "Developer")
        self._basvuru("Veli", "2D Artist")
        self._basvuru("Solo", "3D Artist", team_status=JamApplication.TeamStatus.SOLO)
        self._basvuru("Ekipli", "Sound Designer", team_status=JamApplication.TeamStatus.HAS_TEAM)

        takimlar = run_matchmaker(self.jam)

        isimler = {u.full_name for u in takimlar[0].members.all()}
        self.assertEqual(isimler, {"Ali", "Veli"})

    def test_single_leftover_is_not_teamed_alone(self):
        self._basvuru("Yalniz", "Developer")

        takimlar = run_matchmaker(self.jam)

        self.assertEqual(takimlar, [])
        self.assertEqual(SuggestedTeam.objects.filter(jam=self.jam).count(), 0)

    def test_team_names_are_sequential(self):
        """REGRESYON: eski kod 1, 3, 5... diye numaralandırıyordu."""
        for i, rol in enumerate(["Developer", "2D Artist", "3D Artist", "Game Designer"]):
            self._basvuru(f"A{i}", rol)
        for i, rol in enumerate(["Developer", "2D Artist", "3D Artist", "Game Designer"]):
            self._basvuru(f"B{i}", rol)

        takimlar = run_matchmaker(self.jam)

        self.assertEqual([t.name for t in takimlar], ["Takım 1", "Takım 2"])

    def test_already_assigned_applicants_are_skipped(self):
        self._basvuru("Ali", "Developer")
        self._basvuru("Veli", "2D Artist")
        run_matchmaker(self.jam)

        self._basvuru("Yeni1", "3D Artist")
        self._basvuru("Yeni2", "Sound Designer")
        ikinci = run_matchmaker(self.jam)

        self.assertEqual(len(ikinci), 1)
        self.assertEqual(ikinci[0].name, "Takım 2")
        self.assertEqual({u.full_name for u in ikinci[0].members.all()}, {"Yeni1", "Yeni2"})

    def test_reset_clears_teams_and_unlinks_members(self):
        self._basvuru("Ali", "Developer")
        self._basvuru("Veli", "2D Artist")
        run_matchmaker(self.jam)

        silinen = reset_matchmaker(self.jam)

        self.assertEqual(silinen, 1)
        self.assertEqual(SuggestedTeam.objects.filter(jam=self.jam).count(), 0)
        self.assertEqual(
            JamApplication.objects.filter(jam=self.jam, suggested_team__isnull=False).count(), 0
        )

    def test_reset_does_not_delete_applications(self):
        self._basvuru("Ali", "Developer")
        self._basvuru("Veli", "2D Artist")
        run_matchmaker(self.jam)

        reset_matchmaker(self.jam)

        self.assertEqual(JamApplication.objects.filter(jam=self.jam).count(), 2)
