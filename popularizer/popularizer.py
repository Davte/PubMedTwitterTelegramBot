"""Check PubMed for news about a topic.

When a new article is found, update Twitter status, post in Telegram channel
    and notify Telegram users about it.
"""

# Standard library modules
import asyncio
import datetime
import logging

# Third party modules
import bs4
import tweepy
from davtelepot.utilities import (
    async_get, make_inline_keyboard, sleep_until
)


class TwitterAPI(object):
    """Twitter API log-in object."""

    def __init__(self, C_KEY, C_SECRET, A_TOKEN, A_TOKEN_SECRET):
        """Create TwitterAPI object and set Twitter tokens."""
        self.C_KEY = C_KEY
        self.C_SECRET = C_SECRET
        self.A_TOKEN = A_TOKEN
        self.A_TOKEN_SECRET = A_TOKEN_SECRET

    @property
    def login(self):
        """Take twitter keys and return logged api object."""
        auth = tweepy.OAuthHandler(self.C_KEY, self.C_SECRET)
        auth.set_access_token(self.A_TOKEN, self.A_TOKEN_SECRET)
        api = tweepy.API(auth)
        return api


class PubMedArticle:
    """PubMed Article."""

    def __init__(self, title, all_authors, journal, pmid, hash_tag="#IgG4RD"):
        """Get article object."""
        # <sup> and <sub> are super- and subscripts
        for spam in ["<sub>", "</sub>", "<sup>", "</sup>"]:
            title = title.replace(spam, '')
        self._title = title
        self._all_authors = all_authors
        self._journal = journal
        self._pmid = pmid
        self._hash_tag = hash_tag

    @property
    def title(self):
        return self._title

    @property
    def all_authors(self):
        return self._all_authors

    @property
    def journal_string(self):
        return self._journal

    @property
    def pmid(self):
        return self._pmid

    @property
    def hash_tag(self):
        return self._hash_tag

    @property
    def link(self):
        """Return link to this PubMed article."""
        return f"pmid.us/{self.pmid}"

    @property
    def journal(self):
        """Return journal name."""
        return self._journal

    @property
    def telegram_text(self):
        """Make text to be sent via Telegram."""
        return (
            f"{self.hash_tag}\n"
            f"<b>{self.title}</b>\n"
            f"<i>{self.all_authors}</i>"
            f"\n{self.journal}"
        )

    @property
    def few_authors(self):
        """Return the list of authors, last name first."""
        authors_list = [
            x
            for x in self.all_authors.replace(",", "").split()
            if x != x.upper()
        ]
        authors_list = [authors_list[-1]] + authors_list[:-1]
        return authors_list

    @property
    def tweet(self):
        """Get text to be tweeted."""
        hash_tag = self.hash_tag
        title = self.title
        authors = self.few_authors
        link = self.link
        title = title.split()[::-1]
        authors = authors[::-1]
        tweet_max_length = (
            140  # Twitter max characters
            - (len(hash_tag) + 1)  # Hashtag length
            - (len(link) + len("http:// "))  # Links are counted as +8 chars
        )
        title_length = 50
        tweet = dict(
            authors=[],
            title=[]
        )
        temp = ""
        while len(temp) < title_length:
            temp = "{ht} {t}{etc}".format(
                ht=hash_tag,
                t=" ".join(
                    tweet["title"]
                ),
                etc=(
                    " [...]. "
                    if len(title) > 0
                    else " "
                )
            )
            if len(title) == 0:
                break
            tweet["title"].append(title.pop())
        even = 1
        while len(temp) < tweet_max_length:
            temp = "{ht} {title}{etc_t}{authors}{etc_a}{link}".format(
                ht=hash_tag,
                title=" ".join(
                    tweet["title"]
                ),
                etc_t=(
                    " [...]. "
                    if len(title) > 0
                    else " "
                ),
                authors=", ".join(
                    tweet["authors"]
                ),
                etc_a=(
                    " &al. "
                    if len(authors) > 0
                    else ". "
                ),
                link=link
            )
            if even:
                if len(title) > 0:
                    tweet["title"].append(title.pop())
                even = 0
            else:
                if len(authors) > 0 and not even:
                    tweet["authors"].append(authors.pop())
                even = 1
            if len(title) == 0 and len(authors) == 0:
                break
        return temp


async def post_on_telegram(bot, article, telegram_addressees):
    """Make `bot` send updates about `article` via telegram."""
    for addressee in telegram_addressees:
        await bot.send_message(
            chat_id=addressee,
            text=article.telegram_text,
            parse_mode="HTML",
            reply_markup=make_inline_keyboard(
                [
                    dict(
                        text="Read the article",
                        url=article.link
                    )
                ],
                1
            )
        )


