import pytest

import enum
from dataclasses import dataclass
from graphotype import Object, Interface, make_schema
from typing import Optional, List

class Episode(enum.Enum):
    NEWHOPE = 4
    EMPIRE = 5
    JEDI = 6

@dataclass
class Character(Interface):
    """A character in the Star Wars trilogy."""
    id: str
    name: Optional[str]
    _friends: List[str]
    def friends(self) -> Optional[List[Optional['Character']]]:
        return [humanData.get(id) or droidData.get(id) for id in self._friends]
    appearsIn: Optional[List[Optional[Episode]]]

@dataclass
class Human(Object, Character):
    homePlanet: Optional[str]

@dataclass
class Droid(Object, Character):
    primaryFunction: Optional[str]

class Query(Object):
    def hero(self, episode: Optional[Episode] = None) -> Optional[Character]:
        if episode == Episode.EMPIRE:
            return luke
        return artoo

    def human(self, id: str) -> Optional[Human]:
        return humanData.get(id)

    def droid(self, id: str) -> Optional[Droid]:
        return droidData.get(id)


luke = Human(
    id="1000",
    name="Luke Skywalker",
    _friends=["1002", "1003", "2000", "2001"],
    appearsIn=[4, 5, 6],
    homePlanet="Tatooine",
)

vader = Human(
    id="1001",
    name="Darth Vader",
    _friends=["1004"],
    appearsIn=[4, 5, 6],
    homePlanet="Tatooine",
)

han = Human(
    id="1002",
    name="Han Solo",
    _friends=["1000", "1003", "2001"],
    appearsIn=[4, 5, 6],
    homePlanet=None,
)

leia = Human(
    id="1003",
    name="Leia Organa",
    _friends=["1000", "1002", "2000", "2001"],
    appearsIn=[4, 5, 6],
    homePlanet="Alderaan",
)

tarkin = Human(
    id="1004", name="Wilhuff Tarkin", _friends=["1001"], appearsIn=[4], homePlanet=None
)

humanData = {"1000": luke, "1001": vader, "1002": han, "1003": leia, "1004": tarkin}

threepio = Droid(
    id="2000",
    name="C-3PO",
    _friends=["1000", "1002", "1003", "2001"],
    appearsIn=[4, 5, 6],
    primaryFunction="Protocol",
)

artoo = Droid(
    id="2001",
    name="R2-D2",
    _friends=["1000", "1002", "1003"],
    appearsIn=[4, 5, 6],
    primaryFunction="Astromech",
)

droidData = {"2000": threepio, "2001": artoo}


@pytest.fixture(scope='session')
def schema():
    yield make_schema(query=Query)
