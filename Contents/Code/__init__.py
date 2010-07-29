# -*- coding: utf-8 -*-
# The above line is used to allow european / german characters to be used WITHIN this file (code)
#
# First ALPHA release on 05-23-2009
# Version 0.1
#
# ct TV is the weekly broadcast of ct Magazine; europe's biggest computer magazine.
# This plug-in makes the last 28 shows available
# All the comntent is in German
#
# We use FRAMEWORK #1
#
#

import os.path
from PMS import *
from PMS.Objects import *
from PMS.Shortcuts import *
from PMS.Resource import *
from lxml.etree import fromstring, tostring
from BeautifulSoup import BeautifulSoup
from  htmlentitydefs import entitydefs
import re
import base64
import urllib
import urllib2

PLUGIN_PREFIX   = "/video/ctTV"
ROOT_URL        = "http://www.heise.de/ct-tv/"
BASE_URL        = "http://www.heise.de"
PLUG_IN_LOC     = "~/Library/Application\ Support/Plex\ Media\ Server/Plug-ins/c't\ TV.bundle/Contents/Resources"

CACHE_INTERVAL  = 3600

MainArt         = "%s/:/resources/%s" % (PLUGIN_PREFIX, "art-default.png")
MainThumb       = "%s/:/resources/%s" % (PLUGIN_PREFIX, "icon-default.png")

FrontPage = []
SecondPage = []

Log('(PLUG-IN) Finished importing libraries & setting global variables')

####################################################################################################
def Start():

	# Add the MainMenu prefix handler
	Plugin.AddPrefixHandler(PLUGIN_PREFIX, MainMenu, L("c't TV"), 'icon-default.png', 'art-default.png')

	# Set up view groups
	Plugin.AddViewGroup("List", viewMode="List", mediaType="items")
	Plugin.AddViewGroup("Info", viewMode="InfoList", mediaType="items")

	# Set the default cache time
	HTTP.SetCacheTime(14400)

	# Set the default MediaContainer attributes
	MediaContainer.title1 = "c't TV"
	MediaContainer.content = 'List'
	MediaContainer.art = MainArt

	Log('(PLUG-IN) Finished initiallizing the plug-in')

####################################################################################################


def MainMenu(sender = None):

	global MainArt
	global MainThumb
	global FrontPage

	Log('(PLUG-IN) **==> ENTER Main Menu')
	if MainThumb == None:
		MainArt         = "%s/:/resources/%s" % (PLUGIN_PREFIX, "art-default.png")
		MainThumb       = "%s/:/resources/%s" % (PLUGIN_PREFIX, "icon-default.png")

	# Get the items for the FRONT page ... all top-level menu items
	if len(FrontPage) == 0:
		FrontPage = LoadFP()

	(MainTitle, MainSubtitle, CurrentVideoTitle, CurrentVideoURL, Themes, Topics, Archive) = FrontPage

	dir = MediaContainer(art = MainArt, title1=MainTitle, title2=MainSubtitle, viewGroup="List")

	# Add current SHOW to media container
	# DirectoryItem( key, title, subtitle=None, summary=None, thumb=None, art=None, **kwargs)
	dir.Append(Function(DirectoryItem(CurrentShowMenu,
					  title = CurrentVideoTitle,
					  subtitle= None,
					  summary = None,
					  thumb = None, #Would be nice to use a DIFFERENT Thumb here
					  art= MainArt),
			    CurrentVideoURL = CurrentVideoURL,
			    CurrentVideoTITLE = CurrentVideoTitle,
			    Themes = Themes)
		   )

	# Add all the TOPICS to the container
	anzahl_topics = len(Topics)

	for Topic in range(0, anzahl_topics):

		(URL,TITEL) = Topics[Topic]

		# DirectoryItem( key, title, subtitle=None, summary=None, thumb=None, art=None, **kwargs)
		dir.Append(Function(DirectoryItem(TopicMenu,
						  title = TITEL,
						  subtitle= None,
						  summary = None,
						  thumb = None, #Would be nice to use a DIFFERENT Thumb here
						  art= MainArt),
				    TopicURL = URL)
			   )

	# Add the ARCHIVE to the container
	# DirectoryItem( key, title, subtitle=None, summary=None, thumb=None, art=None, **kwargs)
	dir.Append(Function(DirectoryItem(ArchiveMenu,
					  title = "Sendungsarchiv",
					  subtitle= None,
					  summary = None,
					  thumb = None, #Would be nice to use a DIFFERENT Thumb here
					  art= MainArt),
			    ArchiveList = Archive)
		   )


	Log('(PLUG-IN) <==** EXIT Main Menu')

	return dir