async def handle_news(api, bot, difference, telegram_addressees, admins,
                      cooldown):
    """Take a set of `difference`s and handle them.

    Update Twitter status, send in Telegram channel and notify Telegram
        users about news from PubMed.
    """
    for article in difference:
        tweet = article.tweet
        logging.info("Handling a PubMed article...")
        sent = False
        tries = 0
        while (not sent) and (tries < 100):
            try:
                # Tweet news
                api.login.update_status(tweet)
                sent = True
                logging.info(
                    "Tweet was sent\n{t}".format(t=tweet)
                )
                with bot.db as db:
                    db['tweets'].insert(
                        dict(
                            tweet=tweet,
                            pmid=article.pmid
                        )
                    )
                logging.info(
                    "Tweet was stored in bot database."
                )
                try:
                    await post_on_telegram(bot, article, telegram_addressees)
                except Exception as e:
                    logging.debug(
                        "Invio su telegram fallito, "
                        "errore:\n{}".format(
                            e
                        )
                    )
            except Exception as e:
                logging.debug(
                    "Tweet failed, I will try to repeat authentication"
                    "in {sec} seconds. Error:\n{e}".format(
                        sec=2+tries,
                        e=e
                    )
                )
                await asyncio.sleep(2+tries)
                tries += 1
        await asyncio.sleep(cooldown)
    # for admin in admins:
    #     try:
    #         await bot.send_message(
    #             chat_id=admin,
    #             text="No news found on PubMed.",
    #             parse_mode=None,
    #             disable_notification=True
    #         )
    #     except Exception as e:
    #         tries += 1
    #         logging.error(e, exc_info=True)
    #         await asyncio.sleep(10)
    return


async def monitor_pubmed(interval=60*60, bot=None, pub_med_search_url='',
                         C_KEY=None, C_SECRET=None,
                         A_TOKEN=None, A_TOKEN_SECRET=None,
                         telegram_addressees=None,
                         admins=None,
                         cooldown_between_twitter_updates=60*60/100):
    """Every `interval` seconds check for news.

    If new articles are found, publish on Twitter and in a Telegram public
        channel and notify certain Telegram users in private chat.

    `interval` [int]: period in seconds between PubMed checks
    `bot` [obj]: telepot.aio.Bot object
    `pub_med_search_url` [str]: search string
    `C_KEY, C_SECRET, A_TOKEN, A_TOKEN_SECRET` [str]: Twitter bot API tokens
    `telegram_addressees` [list]: list of telegram_ids and/or telegram channel
        ids
    `admins` [list]: list of telegram_ids to be notified if no news is found
    `cooldown_between_twitter_updates` [int]: seconds to wait between updates
    """
    if admins is None:
        admins = []
    if telegram_addressees is None:
        telegram_addressees = []
    if bot is None:
        raise Exception("Please provide a telepot Bot object.")
    if len(pub_med_search_url) == 0:
        raise Exception("Invalid url.")
    twitter_api = TwitterAPI(C_KEY, C_SECRET, A_TOKEN, A_TOKEN_SECRET)
    try:
        while 1:
            with bot.db as db:
                last_check_record = db['last_actions'].find_one(what='tweet')
            if last_check_record is not None:
                await sleep_until(
                    last_check_record['when']
                    + datetime.timedelta(seconds=interval)
                )
            while bot.under_maintenance:
                await asyncio.sleep(5)
            update_datetime = datetime.datetime.now()
            logging.info("... checking pubmed for new results ...")
            # Loads new results (set of divs having class rslt)
            bs4_parsed_web_page = await async_get(
                pub_med_search_url,
                mode='html'
            )
            if isinstance(bs4_parsed_web_page, Exception):
                logging.error(
                    "Error getting pubmed updates, "
                    "trying again in 5 minutes".format(
                        bs4_parsed_web_page
                    )
                )
                await asyncio.sleep(60*5)
                continue
            news = set(get_articles_from_page(
                bs4_parsed_web_page=bs4_parsed_web_page
            ))
            # Ignore articles already tweeted
            already_tweeted = [
                record['pmid']
                for record in bot.db['tweets'].find()
            ]
            difference = [
                result
                for result in news
                if result.pmid not in already_tweeted
            ]
            if len(difference) == 0:
                logging.info("Nothing new on PubMed...")
            await handle_news(
                api=twitter_api,
                bot=bot,
                difference=difference,
                telegram_addressees=telegram_addressees,
                admins=admins,
                cooldown=cooldown_between_twitter_updates
            )
            with bot.db as db:
                db['last_actions'].upsert(
                    dict(
                        what='tweet',
                        when=update_datetime
                    ),
                    ['what']
                )
    except Exception as e:
        logging.error(e, exc_info=True)
    return


async def update_pmid(bot):
    """Update `tweets` table.

    Calculate `pmid` field basing on `tweet`.
    """
    for record in bot.db['tweets'].find(pmid=None):
        logging.info(
            f'tweet #{record["id"]} pmid: None -> {int(record["tweet"][-8:])}'
        )
        bot.db['tweets'].update(
            dict(
                pmid=int(record['tweet'][-8:]),
                id=record['id']
            ),
            ['id']
        )
        await asyncio.sleep(0.5)
    return


def get_articles_from_page(bs4_parsed_web_page: bs4.BeautifulSoup):
    for article in bs4_parsed_web_page.findAll(
            "article",
            {"class": "full-docsum"}):
        article = PubMedArticle(
            title=article.find('a', {'class': 'docsum-title'}).text.strip(),
            all_authors=article.find('span', {'class': 'full-authors'}).text.strip(),
            journal=article.find('span', {'class': 'short-journal-citation'}).text.strip(),
            pmid=article.find('span', {'class': 'docsum-pmid'}).text.strip())
        yield article
