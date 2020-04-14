# coding=utf-8
"""
search.py - Sopel Search Engine Module
Copyright 2008-9, Sean B. Palmer, inamidst.com
Copyright 2012, Elsie Powell, embolalia.com
Licensed under the Eiffel Forum License 2.

https://sopel.chat
"""
from __future__ import unicode_literals, absolute_import, print_function, division

import requests

from sopel import module
from sopel.tools import web


ANILIST_ENDPOINT = "https://graphql.anilist.co/"
QUERIES = {
    "anime": """
        query ($name: String) {
            Media (search: $name, type: ANIME) {
                title {
                    romaji
                    english
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
    "character": """
        query ($name: String) {
            Character(search: $name) {
                id
                name {
                    first
                    last
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
                            userPreferred
                        }
                        type
                    }
                }
            }
        }
    """,
}


@module.commands('anilist', 'al')
def al_anime(bot, trigger):
    """Queries AniList for an anime matching the search input."""
    if not trigger.group(2):
        return

    variables = {
        'name': trigger.group(2),
    }
    result = requests.post(ANILIST_ENDPOINT, json={'query': QUERIES['anime'], 'variables': variables})
    data = result.json()['data']

    if data:
        bot.say(data['Media']['title']['english'] + ' (' + data['Media']['seasonYear'] + ') | ' + data['Media']['format'] + ' | Studio: ' + data['Media']['studios']['nodes']['name'] + ' | Score: ' + data['Media']['averageScore'] + ' | ' + data['Media']['status'] + ' Eps: ' + data['Media']['episodes'] + ' | ' + data['Media']['siteUrl'] + ' | Genres: ' + data['Media']['genres'] + ' | VA: ' + data['Media']['characters']['edges']['voiceActors'] + ' | Synopsis: ' + data['Media']['description'])
    else:
        bot.reply("No results found for '%s'." % query)


@module.commands('anilistchar', 'alc')
def al_character(bot, trigger):
    """Queries AniList for a character matching the search input."""
    if not trigger.group(2):
        return

    variables = {
        'name': trigger.group(2),
    }
    result = requests.post(ANILIST_ENDPOINT, json={'query': QUERIES['character'], 'variables': variables})
    data = result.json()['data']

    if data:
        bot.say(data['Character']['name']['full'] + ' from ' + data['Character']['media']['nodes'][0]['title']['userPreferred'])
    else:
        bot.reply("No results found for '%s'." % query)
