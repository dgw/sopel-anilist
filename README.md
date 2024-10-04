# sopel-anilist

AniList plugin for Sopel IRC bots

## Installing

Releases are hosted on PyPI, so after installing Sopel, all you need is `pip`:

```shell
$ pip install sopel-anilist
```

## Using

This plugin provides four lookup types:

- Anime search by title: `.anilist`/`.al`
- Character search by name: `.anilistchar`/`.alc`
- Manga search by title: `.anilistmanga`/`.alm`
- Person (VAs/staff) search by name: `.aniliststaff`/`.als`

Some of these lookups (staff info, in particular) are pretty basic, but
hopefully they're still useful to have around as a tool to directly search
AniList from your IRC client. AniList URLs are provided in case you want to see
data not included in the bot's replies.

The plugin will also show information about links sent to the channel for any of
the supported item types.
