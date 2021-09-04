# coding=utf-8
"""
anilist.py - Sopel AniList Plugin
Copyright 2020-2021 SleepingPanda & dgw
Licensed under the Eiffel Forum License 2.

https://sopel.chat
"""
from __future__ import unicode_literals, absolute_import, print_function, division

try:
    from json import JSONDecodeError
except ImportError:
    # Python < 3.5
    JSONDecodeError = ValueError

import bleach
import requests

from sopel import formatting, module
from sopel.tools import web


ANILIST_ENDPOINT = "https://graphql.anilist.co/"
QUERIES = {
    "anime": """
        query ($name: String) {
            Media (search: $name, type: ANIME) {
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
        query ($name: String) {
            Media (search: $name, type: MANGA) {
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
        query ($name: String) {
            Character(search: $name) {
                id
                name {
                    full
                    native
                }
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


@module.commands('anilist', 'al')
def al_anime(bot, trigger):
    """Queries AniList for an anime matching the search input."""
    if not trigger.group(2):
        bot.reply("You have to tell me what to search.")
        return

    variables = {
        'name': trigger.group(2),
    }
    try:
        data = al_query(QUERIES['anime'], variables)
    except AniListAPIError as e:
        bot.reply("Error: {}".format(str(e)))
        return

    if data.get('errors', []):
        bot.reply("No results found for '%s'." % trigger.group(2))
    else:
        media = data['data']['Media']
        title = next(media['title'][lang] for lang in ['english', 'romaji', 'native'] if media['title'][lang] is not None)
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
        bot.say(truncate_result(output))


@module.commands('anilistmanga', 'alm')
def al_manga(bot, trigger):
    """Queries AniList for an manga matching the search input."""
    if not trigger.group(2):
        bot.reply("You have to tell me what to search.")
        return

    variables = {
        'name': trigger.group(2),
    }
    try:
        data = al_query(QUERIES['manga'], variables)
    except AniListAPIError as e:
        bot.reply("Error: {}".format(str(e)))
        return

    if data.get('errors', []):
        bot.reply("No results found for '%s'." % trigger.group(2))
    else:
        media = data['data']['Media']
        title = next(media['title'][lang] for lang in ['english', 'romaji', 'native'] if media['title'][lang] is not None)
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
        bot.say(truncate_result(output))


@module.commands('anilistchar', 'alc')
def al_character(bot, trigger):
    """Queries AniList for a character matching the search input."""
    if not trigger.group(2):
        bot.reply("You have to tell me what to search.")
        return

    variables = {
        'name': trigger.group(2),
    }
    try:
        data = al_query(QUERIES['character'], variables)
    except AniListAPIError as e:
        bot.reply("Error: {}".format(str(e)))
        return

    if data.get('errors', []):
        bot.reply("No results found for '%s'." % trigger.group(2))
    else:
        char = data['data']['Character']
        media = char['media']['nodes'][0]
        name = char['name']['full'] or char['name']['native']
        title = next(media['title'][lang] for lang in ['english', 'romaji', 'native'] if media['title'][lang] is not None)

        output = (
            "{name} from {title} | {description}"
        ).format(
            char=char,
            name=name,
            title=title,
            description=(clean_html(char['description']) or NO_DESCRIPTION),
        )
        bot.say(truncate_result(output))


def clean_html(input):
    output = bleach.clean(input, tags=[], strip=True)
    return web.decode(output)


def truncate_result(text):
    if len(text) > 400:
        last_space = text.rfind(' ', 0, 400)
        if last_space == -1:
            # force hard break if the text doesn't contain any spaces
            r = text[:400]
        else:
            r = text[:last_space]

        # add ellipsis only if the input was actually shortened
        if len(r) < len(text):
            r += '…'

        return r

    return text