def CurrentShowMenu(sender, CurrentVideoURL, CurrentVideoTITLE, Themes):

	dir = MediaContainer(art = MainArt, title1=sender.title2, title2=CurrentVideoTITLE, viewGroup="Info")

	#class WebVideoItem(self, url, title, subtitle=None, summary=None, duration=None, thumb=None, art=None, **kwargs):
	dir.Append(WebVideoItem(  CurrentVideoURL,
				  CurrentVideoTITLE,
				  subtitle = None,
				  summary = None,
				  duration = None,
				  thumb = MainThumb,
				  art = MainArt
				  )
		   )

	# Check if we have the Themes ... if NOT ==> get them
	if Themes == None:
		# Collect Theme List
		# Test if we need ID - PW ... and get it
		check = getURL(CurrentVideoURL, False)

		# Build a TREE representation of the page
		# Do we need to add the AUTHENTICATION header
		if check[1] <> {None:None}:
			Log('(PLUG-IN) Needed Authentication ctTV-Main Page')
			Show_Main = XML.ElementFromURL(CurrentVideoURL, isHTML=True, values=None, headers=check[1], cacheTime=None, encoding="Latin-1", errors="ignore")
		else:
			Show_Main = XML.ElementFromURL(CurrentVideoURL, isHTML=True, values=None, cacheTime=None, encoding="Latin-1", errors="ignore")

		Themes = getThemes(Show_Main)

	anzahl_themes = len(Themes)

	for Thema in range(0, anzahl_themes):

		(URL,TITEL,DESCRIPTION) = Themes[Thema]

		dir.Append(WebVideoItem(  URL,
					  TITEL,
					  subtitle = None,
					  summary = DESCRIPTION,
					  duration = None,
					  thumb = MainThumb,
					  art = MainArt
					  )
			   )

	return dir

def LoadFP():

	Log('(PLUG-IN) **==> ENTER Load ct TV Main Page')

	OLDMENU = ""

	MenuItems = []
	Page_Items = []

	# Test if we need ID - PW ... and get it
	check = getURL(ROOT_URL, False)

	# Build a TREE representation of the page
	# Do we need to add the AUTHENTICATION header
	if check[1] <> {None:None}:
		Log('(PLUG-IN) Needed Authentication ctTV-Main Page')
		ctTV_Main = XML.ElementFromURL(ROOT_URL, isHTML=True, values=None, headers=check[1], cacheTime=None, encoding="Latin-1", errors="ignore")
	else:
		ctTV_Main = XML.ElementFromURL(ROOT_URL, isHTML=True, values=None, cacheTime=None, encoding="Latin-1", errors="ignore")

	# Read a string version of the page
	ctTV_MainString = cleanHTML(urllib2.urlopen(check[0]).read())

	# Get some MAIN Meta-Data of c't TV:
	MainTitle = ctTV_Main.xpath("/html/body/div[@id='navi_top']/div[1]/ul[1]/li[2]/a")[0]
	MainTitle = tostring(MainTitle).split('">')[1][:-4].replace('<span>','').replace('</span>','').encode('Latin-1').decode('utf-8')
	MainSubtitle = ctTV_Main.xpath("/html/body/div[@id='navi_top']/div[1]/ul[3]/li[4]/a")[0].text.encode('Latin-1').decode('utf-8')

	# Define current video
	CurrentVideoTitle1 = ctTV_Main.xpath("//*[@id='hauptbereich']/div[@id='video']/h1/text()")[0].encode('Latin-1').decode('utf-8')
	CurrentVideoTitle2 = ctTV_Main.xpath("//*[@id='hauptbereich']/div[@id='video']/h1")[0]
	CurrentVideoTitle2 = tostring(CurrentVideoTitle2).split('|')[1].split('<')[0].encode('Latin-1').decode('utf-8')
	CurrentVideoTitle = CurrentVideoTitle1 + '|' + CurrentVideoTitle2
	CurrentVideoURL = ROOT_URL

	# Collect Theme List
	Themes = getThemes(ctTV_Main)

	# Collect Topic List
	Topics = getTopics(ctTV_Main)

	# Collect Video Archive List
	Archive = getArchive(ctTV_MainString)

	#ML(ctTV_Main)

	return (MainTitle, MainSubtitle, CurrentVideoTitle, CurrentVideoURL, Themes, Topics, Archive)

