import asyncio
import datetime
import json
import logging
import os.path
import telepot
import tweepy
import urllib
from bs4 import BeautifulSoup
from secrets import telegramBotToken, C_KEY, C_SECRET, A_TOKEN, A_TOKEN_SECRET, channel

class pubMedArticle():
	def __init__(self, div, hashTag="#IgG4RD"):
		self._div = div
		self._hashTag = hashTag
		self._title = div.find("p", { "class" : "title" }).text.replace("<sub>", "").replace("</sub>", "").replace("<sup>", "").replace("</sup>", "") #sub- and superscript used to cause troubles, hence they are replaced
		self._link = div.find("p", { "class" : "title" }).a["href"]
		self._authors = div.find("div", { "class" : "supp" }).p.text
		self._journal = div.find("span", { "class" : "jrnl" }).attrs['title']
	
	@staticmethod
	def getPubMedTweet(hashTag = "#IgG4RD", title="string", authors=["list"], link="url"):
		title = title.split()[::-1]
		authors=authors[::-1]
		maxTweetLen = 140-(len(hashTag)+1)-(len(link) + len("http:// "))#Twitter counts characters in links considering "http://" prefix and " " suffix, so the max lenght is furtherly reduced
		authorsLen = 25
		titleLen = 50
		tweet={"authors":[], "title":[]}
		temp=""
		while len(temp)<titleLen:
			temp = hashTag + " " + " ".join(tweet["title"]) + (" [...]. " if len(title)>0 else " ")
			if len(title)==0:
				break
			tweet["title"].append(title.pop())
		even=1
		while len(temp)<maxTweetLen:
			temp = hashTag + " " + " ".join(tweet["title"]) + (" [...]. " if len(title)>0 else " ") + ", ".join(tweet["authors"]) + (" &al. " if len(authors)>0 else ". ") + link
			if even:
				if len(title)>0:
					tweet["title"].append(title.pop())
				even=0
			else:
				if len(authors)>0 and not even:
					tweet["authors"].append(authors.pop())
				even=1
			if len(title)==0 and len(authors)==0:
				break
		return temp
	
	@property
	def hashTag(self):
		return self._hashTag
	
	@property
	def title(self):
		return self._title
	
	@property
	def link(self):
		return "pmid.us" + self._link.replace("/pubmed", "")
	
	@property
	def authors(self):
		def splitAuthors(authString):
			authList = [x for x in authString.replace(",","").split() if x!=x.upper()]
			authList = [authList[-1]] + authList[:-1]
			return authList
		return splitAuthors(self._authors)
	
	@property
	def tweet(self):
		return self.getPubMedTweet(self.hashTag, self.title, self.authors, self.link)
	
	@property
	def journal(self):
		return self._journal
	
	@property
	def ext(self):
		return "{s.hashTag}\n*{s.title}*\n_{s._authors}_\n{s.journal}".format(s=self)

def jsonread(file):
	if not os.path.exists(file):
		logging.error("{} is not a valid file, {{}} is returned.".format(file))
		return {}
	with open(file, "r") as f:
		return json.load(f)

def jsonwrite(what, file):
	with open(file, "w") as f:
		return json.dump(what, f, indent=4)
	
def isOld(what, howMuch=5, unit="minutes"):
	"""
	Accepts a datetime object or a string (YYYYmmddHHMMSS) and an amount of minutes and returns
		- True if more thant *howMuch* minutes have passed since *what*
		- False if *what* is recent (less than *howMuch* minutes have passed)
		- TypeError is raised if *what* is neither a string or a datetime.datetime object
	"""
	if unit=="minutes":
		cutOff = datetime.timedelta(minutes=howMuch)
	elif unit=="seconds":
		cutOff = datetime.timedelta(seconds=howMuch)
	if isinstance(what, datetime.datetime):
		what = datetime.datetime.strftime(what, "%Y%m%d%H%M%S")
	if type(what) is not str:
		raise TypeError("The first parameter must be a str or a datetime.datetime object")
	return what <= datetime.datetime.strftime(datetime.datetime.now() - cutOff, "%Y%m%d%H%M%S")

async def isItTimeTo(what, interval):
	global lastActions
	if what in lastActions:
		while not isOld(what=lastActions[what], howMuch=interval, unit="seconds"):
			await asyncio.sleep(interval/10)
	return

