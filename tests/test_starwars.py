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

from graphql import graphql, format_error

StarWarsSchema = make_schema(query=Query)


def test_hero_name_query():
    query = """
        query HeroNameQuery {
          hero {
            name
          }
        }
    """
    expected = {"hero": {"name": "R2-D2"}}
    result = graphql(StarWarsSchema, query)
    assert not result.errors
    assert result.data == expected


def test_hero_name_and_friends_query():
    query = """
        query HeroNameAndFriendsQuery {
          hero {
            id
            name
            friends {
              name
            }
          }
        }
    """
    expected = {
        "hero": {
            "id": "2001",
            "name": "R2-D2",
            "friends": [
                {"name": "Luke Skywalker"},
                {"name": "Han Solo"},
                {"name": "Leia Organa"},
            ],
        }
    }
    result = graphql(StarWarsSchema, query)
    assert not result.errors
    assert result.data == expected


def test_nested_query():
    query = """
        query NestedQuery {
          hero {
            name
            friends {
              name
              appearsIn
              friends {
                name
              }
            }
          }
        }
    """
    expected = {
        "hero": {
            "name": "R2-D2",
            "friends": [
                {
                    "name": "Luke Skywalker",
                    "appearsIn": ["NEWHOPE", "EMPIRE", "JEDI"],
                    "friends": [
                        {"name": "Han Solo"},
                        {"name": "Leia Organa"},
                        {"name": "C-3PO"},
                        {"name": "R2-D2"},
                    ],
                },
                {
                    "name": "Han Solo",
                    "appearsIn": ["NEWHOPE", "EMPIRE", "JEDI"],
                    "friends": [
                        {"name": "Luke Skywalker"},
                        {"name": "Leia Organa"},
                        {"name": "R2-D2"},
                    ],
                },
                {
                    "name": "Leia Organa",
                    "appearsIn": ["NEWHOPE", "EMPIRE", "JEDI"],
                    "friends": [
                        {"name": "Luke Skywalker"},
                        {"name": "Han Solo"},
                        {"name": "C-3PO"},
                        {"name": "R2-D2"},
                    ],
                },
            ],
        }
    }
    result = graphql(StarWarsSchema, query)
    assert not result.errors
    assert result.data == expected


def test_fetch_luke_query():
    query = """
        query FetchLukeQuery {
          human(id: "1000") {
            name
          }
        }
    """
    expected = {"human": {"name": "Luke Skywalker"}}
    result = graphql(StarWarsSchema, query)
    assert not result.errors
    assert result.data == expected


def test_fetch_some_id_query():
    query = """
        query FetchSomeIDQuery($someId: String!) {
          human(id: $someId) {
            name
          }
        }
    """
    params = {"someId": "1000"}
    expected = {"human": {"name": "Luke Skywalker"}}
    result = graphql(StarWarsSchema, query, variable_values=params)
    assert not result.errors
    assert result.data == expected


def test_fetch_some_id_query2():
    query = """
        query FetchSomeIDQuery($someId: String!) {
          human(id: $someId) {
            name
          }
        }
    """
    params = {"someId": "1002"}
    expected = {"human": {"name": "Han Solo"}}
    result = graphql(StarWarsSchema, query, variable_values=params)
    assert not result.errors
    assert result.data == expected


def test_invalid_id_query():
    query = """
        query humanQuery($id: String!) {
          human(id: $id) {
            name
          }
        }
    """
    params = {"id": "not a valid id"}
    expected = {"human": None}
    result = graphql(StarWarsSchema, query, variable_values=params)
    assert not result.errors
    assert result.data == expected


def test_fetch_luke_aliased():
    query = """
        query FetchLukeAliased {
          luke: human(id: "1000") {
            name
          }
        }
    """
    expected = {"luke": {"name": "Luke Skywalker"}}
    result = graphql(StarWarsSchema, query)
    assert not result.errors
    assert result.data == expected


def test_fetch_luke_and_leia_aliased():
    query = """
        query FetchLukeAndLeiaAliased {
          luke: human(id: "1000") {
            name
          }
          leia: human(id: "1003") {
            name
          }
        }
    """
    expected = {"luke": {"name": "Luke Skywalker"}, "leia": {"name": "Leia Organa"}}
    result = graphql(StarWarsSchema, query)
    assert not result.errors
    assert result.data == expected


def test_duplicate_fields():
    query = """
        query DuplicateFields {
          luke: human(id: "1000") {
            name
            homePlanet
          }
          leia: human(id: "1003") {
            name
            homePlanet
          }
        }
    """
    expected = {
        "luke": {"name": "Luke Skywalker", "homePlanet": "Tatooine"},
        "leia": {"name": "Leia Organa", "homePlanet": "Alderaan"},
    }
    result = graphql(StarWarsSchema, query)
    assert not result.errors
    assert result.data == expected


def test_use_fragment():
    query = """
        query UseFragment {
          luke: human(id: "1000") {
            ...HumanFragment
          }
          leia: human(id: "1003") {
            ...HumanFragment
          }
        }
        fragment HumanFragment on Human {
          name
          homePlanet
        }
    """
    expected = {
        "luke": {"name": "Luke Skywalker", "homePlanet": "Tatooine"},
        "leia": {"name": "Leia Organa", "homePlanet": "Alderaan"},
    }
    result = graphql(StarWarsSchema, query)
    assert not result.errors
    assert result.data == expected


def test_check_type_of_r2():
    query = """
        query CheckTypeOfR2 {
          hero {
            __typename
            name
          }
        }
    """
    expected = {"hero": {"__typename": "Droid", "name": "R2-D2"}}
    result = graphql(StarWarsSchema, query)
    assert not result.errors
    assert result.data == expected


def test_check_type_of_luke():
    query = """
        query CheckTypeOfLuke {
          hero(episode: EMPIRE) {
            __typename
            name
          }
        }
    """
    expected = {"hero": {"__typename": "Human", "name": "Luke Skywalker"}}
    result = graphql(StarWarsSchema, query)
    assert not result.errors
    assert result.data == expected


def test_parse_error():
    query = """
        qeury
    """
    result = graphql(StarWarsSchema, query)
    assert result.invalid
    formatted_error = format_error(result.errors[0])
    assert formatted_error["locations"] == [{"column": 9, "line": 2}]
    assert (
        'Syntax Error GraphQL (2:9) Unexpected Name "qeury"'
        in formatted_error["message"]
    )
    assert result.data is None