def getThemes(WebPageTree):

	global MainArt
        global MainThumb

        Log('(PLUG-IN) **==> ENTER Getting THEMES from current page')

        if MainThumb == None:
		MainArt         = "%s/:/resources/%s" % (PLUGIN_PREFIX, "art-default.png")
		MainThumb       = "%s/:/resources/%s" % (PLUGIN_PREFIX, "icon-default.png")

	# Get the list of Themes from the Element Tree
        Themelist = WebPageTree.xpath("//*[@id='themenuebersicht']/ul/li/a")

	#ML(Themelist[0])

	# How many did we get?
        anzahl_themen = len(Themelist)

        Themes = []
        # Get the URL, THUMB, and DESCRIPTION for each Thema
        for Thema in range(0,anzahl_themen):

                ThemenSet = Themelist[Thema]

		#ML(ThemenSet)

                try:
                        URL = BASE_URL + ThemenSet.get('href')
                except:
                        URL = "URL Error"

		#ML(URL)

		try:
			TITEL = str(Thema+1) + ". Teil: " + WebPageTree.xpath("//*[@id='themenuebersicht']/ul/li/a/span[@class='titel']/text()")[Thema].encode('Latin-1').decode('utf-8')

		except:
			TITEL = "Titel Error"

		#ML(TITEL)

		try:
			DESCRIPTION = WebPageTree.xpath("//*[@id='themenuebersicht']/ul/li/a/span[@class='beschreibung']/text()")[Thema].encode('Latin-1').decode('utf-8')

		except:
			DESCRIPTION = "DESCRIPTION Error"

		#ML(DESCRIPTION)

                if URL <> "":
                        Themes = Themes + [(URL,TITEL,DESCRIPTION)]

	#Log(len(Themes))

        Log('(PLUG-IN) <==** EXIT Getting THEMES from current page')

        return Themes


def getTopics(WebPageTree):

	global MainArt
        global MainThumb

        Log('(PLUG-IN) **==> ENTER Getting TOPICS from current page')

        if MainThumb == None:
		MainArt         = "%s/:/resources/%s" % (PLUGIN_PREFIX, "art-default.png")
		MainThumb       = "%s/:/resources/%s" % (PLUGIN_PREFIX, "icon-default.png")

	# Get the list of Topics from the Element Tree
        Topiclist = WebPageTree.xpath("//*[@id='navigation-rubriken']/li/a")

	#ML(Topiclist)

	# How many did we get?
        anzahl_Topics = len(Topiclist)

        Topics = []
        # Get the URL and TITLE for each Topic
        for Topic in range(0,anzahl_Topics):

                TopicSet = Topiclist[Topic]

		#ML(TopicSet)

                try:
                        URL = BASE_URL + TopicSet.get('href')
                except:
                        URL = "URL Error"

		#ML(URL)

		try:
			TITEL = WebPageTree.xpath("//*[@id='navigation-rubriken']/li/a")[Topic].text_content().encode('utf-8') #.decode('utf-8').encode('Latin-1').decode('utf-8')
			if isinstance(TITEL, str):
				TITEL = unicode(TITEL,'utf-8')

		except:
			TITEL = "Titel Error"

		#ML(TITEL)

                if URL <> "":
                        Topics = Topics + [(URL,TITEL)]

	Log(len(Topics))

        Log('(PLUG-IN) <==** EXIT Getting TOPICS from current page')

        return Topics

