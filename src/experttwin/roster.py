from dataclasses import dataclass


@dataclass(frozen=True)
class RosterProfile:
    name: str
    role: str
    war_room_role: str = "Participant"


AUTHORIZED_ROSTER = (
    RosterProfile(
        "Hrishikesh Mohile",
        "Principal Software Engineering Manager",
        "Engineering Manager / Moderator / Final Decision Owner",
    ),
    RosterProfile("Amrita Shanbhag", "Senior Software Engineer"),
    RosterProfile("Devarakonda Sathish", "Data Engineer"),
    RosterProfile("Kumar Ritesh", "Senior Software Engineer"),
    RosterProfile("Manish Patil", "Senior Software Engineer"),
    RosterProfile("Nishikant Lambat", "Software Engineer"),
    RosterProfile("Rajendra Kalepu", "Senior Data Engineer"),
    RosterProfile("Satyajit Sahu", "Software Engineering"),
    RosterProfile("Siya Sharma", "Software Engineer"),
    RosterProfile("Tulika", "Software Engineer II"),
    RosterProfile("Vishwas Srivastava", "Principal Software Engineer"),
)
AUTHORIZED_NAMES = tuple(profile.name for profile in AUTHORIZED_ROSTER)
MANAGER_NAME = AUTHORIZED_ROSTER[0].name
