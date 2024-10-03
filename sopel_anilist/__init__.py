"""sopel-anilist

AniList plugin for Sopel IRC bots

Copyright 2020-2021 SleepingPanda & dgw
Licensed under the Eiffel Forum License 2.

https://sopel.chat
"""
from __future__ import annotations

from json import JSONDecodeError

import bleach
import requests

from sopel import formatting, plugin
from sopel.tools import web


ANILIST_ENDPOINT = "https://graphql.anilist.co/"
QVARS = {
    "id": ("$id: Int", "id: $id"),
    "search": ("$name: String", "search: $name"),
}
QUERIES = {
    "anime": """
        query (%s) {
            Media (%s, type: ANIME) {
                title {
                    romaji
                    english
                    native
                }
                format
                seasonYear
                averageScore
                status
                episodes
                siteUrl
                genres
                description (asHtml: true)
                characters (role: MAIN) {
                    edges {
                        node {
                            name {
                                full
                            }
                        }
                        voiceActors (language: JAPANESE) {
                            name {
                                full
                            }
                        }
                    }
                }
                studios (isMain: true) {
                    nodes {
                        name
                    }
                }
            }
        }
    """,
    "manga": """
        query (%s) {
            Media (%s, type: MANGA) {
                title {
                    romaji
                    english
                    native
                }
                format
                startDate {
                    year
                }
                averageScore
                status
                volumes
                siteUrl
                genres
                description (asHtml: true)
                characters (role: MAIN) {
                    nodes {
                        name {
                            full
                        }
                    }
                }
                staff {
                    nodes {
                        name {
                            full
                        }
                    }
                }
            }
        }
    """,
    "character": """
        query (%s) {
            Character(%s) {
                id
                name {
                    full
                    native
                }
                siteUrl
                description(asHtml: true)
                media {
                    nodes {
                        id
                        title {
                            romaji
                            english
                            native
                        }
                        type
                    }
                }
            }
        }
    """,
    "staff": """
        query (%s) {
            Staff(%s) {
                id
                name {
                    full
                    native
                }
                siteUrl
                primaryOccupations
                yearsActive
            }
        }
    """,
}

NO_DESCRIPTION = formatting.italic('[no description available]')


class AniListAPIError(Exception):
    pass


def al_query(query, variables={}):
    """Send a GraphQL query to AniList.

    :param str query: the query to send
    :param variables: any variables needed for the query to run
    :type variables: :class:`dict`
    :return: Decoded JSON result
    :rtype: :class:`dict`
    :raise AniListAPIError: when the API request fails for any reason
    """
    try:
        r = requests.post(
            ANILIST_ENDPOINT,
            json={
                'query': query,
                'variables': variables,
            },
        )
    except Exception as e:
        raise AniListAPIError("Communication with AniList failed.")

    try:
        data = r.json()
    except JSONDecodeError:
        raise AniListAPIError("JSON decoding failed.")

    return data


@plugin.url(r'https?://anilist\.co/(?P<type>anime|manga|character|staff)/(?P<id>\d+)')
def anilist_link(bot, trigger):
    # yes, this is the hacky way
    # I don't want to maintain a mapping
    globals()['al_' + trigger.group('type')](bot, trigger, trigger.group('id'))


@plugin.commands('anilist', 'al')
def al_anime(bot, trigger, id_=None):
    """Queries AniList for an anime matching the search input."""
    if id_ is None and not trigger.group(2):
        bot.reply("You have to tell me what to search.")
        return

    variables = {}
    if id_ is None:
        variables['name'] = trigger.group(2)
    else:
        variables['id'] = id_

    qvars = QVARS['id'] if id_ else QVARS['search']
    query = QUERIES['anime'] % (qvars[0], qvars[1])  # % because .format() would require doubling every { and }

    try:
        data = al_query(query, variables)
    except AniListAPIError as e:
        bot.reply("Error: {}".format(str(e)))
        return

    if data.get('errors', []):
        bot.reply("No results found for '%s'." % trigger.group(2))
    else:
        media = data['data']['Media']
        title = next(media['title'][lang] for lang in ['romaji', 'native', 'english'] if media['title'][lang] is not None)
        studios = ', '.join([studio['name'] for studio in media['studios']['nodes']])
        genres = ', '.join(media['genres'])
        voice_actors = ', '.join(
            [
                va['name']['full']
                for char in media['characters']['edges']
                for va in char['voiceActors']
            ]
        )

        output = (
            "{title} ({media[seasonYear]}) | {media[format]} | "
            "Studio: {studios} | Score: {media[averageScore]} | {media[status]} | "
            "Eps: {media[episodes]} | {media[siteUrl]} | Genres: {genres} | "
            "VA: {voice_actors} | Synopsis: {description}"
        ).format(
            media=media,
            title=title,
            studios=studios,
            genres=genres,
            voice_actors=voice_actors,
            description=(clean_html(media['description']) or NO_DESCRIPTION),
        )
        bot.say(output, truncation='…')