def getArchive(ctTV_MainString):

	global MainArt
        global MainThumb

        Log('(PLUG-IN) **==> ENTER Getting PREVIOUS SHOWS from current page')

        if MainThumb == None:
		MainArt         = "%s/:/resources/%s" % (PLUGIN_PREFIX, "art-default.png")
		MainThumb       = "%s/:/resources/%s" % (PLUGIN_PREFIX, "icon-default.png")

	# Get the list of Previous Shows from the Element Tree
	WebPageTree = ctTV_MainString.split('<script type="text/javascript">')[1].split("</div> \<script\> var scrollto_mini")[0][17:]

	Archivelist = BeautifulSoup(WebPageTree).findAll('a')

        Log(len(Archivelist))
	#ML(Archivelist[0])

	# How many did we get?
        anzahl_Archives = len(Archivelist)

        Archives = []
        # Get the URL, THUMB, and ALT description for each Thema
        for Show in range(0,anzahl_Archives-2):

                ArchiveSet = Archivelist[Show]

		#ML(ArchiveSet)

                # We have to TRY each attribute as not all stations have all attributes.
                try:
                        URL = BASE_URL + ArchiveSet.get('href')
		except:
                        URL = "URL Error"

		#ML(URL)

		try:
                        THUMB = BASE_URL + ArchiveSet.find('img').get('src')
                except:
                        THUMB = "THUMB Error"

		#ML(THUMB)

		try:
			ALT = ArchiveSet.find('img').get('alt')

		except:
			ALT = "ALT Error"

		#ML(ALT)

		try:
			TITEL = ArchiveSet.find('img').get('title')[:-2].replace('-',' ').encode('Latin-1').decode('utf-8')

		except:
			TITEL = "Titel Error"

		#ML(TITEL)

                if URL <> "":
                        Archives = Archives + [(URL,THUMB, ALT, TITEL)]

	Log(len(Archives))

        Log('(PLUG-IN) <==** EXIT Getting PREVIOUS SHOWS from current page')

        return Archives

