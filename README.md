# Twitter & Telegram bot monitoring a PubMed advanced search
This project provides code which can be run o a server to check for new results of a specific PubMed search.
When a new article is detected, it gets posted on twitter and Telegram channel and sent to a list of user by a Telegram bot.
## Credits
#### Credits to:
* [TweePy](https://github.com/tweepy/tweepy)
* [telepot by nickoala](https://github.com/nickoala/telepot)
* [bs4](https://www.crummy.com/software/BeautifulSoup/)

All of them come with MIT license:

MIT License

Copyright (c) 2013-2014 Joshua Roesslein

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

## Instructions
* Install all required modules:
```
pip install telepot
pip install tweepy
pip install bs4
```
* Insert your private data in a file called secrets.py (it is .gitignored). Here is an example:
```
#Telegram
telegramBotToken = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"#To get a token, [ask BotFather](https://telegram.me/botfather)
channel = "@telegram"#Create a new channel and put here its @address (@telegram is Telegram's official news channel)
privateTelegramUsers = [123456789, 234567891]#List of users' numerical IDs who will receive a Telegram message by the bot when a new article is detected. First of them will receive also "nothing new" notifications. May be empty (I suggest not).

#Twitter
# The consumer keys can be found on your application's Details page located at https://dev.twitter.com/apps (under "OAuth settings")
C_KEY = ""
C_SECRET = ""
# The access tokens can be found on your applications's Details page located at https://dev.twitter.com/apps (located under "Your access token")
A_TOKEN = ""
A_TOKEN_SECRET = ""

#PubMed
pubMedSearch = """https://www.ncbi.nlm.nih.gov/pubmed?term=......&cmd=DetailsSearch"""#Copy url from any PubMed advanced search
```