@plugin.commands('anilistmanga', 'alm')
def al_manga(bot, trigger, id_=None):
    """Queries AniList for an manga matching the search input."""
    if id_ is None and not trigger.group(2):
        bot.reply("You have to tell me what to search.")
        return

    variables = {}
    if id_ is None:
        variables['name'] = trigger.group(2)
    else:
        variables['id'] = id_

    qvars = QVARS['id'] if id_ else QVARS['search']
    query = QUERIES['manga'] % (qvars[0], qvars[1])  # % because .format() would require doubling every { and }

    try:
        data = al_query(query, variables)
    except AniListAPIError as e:
        bot.reply("Error: {}".format(str(e)))
        return

    if data.get('errors', []):
        bot.reply("No results found for '%s'." % trigger.group(2))
    else:
        media = data['data']['Media']
        title = next(media['title'][lang] for lang in ['romaji', 'native', 'english'] if media['title'][lang] is not None)
        staff = ', '.join([staff['name']['full'] for staff in media['staff']['nodes']])
        genres = ', '.join(media['genres'])
        characters = ', '.join(
            [
                char['name']['full']
                for char in media['characters']['nodes']
            ]
        )
        output = (
            "{title} ({media[startDate][year]}) | {media[format]} | "
            "Staff: {staff} | Score: {media[averageScore]} | {media[status]} | "
            "Vols: {media[volumes]} | {media[siteUrl]} | Genres: {genres} | "
            "MC: {characters} | Synopsis: {description}"
        ).format(
            media=media,
            title=title,
            staff=staff,
            genres=genres,
            characters=characters,
            description=(clean_html(media['description']) or NO_DESCRIPTION),
        )
        bot.say(output, truncation='…')


@plugin.commands('anilistchar', 'alc')
def al_character(bot, trigger, id_=None):
    """Queries AniList for a character matching the search input."""
    if id_ is None and not trigger.group(2):
        bot.reply("You have to tell me what to search.")
        return

    variables = {}
    if id_ is None:
        variables['name'] = trigger.group(2)
    else:
        variables['id'] = id_

    qvars = QVARS['id'] if id_ else QVARS['search']
    query = QUERIES['character'] % (qvars[0], qvars[1])  # % because .format() would require doubling every { and }

    try:
        data = al_query(query, variables)
    except AniListAPIError as e:
        bot.reply("Error: {}".format(str(e)))
        return

    if data.get('errors', []):
        bot.reply("No results found for '%s'." % trigger.group(2))
    else:
        char = data['data']['Character']
        media = char['media']['nodes'][0]
        name = char['name']['full'] or char['name']['native']
        title = next(media['title'][lang] for lang in ['romaji', 'native', 'english'] if media['title'][lang] is not None)

        output = (
            "{name} from {title} | {link} | {description}"
        ).format(
            name=name,
            title=title,
            link=char['siteUrl'],
            description=(clean_html(char['description']) or NO_DESCRIPTION),
        )
        bot.say(output, truncation='…')


@plugin.commands('aniliststaff', 'als')
def al_staff(bot, trigger, id_=None):
    """Queries AniList for staff (person) matching the search input."""
    if id_ is None and not trigger.group(2):
        bot.reply("You have to tell me what to search.")
        return

    variables = {}
    if id_ is None:
        variables['name'] = trigger.group(2)
    else:
        variables['id'] = id_

    qvars = QVARS['id'] if id_ else QVARS['search']
    query = QUERIES['staff'] % (qvars[0], qvars[1])  # % because .format() would require doubling every { and }

    try:
        data = al_query(query, variables)
    except AniListAPIError as e:
        bot.reply("Error: {}".format(str(e)))
        return

    if data.get('errors', []):
        bot.reply("No results found for '%s'." % trigger.group(2))
    else:
        staff = data['data']['Staff']
        name = staff['name']['full'] or staff['name']['native']
        occupations = ', '.join(staff['primaryOccupations']) or '(unknown roles)'

        active_vals = len(staff['yearsActive'])
        if active_vals == 2:
            years_active = '%s—%s' % (staff['yearsActive'][0], staff['yearsActive'][1])
        elif active_vals == 1:
            years_active = '%s–present' % staff['yearsActive'][0]
        else:
            years_active = '(no data)'

        output = (
            "{name}: {occupations} | Active {active} | {link}"
        ).format(
            name=name,
            occupations=', '.join(staff['primaryOccupations']),
            active=years_active,
            link=staff['siteUrl'],
        )
        bot.say(output, truncation='…')


def clean_html(input):
    output = bleach.clean(input, tags=[], strip=True)
    return web.decode(output)