def TopicMenu(sender, TopicURL):

	global MainArt
	global MainThumb
	global FrontPage

	Log('(PLUG-IN) **==> ENTER Topic Menu')
	if MainThumb == None:
		MainArt         = "%s/:/resources/%s" % (PLUGIN_PREFIX, "art-default.png")
		MainThumb       = "%s/:/resources/%s" % (PLUGIN_PREFIX, "icon-default.png")

	# Get the items for the FRONT page ... all top-level menu items
	if len(FrontPage) == 0:
		FrontPage = LoadFP()

	# Test if we need ID - PW ... and get it
	check = getURL(TopicURL, False)

	# Build a TREE representation of the page
	# Do we need to add the AUTHENTICATION header
	if check[1] <> {None:None}:
		Log('(PLUG-IN) Needed Authentication ctTV-Main Page')
		Topic_Main = XML.ElementFromURL(TopicURL, isHTML=True, values=None, headers=check[1], cacheTime=None, encoding="Latin-1", errors="ignore")
	else:
		Topic_Main = XML.ElementFromURL(TopicURL, isHTML=True, values=None, cacheTime=None, encoding="Latin-1", errors="ignore")

	# Read a string version of the page
	Topic_MainString = cleanHTML(urllib2.urlopen(check[0]).read())

	# Collect Video Archive List
	ArchiveList = getArchive(Topic_MainString)

	dir = MediaContainer(art = MainArt, title1=sender.title2, title2=sender.itemTitle, viewGroup="Info")

	if sender.itemTitle == "News":
		TITEL = "Aktuelle " + sender.itemTitle

	else:
		TITEL = "Aktuell " + sender.itemTitle

	#ML(sender.itemTitle.encode('Latin-1'))

	SUBTITLE = Topic_Main.xpath("//*[@id='hauptbereich']/div[3]/h2")[0].text_content().encode('Latin-1').decode('utf-8')

	if ((sender.itemTitle == "News") or (sender.itemTitle == 'Computer-ABC')):

		SUMMARY = Topic_Main.xpath("//*[@id='hauptbereich']/div[3]/h1")[0].text_content()

		TEMP = ""
		if ((sender.itemTitle == "News")):

			SUMMARY = Topic_Main.xpath("//*/strong")

			for item in range(0,len(SUMMARY)):

				try:
					TEMP = TEMP + str(SUMMARY[item].text_content().encode('Latin-1')) + '\n\n'
				except:
					TEMP = TEMP + str(SUMMARY[item].text_content()) + '\n\n'

			SUMMARY = TEMP

		else:
			SUMMARY = SUMMARY + "\n\n" + Topic_Main.xpath("//*[@id='hauptbereich']/div[3]/p")[0].text_content()

		if ((sender.itemTitle == "Computer-ABC")):

			SUMMARY = SUMMARY.encode('Latin-1').decode('utf-8').encode('Latin-1').decode('utf-8')

		elif ((sender.itemTitle == "News")):
			SUMMARY = SUMMARY.decode('utf-8')

		else:
			SUMMARY = SUMMARY.encode('Latin-1').decode('utf-8')

	else:
		SUMMARY = Topic_Main.xpath("//*[@id='hauptbereich']/div[3]/h1")[0].text_content()

		SUMMARY = SUMMARY + "\n\n" + Topic_Main.xpath("//*[@id='hauptbereich']/div[3]/p")[0].text_content()

		#ML(Topic_Main.xpath("//*[@id='hauptbereich']/div[3]/content_ad_possible/p[1]"))

		SUMMARY = SUMMARY + "\n\n" + Topic_Main.xpath("//*[@id='hauptbereich']/div[3]/content_ad_possible/p[1]")[0].text_content()

		try:
			SUMMARY = SUMMARY.encode('Latin-1').decode('utf-8').encode('Latin-1').decode('utf-8')

		except:
			SUMMARY = SUMMARY.encode('Latin-1').decode('utf-8')

	#class WebVideoItem(self, url, title, subtitle=None, summary=None, duration=None, thumb=None, art=None, **kwargs):
	dir.Append(WebVideoItem(  TopicURL,
				  TITEL,
				  subtitle = SUBTITLE,
				  summary = SUMMARY,
				  duration = None,
				  thumb = MainThumb,
				  art = MainArt
				  )
		   )

	anzahl_archivelist = len(ArchiveList)

	#ML(ArchiveList)

	for Item in range(anzahl_archivelist-2,0,-1):

		(URL,THUMB, ALT, TITEL) = ArchiveList[Item]

		if sender.itemTitle == "Schnurer hilft!":

			try:

				TITEL = TITEL.split('Video Schnurer hilft ')[1]

			except:
				TITEL = 'Video Schnurer hilft '

		elif sender.itemTitle == "News":

			try:

				TITEL = 'News' + TITEL.split('Sendung')[1]

			except:
				TITEL = TITEL

		elif sender.itemTitle == "Computer-ABC":

			try:

				TITEL = "Was ist: " + TITEL.split('ABC')[1]

			except:
				TITEL = TITEL

		else:

			TITEL = TITEL.split('Video ')[1]

		#ML(THUMB)

		(SUBTITLE, SUMMARY) = getArchiveDetail(sender, URL)

		dir.Append(WebVideoItem(  URL,
					  TITEL,
					  subtitle = SUBTITLE,
					  summary = SUMMARY,
					  duration = None,
					  thumb = THUMB,
					  art = MainArt
					  )
			   )

	Log('(PLUG-IN) <==** EXIT Topic Menu')

	return dir