async def checkPeriodically(interval=60*60):
	what = "tweet"
	try:
		global auth, api
		while 1:
			#Checks only if interval time has passed since last check
			await isItTimeTo(what, interval)
			logging.info("... checking for news ...")
			#Process new results for advanced pubmed search: each new result is a "<div class: rslt>" element of this BeautifulSoup-interpreted html page open by urllib
			new = set(BeautifulSoup(urllib.request.urlopen(pubMedSearch).read(), 'html.parser').findAll("div", { "class" : "rslt" }))
			previousTweets = jsonread(tweetFile)
			if len(previousTweets)==0:
				previousTweets = []
			#Excludes previous tweets
			difference = [a for a in [pubMedArticle(x) for x in new] if a.tweet not in previousTweets]
			if len(difference)==0:
				logging.info("... nothing new ...")
				if len(privateTelegramUsers):
					try:
						await bot.sendMessage(privateTelegramUsers[0], "Just checked PubMed for news but there aren't.")
					except Exception as e:
						logging.debug("Failed to send via Telegram. Error description:\n{e}".format(e=e))
			for a in difference:
				tweet = a.tweet
				extended = a.ext
				print("Tweet:\n{}\n\nExtended:\n{}\n\n\n".format(tweet, extended))
				logging.info("Found a new article!")
				sent, tries = False, 0
				while (not sent) and (tries<100):
					try:
						api.update_status(tweet)
						sent=True
						previousTweets.append(tweet)
						jsonwrite(previousTweets, tweetFile)
						logging.info("\n\nJust twitted:\n{}\n".format(tweet))
					except Exception as e:
						#Awaits some time (the more failures, the longer the pause) and repeats Twitter authentication
						logging.debug("Failed to tweet, trying again in {sec} seconds. Error description:\n{e}".format(sec=2+tries, e=e))
						await asyncio.sleep(2+tries)
						auth = tweepy.OAuthHandler(C_KEY, C_SECRET)
						auth.set_access_token(A_TOKEN, A_TOKEN_SECRET)
						api = tweepy.API(auth)
						tries+=1
				try:
					for interested in privateTelegramUsers:
						await bot.sendMessage(interested,tweet,parse_mode=None)
				except Exception as e:
					logging.debug("Failed to send via Telegram. Error description:\n{e}".format(e=e))
				try:
					await bot.sendMessage(channel, extended, parse_mode="Markdown", reply_markup = {'inline_keyboard': [[{'text': "Read the article", 'url': a.link}]]})
				except Exception as e:
					logging.debug("Failed to post on Telegram channel. Error description:\n{e}".format(e=e))
				#Awaits 1 minute between updates
				await asyncio.sleep(60)
			#Awaits interval between repeats
			lastActions[what] = datetime.datetime.strftime(datetime.datetime.now(), "%Y%m%d%H%M%S")
			jsonwrite(previousTweets, lastActionsFile)
	except Exception as e:
		logging.error(e, exc_info=True)
	return

# ----------- Logging configuration ----------- #
logFile = "PubMedTTBot.log"
logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s %(levelname)-5.5s]  %(message)s")
rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)
fileHandler = logging.FileHandler(logFile, mode="a", encoding="utf-8")
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)

# ----------- Telepot configuration ----------- #
bot = telepot.aio.Bot(telegramBotToken)

# ----------- Global variables ----------- #
tweetFile = "tweets.txt"
lastActionsFile = "lastActions.txt"
# Twitter API authorization through tweepy (see tweepy documentation)
auth = tweepy.OAuthHandler(C_KEY, C_SECRET)
auth.set_access_token(A_TOKEN, A_TOKEN_SECRET)
api = tweepy.API(auth)
# lastActions is a dictionary {what: when}, useful not to repeat actions too early after bot is restarted. It gets checked by isItTimeTo(what, interval) function
lastActions = jsonread(lastActionsFile)
#pubMedSearch is a url to a pubmed advanced searc, e.g. "https://www.ncbi.nlm.nih.gov/pubmed/?term=(%22IgG4RD%22+OR+%22IgG4-RD%22+OR+%22IgG4+related+disease%22)"
try:
	from secrets import pubMedSearch
except:
	pubMedSearch = input("Give me a PubMed advanced search url to have it checked:\t\t")
try:
	from secrets import privateTelegramUsers
except:
	tmp, privateTelegramUsers = "", []
	while 1:
		tmp = input("Who should be noticed in private chat when an update is available? Please enter Telegram numeric IDs. When you're done, leave blank\n\t\t")
		if len(tmp)==0:
			break
		try:
			privateTelegramUsers.append(int(tmp))
		except:
			print("Invalid input. Please enter a Telegram numeric id or leave blank to skip this part")

loop = asyncio.get_event_loop()
asyncio.ensure_future(checkPeriodically())
loop.run_forever()