def getArchiveDetail(sender, URL):

	Log('(PLUG-IN) **==> ENTER getArchiveDetail ')

	# Test if we need ID - PW ... and get it
	check = getURL(URL, False)

	# Build a TREE representation of the page
	# Do we need to add the AUTHENTICATION header
	if check[1] <> {None:None}:
		Log('(PLUG-IN) Needed Authentication ctTV-Main Page')
		Archive_Main = XML.ElementFromURL(URL, isHTML=True, values=None, headers=check[1], cacheTime=None, encoding="Latin-1", errors="ignore")
	else:
		Archive_Main = XML.ElementFromURL(URL, isHTML=True, values=None, cacheTime=None, encoding="Latin-1", errors="ignore")

	SUBTITLE = Archive_Main.xpath("//*[@id='hauptbereich']/div[3]/h2")[0].text_content().encode('Latin-1').decode('utf-8')

	if ((sender.itemTitle == "News") or (sender.itemTitle == 'Computer-ABC')):

		SUMMARY = Archive_Main.xpath("//*[@id='hauptbereich']/div[3]/h1")[0].text_content()

		TEMP = ""
		if ((sender.itemTitle == "News")):

			SUMMARY = Archive_Main.xpath("//*/strong")

			for item in range(0,len(SUMMARY)):

				try:
					TEMP = TEMP + str(SUMMARY[item].text_content().encode('Latin-1')) + '\n\n'
				except:
					TEMP = TEMP + str(SUMMARY[item].text_content()) + '\n\n'

			SUMMARY = TEMP

		else:
			SUMMARY = SUMMARY + "\n\n" + Archive_Main.xpath("//*[@id='hauptbereich']/div[3]/p")[0].text_content()

		if ((sender.itemTitle == "Computer-ABC")):

			SUMMARY = SUMMARY.encode('Latin-1').decode('utf-8').encode('Latin-1').decode('utf-8')

		elif ((sender.itemTitle == "News")):
			SUMMARY = SUMMARY.decode('utf-8')

		else:
			SUMMARY = SUMMARY.encode('Latin-1').decode('utf-8')

	else:
		SUMMARY = Archive_Main.xpath("//*[@id='hauptbereich']/div[3]/h1")[0].text_content()

		SUMMARY = SUMMARY + "\n\n" + Archive_Main.xpath("//*[@id='hauptbereich']/div[3]/p")[0].text_content()

		#ML(Topic_Main.xpath("//*[@id='hauptbereich']/div[3]/content_ad_possible/p[1]"))

		try:
			SUMMARY = SUMMARY + "\n\n" + Archive_Main.xpath("//*[@id='hauptbereich']/div[3]/content_ad_possible/p[1]")[0].text_content()

		except:
			SUMMARY = SUMMARY

		try:
			SUMMARY = SUMMARY.encode('Latin-1').decode('utf-8').encode('Latin-1').decode('utf-8')

		except:
			SUMMARY = SUMMARY.encode('Latin-1').decode('utf-8')

	Log('(PLUG-IN) <==** EXIT getArchiveDetail')

	return (SUBTITLE, SUMMARY)

def ArchiveMenu(sender, ArchiveList):

	global MainArt
	global MainThumb
	global FrontPage

	Log('(PLUG-IN) **==> ENTER Archive Menu')
	if MainThumb == None:
		MainArt         = "%s/:/resources/%s" % (PLUGIN_PREFIX, "art-default.png")
		MainThumb       = "%s/:/resources/%s" % (PLUGIN_PREFIX, "icon-default.png")

	# Get the items for the FRONT page ... all top-level menu items
	if len(FrontPage) == 0:
		FrontPage = LoadFP()

	dir = MediaContainer(art = MainArt, title1=sender.title2, title2=sender.itemTitle, viewGroup="Info")

	anzahl_shows = len(ArchiveList)

	for Show in range(anzahl_shows-2,0,-1):

		(URL,THUMB, ALT, TITEL) = ArchiveList[Show]

		#THUMB = str(THUMB)
		#localFileName = os.path.expanduser("~/" + urllib.quote_plus(THUMB) + ".jpg") #PLUG_IN_LOC + "/temp/" + urllib.quote_plus(THUMB)
		#ML(localFileName)
		#if not(os.path.isfile(localFileName)):
			#urllib.urlretrieve(THUMB, localFileName)

		# Add current SHOW to media container
		# DirectoryItem( key, title, subtitle=None, summary=None, thumb=None, art=None, **kwargs)
		dir.Append(Function(DirectoryItem(CurrentShowMenu,
						  title = TITEL,
						  subtitle= None,
						  summary = None,
						  thumb = THUMB, #Would be nice to use a DIFFERENT Thumb here
						  art= MainArt),
				    CurrentVideoURL = URL,
				    CurrentVideoTITLE = TITEL,
				    Themes = None)
			   )

	Log('(PLUG-IN) <==** EXIT Archive Menu')
	return dir



##############################################
##Utility Functions
##############################################

#def fractSec(s):

	#sec = s % 60
	#temp = (s-sec) / 60
	#min = temp % 60
	#temp = (temp - min) / 60
	#h = temp % 60
	#temp = (temp - h) / 60
	#d = temp % 24
	#temp = (temp - d) / 24
	#years = temp / 365

	#return (years, d, h, min, sec)

def getURL(URL, InstallDefault = False ):

# This function tries to get ID / PW from supplied URLs
# If needed it can also set the DEFAULT handler with these credentials
# making successive calls with no need to specify ID-PW

	global Protected
	global Username
	global Password

	Log('(PLUG-IN) **==> ENTER getURL')

	HEADER = {None:None}

	req = urllib2.Request(URL)

	try:
		Log('(PLUG-IN) Try URL: %s %s' % (URL,req))
		handle = urllib2.urlopen(req)

	except IOError, e:
		# here we *want* to fail
		pass
	else:
		# If we don't fail then the page isn't protected
		Protected = "No"
		Log('(PLUG-IN) URL is NOT protected')
		Log('(PLUG-IN) <==** EXIT getURL')
		return (URL,HEADER)

	if not hasattr(e, 'code') or e.code != 401:
		# we got an error - but not a 401 error
		Log("(PLUG-IN) This page isn't protected by authentication.")
		Log('(PLUG-IN) But we failed for another reason. %s' % (e.code))
		Log('(PLUG-IN) <==** EXIT getURL')
		return (None, None)

	authline = e.headers['www-authenticate']
	# this gets the www-authenticate line from the headers
	# which has the authentication scheme and realm in it

	authobj = re.compile(
		r'''(?:\s*www-authenticate\s*:)?\s*(\w*)\s+realm=['"]([^'"]+)['"]''',
		re.IGNORECASE)
	# this regular expression is used to extract scheme and realm
	matchobj = authobj.match(authline)

	if not matchobj:
		# if the authline isn't matched by the regular expression
		# then something is wrong
		Log('(PLUG-IN) The authentication header is badly formed.')
		Log('(PLUG-IN) Authline: %s' % (authline))
		Protected = "Yes"
		Log('(PLUG-IN) <==** EXIT getURL')
		return (None, None)

	scheme = matchobj.group(1)
	REALM = matchobj.group(2)
	# here we've extracted the scheme
	# and the realm from the header
	if scheme.lower() != 'basic':
		Log('(PLUG-IN) This function only works with BASIC authentication.')
		Protected = "Yes"
		Log('(PLUG-IN) <==** EXIT getURL')
		return (None, None)

	if InstallDefault:

		# Create an OpenerDirector with support for Basic HTTP Authentication...
		auth_handler = urllib2.HTTPBasicAuthHandler()
		auth_handler.add_password(realm=REALM,
					  uri=URL,
					  user=Username,
					  passwd=Password)
		opener = urllib2.build_opener(auth_handler)
		# ...and install it globally so it can be used with urlopen.
		urllib2.install_opener(opener)

		# All OK :-)
		Protected = "Yes"
		Log('(PLUG-IN) ### Alles Ready ! via default Opener###')
		Log('(PLUG-IN) <==** EXIT getURL')
		return (URL, HEADER)

	base64string = base64.encodestring('%s:%s' % (Username, Password))[:-1]
	authheader = "Basic %s" % base64string
	req.add_header("Authorization", authheader)
	HEADER = {"Authorization": authheader}

	try:
		handle = urllib2.urlopen(req)
	except IOError, e:
		# here we shouldn't fail if the username/password is right
		Log("(PLUG-IN) It looks like the username or password is wrong.")
		Protected = "Yes"
		Log('(PLUG-IN) <==** EXIT getURL')
		return (None, None)

	# All OK :-)
	Protected = "Yes"

	Log('(PLUG-IN) <==** EXIT getURL')
	return (req,HEADER)

#def wochentag(urldate):
## Exctract DATE from Video Item

	#split = urldate.split('=')
	#wd = split[1]

	#if wd == "http://www.compiz.de/":

		#wd = ""

	#return wd

#def fixURL(url):
## This will ENCODE an url to get rid of e.g. spaces in between.

	#try:
		#tempstr = RIGHT[0].split(':')
		#url = tempstr[0] + ':' + urllib.quote(tempstr[1])

		#return url
	#except:
		#return urllib.quote(url)

#def cleanstring(mystr):

	#str=mystr.replace("\\n", " ")
	#while str.find("  ")>=0:
		#str=str.replace("  ", " ")
	#if str.startswith(" "):
		#str=str[1:]
	#if str.endswith(" "):
		#str=str[:-1]
	#return str

#def cleanGerman(mystr, decodec = 'utf-8', encodec = 'Latin-1'):
## This is an attempt to get rid of " &auml; " etc within a string
## Still working on it ... any help appreicated.

	#if encodec <> None:
		#mystr = mystr.encode(encodec)
	#Log('******%s' % mystr)

	#mystr = mystr.replace('&auml;',"ä") # öüß
	#mystr = mystr.replace('&ouml;',"ö") # ß
	#mystr = mystr.replace('&uuml;',"ü") # öü
	#mystr = mystr.replace('&szlig;',"ß") # öüß
	#mystr = mystr.replace('&Auml;',"Ä") # öüß
	#mystr = mystr.replace('&Ouml;',"Ö") # ß
	#mystr = mystr.replace('&Uuml;',"Ü") # öü
	#mystr = mystr.replace('&#034;','"') # öüß
	#mystr = mystr.replace('\u00E9','é')
	#mystr = mystr.replace('&#039;',"'") # öüß
	#mystr = mystr.replace('&amp;','&')

	#if decodec <> None:
		#mystr = mystr.decode(decodec)
	#Log('******%s' % mystr)
	#return mystr

def cleanHTML(text, skipchars=[], extra_careful=1):
# This is an attempt to get rid of " &auml; " etc within a string
# Still working on it ... any help appreicated.

	entitydefs_inverted = {}

	for k,v in entitydefs.items():
		entitydefs_inverted[v] = k

	_badchars_regex = re.compile('|'.join(entitydefs.values()))
	_been_fixed_regex = re.compile('&\w+;|&#[0-9]+;')

	# if extra_careful we don't attempt to do anything to
	# the string if it might have been converted already.
	if extra_careful and _been_fixed_regex.findall(text):
		return text

	if type(skipchars) == type('s'):
		skipchars = [skipchars]

	keyholder= {}
	for x in _badchars_regex.findall(text):
		if x not in skipchars:
			keyholder[x] = 1
	text = text.replace('&','&amp;')
	text = text.replace('\x80', '&#8364;')
	for each in keyholder.keys():
		if each == '&':
			continue

		better = entitydefs_inverted[each]
		if not better.startswith('&#'):
			better = '&%s;'%entitydefs_inverted[each]

		text = text.replace(each, better)
	return text

#def DurationToInt(mystr):
## This converts "00:00" to an INT with 1000ths of seconds for PLEX

	#Duration = 0
	#sekunden = 0
	#minuten = 0
	#stunden = 0
	#tage = 0

	#Multiplier = 1000

	## Transform a time string of "xx:xx:xx" format into a INT showing miliseconds
	#str=mystr.split(':')
	#try:
		#sekunden = str.pop()

	#except:
		#Duration = 0
		#return Duration

	#try:
		#minuten = str.pop()

	#except:
		#Duration = int(sekunden)  * Multiplier
		#return Duration

	#try:
		#stunden = str.pop()

	#except:
		#Duration = int(minuten) * 60 * Multiplier + int(sekunden)  * Multiplier
		#return Duration

	#try:
		#tage = str.pop()

	#except:
		#Duration = int(stunden) * 60 * 60 * Multiplier + int(minuten) * 60 * Multiplier + int(sekunden)  * Multiplier
		#return Duration

	#Duration = int(tage) * 24 *60 * 60 * Multiplier + int(stunden) * 60 * 60 * Multiplier + int(minuten) * 60 * Multiplier + int(sekunden)  * Multiplier
	#return Duration

#def GetValues(key, doc, ende = None):
	##Look for values within a document and returns a LIST of items

	#inhalt = []

	#temp = doc.split(key)

	#anzahl = len(temp)

	#for item in range(0,anzahl):

		#try:
			#if ende == None:
				#ende = '>'

			#value = temp[item].split(ende)[0]

			#inhalt = inhalt + [value] #.append(value)

		#except:
			#Log('None')
			#None

	#tag = inhalt

	#return  inhalt

#def makeUnicode(item):

	#if isinstance(item, str):
		#ergebnis = unicode(item,'Latin-1')

	#return item

def ML(Target):

	Log('***********************************************')
	temp = Target
	try:
		temp = tostring(temp)

	except:
		temp = temp

	try:
		Log('TYPE: %s' % type(temp))
	except:
		Log('TYPE: Error')

	try:
		Log('LEN: %d' %len(temp))
	except:
		Log('LEN: Error')

	try:
		Log('CONTENT: %s' % temp)
	except:
		Log('CONTENT: Error')

	Log('***********************************************')

	return
