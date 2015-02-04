################################################################
# File: ch.py
# Title: Chatango Library
# Author: Lumirayz/Lumz <lumirayz@gmail.com>
# Version: 1.3
# Description:
#  An event-based library for connecting to one or multiple Chatango rooms, has
#  support for several things including: messaging, message font,
#  name color, deleting, banning, recent history, 2 userlist modes,
#  flagging, avoiding flood bans, detecting flags.
################################################################

################################################################
# License
################################################################
# Copyright 2011 Lumirayz
# This program is distributed under the terms of the GNU GPL.

################################################################
# Imports
################################################################
import socket
import threading
import time
import random
import re
import sys
import select
import os


################################################################
# Python 2 compatibility
################################################################
if sys.version_info[0] < 3:
        class urllib:
                parse = __import__("urllib")
                request = __import__("urllib2")
        input = raw_input
        import codecs
else:
        import urllib.request
        import urllib.parse

################################################################
# Constants
################################################################
Userlist_Recent = 1
Userlist_All    = 0

BigMessage_Multiple = 0
BigMessage_Cut      = 1

class Struct:
        def __init__(self, **entries):
                self.__dict__.update(entries)
################################################################
# Tagserver stuff
################################################################
specials = {'mitvcanal': 56, 'magicc666': 22, 'livenfree': 18, 'eplsiite': 56, 'soccerjumbo2': 21, 'bguk': 22, 'animachat20': 34, 'pokemonepisodeorg': 55, 'sport24lt': 56, 'mywowpinoy': 5, 'phnoytalk': 21, 'flowhot-chat-online': 12, 'watchanimeonn': 26, 'cricvid-hitcric-': 51, 'fullsportshd2': 18, 'chia-anime': 12, 'narutochatt': 52, 'ttvsports': 56, 'futboldirectochat': 22, 'portalsports': 18, 'stream2watch3': 56, 'proudlypinoychat': 51, 'ver-anime': 34, 'iluvpinas': 53, 'vipstand': 21, 'eafangames': 56, 'worldfootballusch2': 18, 'soccerjumbo': 21, 'myfoxdfw': 22, 'animelinkz': 20, 'rgsmotrisport': 51, 'bateriafina-8': 8, 'as-chatroom': 10, 'dbzepisodeorg': 12, 'tvanimefreak': 54, 'watch-dragonball': 19, 'narutowire': 10, 'leeplarp': 27}
tsweights = [['5', 75], ['6', 75], ['7', 75], ['8', 75], ['16', 75], ['17', 75], ['18', 75], ['9', 95], ['11', 95], ['12', 95], ['13', 95], ['14', 95], ['15', 95], ['19', 110], ['23', 110], ['24', 110], ['25', 110], ['26', 110], ['28', 104], ['29', 104], ['30', 104], ['31', 104], ['32', 104], ['33', 104], ['35', 101], ['36', 101], ['37', 101], ['38', 101], ['39', 101], ['40', 101], ['41', 101], ['42', 101], ['43', 101], ['44', 101], ['45', 101], ['46', 101], ['47', 101], ['48', 101], ['49', 101], ['50', 101], ['52', 110], ['53', 110], ['55', 110], ['57', 110], ['58', 110], ['59', 110], ['60', 110], ['61', 110], ['62', 110], ['63', 110], ['64', 110], ['65', 110], ['66', 110], ['68', 95], ['71', 116], ['72', 116], ['73', 116], ['74', 116], ['75', 116], ['76', 116], ['77', 116], ['78', 116], ['79', 116], ['80', 116], ['81', 116], ['82', 116], ['83', 116], ['84', 116]]
def getServer(group):
        try:
                sn = specials[group]
        except KeyError:
                group = group.replace("_", "q")
                group = group.replace("-", "q")
                fnv = float(int(group[0:min(5, len(group))], 36))
                lnv = group[6: (6 + min(3, len(group) - 5))]
                if(lnv):
                        lnv = float(int(lnv, 36))
                        if(lnv <= 1000):
                                lnv = 1000
                else:
                        lnv = 1000
                num = (fnv % lnv) / lnv
                maxnum = sum(map(lambda x: x[1], tsweights))
                cumfreq = 0
                sn = 0
                for wgt in tsweights:
                        cumfreq += float(wgt[1]) / maxnum
                        if(num <= cumfreq):
                                sn = int(wgt[0])
                                break
        return "s" + str(sn) + ".chatango.com"

################################################################
# Uid
################################################################
def genUid():
        return str(random.randrange(10 ** 15, 10 ** 16))

################################################################
# Message stuff
################################################################
def clean_message(msg):
        n = re.search("<n(.*?)/>", msg)
        if n: n = n.group(1)
        f = re.search("<f(.*?)>", msg)
        if f: f = f.group(1)
        msg = re.sub("<n.*?/>", "", msg)
        msg = re.sub("<f.*?>", "", msg)
        msg = strip_html(msg)
        msg = msg.replace("&lt;", "<")
        msg = msg.replace("&gt;", ">")
        msg = msg.replace("&quot;", "\"")
        msg = msg.replace("&apos;", "'")
        msg = msg.replace("&amp;", "&")
        return msg, n, f

def strip_html(msg):
        """Strip HTML."""
        li = msg.split("<")
        if len(li) == 1:
                return li[0]
        else:
                ret = list()
                for data in li:
                        data = data.split(">", 1)
                        if len(data) == 1:
                                ret.append(data[0])
                        elif len(data) == 2:
                                ret.append(data[1])
                return "".join(ret)

def parseNameColor(n):
        """This just returns its argument, should return the name color."""
        #probably is already the name
        return n

def parseFont(f):
        """Parses the contents of a f tag and returns color, face and size."""
        #' xSZCOL="FONT"'
        try: #TODO: remove quick hack
                sizecolor, fontface = f.split("=", 1)
                sizecolor = sizecolor.strip()
                size = int(sizecolor[1:3])
                col = sizecolor[3:6]
                if col == "": col = None
                face = f.split("\"", 2)[1]
                return col, face, size
        except:
                return None, None, None

################################################################
# Anon id
################################################################
def getAnonId(n, ssid):
        """Gets the anon's id."""
        if n == None: n = "5504"
        try:
                return "".join(list(
                        map(lambda x: str(x[0] + x[1])[-1], list(zip(
                                list(map(lambda x: int(x), n)),
                                list(map(lambda x: int(x), ssid[4:]))
                        )))
                ))
        except ValueError:
                return "NNNN"
################################################################
# PM Auth
################################################################
def _getAuth(name, password):
        auth = urllib.request.urlopen("http://chatango.com/login",
                                      urllib.parse.urlencode({
                                              "user_id": name,
                                              "password": password,
                                              "storecookie": "on",
                                              "checkerrors": "yes"}).encode()
                                      ).getheader("Set-Cookie")
        try:
                return re.search("auth.chatango.com=(.*?);", auth).group(1)
        except:
                return None
################################################################
# PM class
################################################################
class PM:
        """Manages a connection with Chatango PM."""
        ####
        # Init
        ####
        def __init__(self, mgr):
                self._connected = False
                self._mgr = mgr
                self.idle = 1
                self._auid = None
                self._blocklist = set()
                self._unblocklist = set()
                self._contacts = set()
                self._wlock = False
                self._premium = False
                self._firstCommand = True
                self._wbuf = b""
                self._wlockbuf = b""
                self._rbuf = b""
                self._pingTask = None
                self._connect()
                if sys.version_info[0] < 3 and sys.platform.startswith("win"):
                        self.unicodeCompat = False
                else:
                        self.unicodeCompat = True
        ####
        # Connections
        ####
        def _connect(self):
                self._wbuf = b""
                self._sock = socket.socket()
                self._sock.connect((self._mgr._PMHost, self._mgr._PMPort))
                self._sock.setblocking(False)
                self._firstCommand = True
                if not self._auth(): return
                self._pingTask = self.mgr.setInterval(self._mgr._pingDelay, self.ping)
                self._connected = True
        def _auth(self):
                self._auid = _getAuth(self._mgr.name, self._mgr.password)
                if self._auid == None:
                        self._sock.close()
                        self._callEvent("onLoginFail")
                        self._sock = None
                        return False
                self._sendCommand("tlogin", self._auid, "2")
                self._setWriteLock(True)
                return True
        def disconnect(self):
                self._disconnect()
                self._callEvent("onPMDisconnect")
        def _disconnect(self):
                self._connected = False
                self._sock.close()
                self._sock = None
        ####
        # Feed
        ####
        def _feed(self, data):
                """
                Feed data to the connection.
                
                @type data: bytes
                @param data: data to be fed
                """
                self._rbuf += data
                while self._rbuf.find(b"\x00") != -1:
                        data = self._rbuf.split(b"\x00")
                        for food in data[:-1]:
                                if self.unicodeCompat:
                                        self._process(food.decode().rstrip("\r\n")) #numnumz ;3
                                else:
                                        self._process(food.decode(errors="replace").rstrip("\r\n"))
                        self._rbuf = data[-1]
        def _process(self, data):
                """
                Process a command string.
                
                @type data: str
                @param data: the command string
                """
                self._callEvent("onRaw", data)
                data = data.split(":")
                cmd, args = data[0], data[1:]
                func = "rcmd_" + cmd
                if hasattr(self, func):
                        getattr(self, func)(args)
        ####
        # Properties
        ####
        def getManager(self): return self._mgr
        def getContacts(self): return self._contacts
        def getBlocklist(self): return self._blocklist
        def getUnblocklist(self): return self._unblocklist
        mgr = property(getManager)
        contacts = property(getContacts)
        blocklist = property(getBlocklist)
        unblocklist = property(getUnblocklist)
        ####
        # Received Commands
        ####
        def rcmd_OK(self, args):
                self._setWriteLock(False)
                self._sendCommand("wl")
                self._sendCommand("getblock")
                self._sendCommand("getpremium", "1")
                self.setIdle()
                self._callEvent("onPMConnect")
        def rcmd_block_list(self, args):
                self._blocklist = set()
                for name in args:
                        if name == "": continue
                        self._blocklist.add(User(name))
        def rcmd_unblock_list(self, args):
                self._unblocklist = set()
                for name in args:
                        if name == "": continue
                        self._unblocklist.add(User(name))
        def rcmd_DENIED(self, args):
                self._disconnect()
                self._callEvent("onLoginFail")
        def rcmd_msg(self, args):
                user = User(args[0])
                body = strip_html(":".join(args[5:]))
                self._callEvent("onPMMessage", user, body)
        def rcmd_connect(self, args):
                        self._callEvent("onPMConnect1", User(args[0]), args[1], args[2])
        def rcmd_premium(self, args):
                if float(args[1]) > time.time():
                        self._premium = True
                        if self._mgr.user._mbg: self.setBgMode(1)
                        if self._mgr.user._mrec: self.setRecordingMode(1)
                else:
                        self._premium = False
        def rcmd_kickingoff(self, args):
                self.disconnect()
        ####
        # Commands
        ####
        def ping(self):
                self._sendCommand("")
                self._callEvent("onPMPing")
                if self.idle != 0:
                        self.setIdle()
                        self.idle = 0
        def message(self, user, msg):
                self.setActive()
                self.idle = 1
                msg = msg.replace("<b>", "<B>").replace("<u>", "<U>").replace("<i>", "<I>").replace("</b>", "</B>").replace("</u>", "</U>").replace("</i>", "</I>")
                self._sendCommand("msg", user.name, "<n%s/><m v=\"1\"><g xs0=\"1\"><g x%ss%s=\"0\">%s</g></g></m>" % (self._mgr.user.nameColor, self._mgr.user.fontSize, self._mgr.user.fontColor, msg))
        def test(self, user):
                self._sendCommand("connect", user.name)
        def addContact(self, user):
                if user not in self._contacts:
                        self._sendCommand("wladd", user.name)
                        self._contacts.add(user)
                        self._callEvent("onPMContactAdd", user)
        def goIdle(self, args):
                self._sendCommand("idle", str(args))
        def removeContact(self, user):
                if user in self._contacts:
                        self._sendCommand("wldelete", user.name)
                        self._contacts.remove(user)
                        self._callEvent("onPMContactRemove", user)
        def block(self, user):
                if user not in self._blocklist:
                        self._sendCommand("block", user.name, user.name, "S")
                        self._blocklist.add(user)
                        self._callEvent("onPMBlock", user)
        def unblock(self, user):
                if user in self._blocklist:
                        self._sendCommand("unblock", user.name)
                        self._blocklist.remove(user)
                        self._callEvent("onPMUnblock", user)
        def setBgMode(self, mode):
                self._sendCommand("msgbg", str(mode))
        def setRecordingMode(self, mode):
                self._sendCommand("msgmedia", str(mode))
        def setIdle(self):
                self._sendCommand("idle:0")
        def setActive(self):
                self._sendCommand("idle:1")
        ####
        # Util
        ####
        def _callEvent(self, evt, *args, **kw):
                getattr(self.mgr, evt)(self, *args, **kw)
                self.mgr.onEventCalled(self, evt, *args, **kw)
        def _write(self, data):
                if self._wlock:
                        self._wlockbuf += data
                else:
                        self.mgr._write(self, data)
        def _setWriteLock(self, lock):
                self._wlock = lock
                if self._wlock == False:
                        self._write(self._wlockbuf)
                        self._wlockbuf = b""
        def _sendCommand(self, *args):
                if self._firstCommand:
                        terminator = b"\x00"
                        self._firstCommand = False
                else:
                        terminator = b"\r\n\x00"
                self._write(":".join(args).encode() + terminator)
################################################################
# Room class
################################################################
class Room:
        """Manages a connection with a Chatango room."""
        ####
        # Init
        ####
        def __init__(self, room, uid = None, server = None, port = None, mgr = None):
                # Basic stuff
                self._name = room
                self._server = server or getServer(room)
                self._port = port or 443
                self._mgr = mgr
                # Under the hood
                self._connected = False
                self._reconnecting = False
                self._uid = uid or genUid()
                self._rbuf = b""
                self._wbuf = b""
                self._wlockbuf = b""
                self._owner = None
                self._mods = list()
                self._mqueue = dict()
                self._history = list()
                self._userlist = list()
                self._firstCommand = True
                self._connectAmmount = 0
                self._premium = False
                self._userCount = 0
                self._pingTask = None
                self._botname = None
                self._currentname = None
                self._users = dict()
                self._msgs = dict()
                self._wlock = False
                self._silent = False
                self._banlist = dict()
                self._unbanlist = dict()
                if sys.version_info[0] < 3 and sys.platform.startswith("win"):
                        self.unicodeCompat = False
                else:
                        self.unicodeCompat = True
                # Inited vars
                if self._mgr: self._connect()
        ####
        # User and Message management
        ####
        def getMessage(self, mid):
                return self._msgs.get(mid)
        def createMessage(self, msgid, **kw):
                if msgid not in self._msgs:
                        msg = Message(msgid = msgid, **kw)
                        self._msgs[msgid] = msg
                else:
                        msg = self._msgs[msgid]
                return msg
        ####
        # Connect/disconnect
        ####
        def _connect(self):
                """Connect to the server."""
                self._sock = socket.socket()
                self._sock.connect((self._server, self._port))
                self._sock.setblocking(False)
                self._firstCommand = True
                self._wbuf = b""
                self._auth()
                self._pingTask = self.mgr.setInterval(self.mgr._pingDelay, self.ping)
                if not self._reconnecting: self.connected = True
        def reconnect(self):
                """Reconnect."""
                self._reconnect()
        def _reconnect(self):
                """Reconnect."""
                self._reconnecting = True
                if self.connected:
                        self._disconnect()
                self._uid = genUid()
                self._connect()
                self._reconnecting = False
        def disconnect(self):
                """Disconnect."""
                self._disconnect()
                self._callEvent("onDisconnect")
        def _disconnect(self):
                """Disconnect from the server."""
                if not self._reconnecting: self.connected = False
                for user in self._userlist:
                        user.clearSessionIds(self)
                self._userlist = list()
                self._pingTask.cancel()
                self._sock.close()
                if not self._reconnecting: del self.mgr._rooms[self.name]
        def _auth(self):
                """Authenticate."""
                if self.mgr.name and self.mgr.password:
                        self._sendCommand("bauth", self.name, self._uid, self.mgr.name, self.mgr.password)
                        self._currentname = self.mgr.name
                else: self._sendCommand("bauth", self.name)
                self._setWriteLock(True)
        ####
        # Properties
        ####
        def getBotName(self):
                if self.mgr.name and self.mgr.password: return self.mgr.name
                elif self.mgr.name and self.mgr.password == None: return "#"+self.mgr.name
                elif self.mgr.name == None: return self._botname
        def getCurrentname(self): return self._currentname
        def getName(self): return self._name
        def getManager(self): return self._mgr
        def getUserlist(self, mode = None, unique = None, memory = None):
                ul = None
                if mode == None: mode = self.mgr._userlistMode
                if unique == None: unique = self.mgr._userlistUnique
                if memory == None: memory = self.mgr._userlistMemory
                if mode == Userlist_Recent:
                        ul = map(lambda x: x.user, self._history[-memory:])
                elif mode == Userlist_All:
                        ul = self._userlist
                if unique:
                        return list(set(ul))
                else:
                        return ul
        def getUserNames(self):
                ul = self.userlist
                return list(map(lambda x: x.name, ul))
        def getUser(self): return self.mgr.user
        def getOwner(self): return self._owner
        def getOwnerName(self): return self._owner.name
        def getMods(self):
                newset = list()
                for mod in self._mods:
                        newset.append(mod)
                return newset
        def getModNames(self):
                mods = self.getMods()
                return [x.name.split(',')[0] for x in mods]
        def getUserCount(self): return self._userCount
        def getSilent(self): return self._silent
        def setSilent(self, val): self._silent = val
        def getBanlist(self): return list(self._banlist.keys())
        def getUnbanlist(self): return [[record["target"], record["src"]] for record in self._unbanlist.values()]
        name = property(getName)
        botname = property(getBotName)
        currentname = property(getCurrentname)
        mgr = property(getManager)
        userlist = property(getUserlist)
        usernames = property(getUserNames)
        user = property(getUser)
        owner = property(getOwner)
        ownername = property(getOwnerName)
        mods = property(getMods)
        modnames = property(getModNames)
        usercount = property(getUserCount)
        silent = property(getSilent, setSilent)
        banlist = property(getBanlist)
        unbanlist = property(getUnbanlist)
        ####
        # Feed/process
        ####
        def _feed(self, data):

                self._rbuf += data
                while self._rbuf.find(b"\x00") != -1:
                        data = self._rbuf.split(b"\x00")
                        for food in data[:-1]:
                                if self.unicodeCompat:
                                        self._process(food.decode().rstrip("\r\n")) #numnumz ;3
                                else:
                                        self._process(food.decode(errors="replace").rstrip("\r\n"))
                        self._rbuf = data[-1]
        def _process(self, data):
                self._callEvent("onRaw", data)
                data = data.split(":")
                cmd, args = data[0], data[1:]
                func = "rcmd_" + cmd
                if hasattr(self, func):
                        getattr(self, func)(args)
        ####
        # Received Commands
        ####
        def rcmd_ok(self, args):
                if args[2] == "N" and self.mgr.password == None and self.mgr.name == None:
                        n = args[4].rsplit('.', 1)[0]
                        n = n[-4:]
                        aid = args[1][0:8]
                        pid = "!anon" + getAnonId(n, aid)
                        self._botname = pid
                        self._currentname = pid
                        self.user._nameColor = n
                elif args[2] == "N" and self.mgr.password == None:
                        self._sendCommand("blogin", self.mgr.name)
                        self._currentname = self.mgr.name
                elif args[2] != "M": #unsuccesful login
                        self._callEvent("onLoginFail")
                        self.disconnect()
                self._owner = User(args[0])
                self._uid = args[1]
                self._aid = args[1][4:8]
                self._mods = set(map(lambda x: User(x), args[6].split(";")))
                self._i_log = list()
        def rcmd_denied(self, args):
                self._disconnect()
                self._callEvent("onConnectFail")
        def rcmd_inited(self, args):
                self._sendCommand("g_participants", "start")
                self._sendCommand("getpremium", "1")
                self._sendCommand("getratelimit")
                self.requestUnbanlist()
                self.requestBanlist()
                if self._connectAmmount == 0:
                        self._callEvent("onConnect")
                        for msg in reversed(self._i_log):
                                user = msg.user
                                self._callEvent("onHistoryMessage", user, msg)
                                self._addHistory(msg)
                        del self._i_log
                else:
                        self._callEvent("onReconnect")
                self._connectAmmount += 1
                self._setWriteLock(False)
        def rcmd_premium(self, args):
                if float(args[1]) > time.time():
                        self._premium = True
                        if self.user._mbg: self.setBgMode(1)
                        if self.user._mrec: self.setRecordingMode(1)
                        self._mgr.bgtime = args[1]
                else:
                        self._premium = False
        def rcmd_mods(self, args):
                modnames = args
                mods = set(map(lambda x: User(x), modnames))
                premods = self._mods
                for user in mods - premods: #modded
                        self._mods.add(user)
                        self._callEvent("onModAdd", user)
                for user in premods - mods: #demodded
                        self._mods.remove(user)
                        self._callEvent("onModRemove", user)
                self._callEvent("onModChange")
        def rcmd_b(self, args):
                mtime = float(args[0])
                puid = args[3]
                ip = args[6]
                name = args[1]
                rawmsg = ":".join(args[9:]) if self.unicodeCompat else ":".join(args[9:]).encode("windows-1252","ignore").decode("windows-1252")
                msg, n, f = clean_message(rawmsg)
                if name == "":
                        nameColor = None
                        name = "#" + args[2]
                        if name == "#":
                                name = "!anon" + getAnonId(n, puid)
                else:
                        if n: nameColor = parseNameColor(n)
                        else: nameColor = None
                i = args[5]
                unid = args[4]
                #Create an anonymous message and queue it because msgid is unknown.
                if f: fontColor, fontFace, fontSize = parseFont(f)
                else: fontColor, fontFace, fontSize = None, None, None          
                msg = Message(
                        time = mtime,
                        user = User(name),
                        body = msg,
                        raw = rawmsg,
                        uid = puid,
                        ip = ip,
                        nameColor = nameColor,
                        fontColor = fontColor,
                        fontFace = fontFace,
                        fontSize = fontSize,
                        unid = unid,
                        room = self
                )
                self._mqueue[i] = msg
        def rcmd_u(self, args):
                temp = Struct(**self._mqueue)
                if hasattr(temp, args[0]):
                        msg = getattr(temp, args[0])
                        if msg.user != self.user:
                                msg.user._fontColor = msg.fontColor
                                msg.user._fontFace = msg.fontFace
                                msg.user._fontSize = msg.fontSize
                                msg.user._nameColor = msg.nameColor
                        del self._mqueue[args[0]]
                        msg.attach(self, args[1])
                        self._addHistory(msg)
                        self._callEvent("onMessage", msg.user, msg)
        def rcmd_i(self, args):
                mtime = float(args[0])
                puid = args[3]
                ip = args[6]
                if ip == "": ip = None
                name = args[1]
                rawmsg = ":".join(args[9:])
                msg, n, f = clean_message(rawmsg)
                msgid = args[5]
                if name == "":
                        nameColor = None
                        name = "#" + args[2]
                        if name == "#":
                                name = "!anon" + getAnonId(n, puid)
                else:
                        if n: nameColor = parseNameColor(n)
                        else: nameColor = None
                if f: fontColor, fontFace, fontSize = parseFont(f)
                else: fontColor, fontFace, fontSize = None, None, None
                msg = self.createMessage(
                        msgid = msgid,
                        time = mtime,
                        user = User(name),
                        body = msg,
                        raw = rawmsg,
                        ip = args[6],
                        unid = args[4],
                        nameColor = nameColor,
                        fontColor = fontColor,
                        fontFace = fontFace,
                        fontSize = fontSize,
                        room = self
                )
                if msg.user != self.user:
                        msg.user._fontColor = msg.fontColor
                        msg.user._fontFace = msg.fontFace
                        msg.user._fontSize = msg.fontSize
                        msg.user._nameColor = msg.nameColor
                self._i_log.append(msg)
        def rcmd_g_participants(self, args):
                args = ":".join(args)
                args = args.split(";")
                for data in args:
                        data = data.split(":")
                        name = data[3].lower()
                        if name == "none": continue
                        user = User(
                                name = name,
                                room = self
                        )
                        user.addSessionId(self, data[0])
                        self._userlist.append(user)
        def rcmd_participant(self, args):
                if args[0] == "0": #leave
                        name = args[3].lower()
                        if name == "none": return
                        user = User(
                                name = name,
                                room = self
                        )
                        user.removeSessionId(self, args[1])
                        self._userlist.remove(user)
                        if user not in self._userlist or not self.mgr._userlistEventUnique:
                                self._callEvent("onLeave", user)
                else: #join
                        name = args[3].lower()
                        if name == "none": return
                        user = User(
                                name = name,
                                room = self
                        )
                        user.addSessionId(self, args[1])
                        if user not in self._userlist: doEvent = True
                        else: doEvent = False
                        self._userlist.append(user)
                        if doEvent or not self.mgr._userlistEventUnique:
                                self._callEvent("onJoin", user)
        def rcmd_show_fw(self, args):
                self._callEvent("onFloodWarning")
        def rcmd_show_tb(self, args):
                self._callEvent("onFloodBan")
        def rcmd_tb(self, args):
                self._callEvent("onFloodBanRepeat")
        def rcmd_delete(self, args):
                msg = self.getMessage(args[0])
                if msg:
                        if msg in self._history:
                                self._history.remove(msg)
                                self._callEvent("onMessageDelete", msg.user, msg)
                                msg.detach()
        def rcmd_deleteall(self, args):
                for msgid in args:
                        self.rcmd_delete([msgid])
        def rcmd_n(self, args):
                self._userCount = int(args[0], 16)
                self._callEvent("onUserCountChange")
        def rcmd_blocklist(self, args):
                self._banlist = dict()
                sections = ":".join(args).split(";")
                for section in sections:
                        params = section.split(":")
                        if len(params) != 5: continue
                        if params[2] == "": continue
                        user = User(params[2])
                        self._banlist[user] = {
                                "unid":params[0],
                                "ip":params[1],
                                "target":user,
                                "time":float(params[3]),
                                "src":User(params[4])
                        }
                self._callEvent("onBanlistUpdate")
        def rcmd_unblocklist(self, args):
                self._unbanlist = dict()
                sections = ":".join(args).split(";")
                for section in sections:
                        params = section.split(":")
                        if len(params) != 5: continue
                        if params[2] == "": continue
                        user = User(params[2])
                        self._unbanlist[user] = {
                                "unid":params[0],
                                "ip":params[1],
                                "target":user,
                                "time":float(params[3]),
                                "src":User(params[4])
                        }
                self._callEvent("onUnbanlistUpdate")
        def rcmd_blocked(self, args):
                if args[2] == "": return
                target = User(args[2])
                user = User(args[3])
                self._banlist[target] = {"unid":args[0], "ip":args[1], "target":target, "time":float(args[4]), "src":user}
                self._callEvent("onBan", user, target)
                self.requestBanlist()
        def rcmd_unblocked(self, args):
                if args[2] == "": return
                target = User(args[2])
                user = User(args[3])
                self._unbanlist[user] = {"unid":args[0], "ip":args[1], "target":target, "time":float(args[4]), "src":user}
                self._callEvent("onUnban", user, target)
                self.requestUnbanlist()
        def rcmd_clearall(self, args):
                self._callEvent("onClearAll")
        ####
        # Commands
        ####
        def login(self, NAME, PASS = None):
                NAME = NAME.title()
                if PASS: self._sendCommand("blogin", NAME, PASS)
                else: self._sendCommand("blogin", NAME)
                self._currentname = NAME
        def logout(self):
                self._sendCommand("blogout")
                self._currentname = self._botname
        def ping(self):
                """Send a ping."""
                self._sendCommand("")
                self._callEvent("onPing")
        def message(self, msg, html = True):
                if not html:
                        msg = msg.replace("<", "&lt;").replace(">", "&gt;")
                if len(msg) > self.mgr._maxLength:
                        if self.mgr._tooBigMessage == BigMessage_Cut:
                                self.message(msg[:self.mgr._maxLength], html = html)
                        elif self.mgr._tooBigMessage == BigMessage_Multiple:
                                while len(msg) > 0:
                                        sect = msg[:self.mgr._maxLength]
                                        msg = msg[self.mgr._maxLength:]
                                        self.message(sect, html = html)
                        return
                msg = "<n" + self.user.nameColor + "/>" + msg
                if self._currentname != None and not self._currentname.startswith('!anon'):
                        msg = "<f x%0.2i%s=\"%s\">" %(self.user.fontSize, self.user.fontColor, self.user.fontFace) + msg
                if not self._silent:
                        self._sendCommand("bmsg:p1jr", msg)
        def setBgMode(self, mode):
                self._sendCommand("msgbg", str(mode))
        def setRecordingMode(self, mode):
                self._sendCommand("msgmedia", str(mode))
        def set_bg(self, color3x):
                '''Set your background. The color must be an html color code.
                The image parameter takes a boolean to turn the picture off or on.
                Transparency is a float less than one or an integer between 1-100.'''
                if self._premium:
                        # Get the original settings
                        letter1 = self.mgr.user.name[0]
                        letter2 = self.mgr.user.name[1] if len(self.mgr.user.name) > 1 else self.mgr.user.name[0]
                        data = urllib.request.urlopen("http://fp.chatango.com/profileimg/%s/%s/%s/msgbg.xml" % (letter1, letter2, self.user.name)).read().decode()
                        data = dict([x.replace('"', '').split("=") for x in re.findall('(\w+=".*?")', data)[1:]])
                        # Add the necessary shiz
                        data["p"] = self.mgr.password
                        data["lo"] = self.mgr.user.name
                        if color3x: data["bgc"] = color3x
                        # Send the request
                        data = urllib.parse.urlencode(data)
                        try:
                                urllib.request.urlopen("http://chatango.com/updatemsgbg?bgc=%s&hasrec=0&p=%s&isvid=0&lo=%s&align=br&bgalp=100&useimg=1&ialp=50&tile=1" % (color3x, self.mgr.password, self.mgr.user.name)).read()
                        except:
                                return False
                        else:
                                return True
        def addMod(self, user):
                if self.getLevel(User(self.currentname)) == 2:
                        self._sendCommand("addmod", user.name)
        def removeMod(self, user):
                if self.getLevel(User(self.currentname)) == 2:
                        self._sendCommand("removemod", user.name)
        def flag(self, user):
                msg = self.getLastMessage(user)
                if msg:
                        self._sendCommand("g_flag", msg.msgid)
                        return True
                return False
        def delete(self, user):
                if self.getLevel(User(self.currentname)) > 0:
                        msg = self.getLastMessage(user)
                        if msg:
                                self._sendCommand("delmsg", msg.msgid)
                        return True
                return False
        def clearUser(self, user):
                if self.getLevel(User(self.currentname)) > 0:
                        msg = self.getLastMessage(user)
                        unid = None
                        if msg:
                                unid = msg.unid
                        if unid:
                                if user.name[0] in ["!","#"]:
                                        self._sendCommand("delallmsg", unid, msg.ip, "")
                                else:
                                        self._sendCommand("delallmsg", unid, msg.ip, user.name)
                        return True
                return False
        def clearall(self):
                """Clear all messages. (Owner only)""" ##<---BULLSHIT! :P
                if self.getLevel(User(self.currentname)) > 0:
                        if User(self.currentname) == self._owner:
                                self._sendCommand("clearall")
                        else:
                                mArray = self._msgs.values()
                                for user in list(set([x.user for x in mArray])):
                                        msg = self.getLastMessage(user)
                                        if msg and hasattr(msg, 'unid'):
                                                self.clearUser(user)
                        return True
                return False
        def ban(self, user):
                msg = self.getLastMessage(user)
                unid = None
                if msg:
                        unid = msg.unid
                if unid:
                        if user.name[0] in ['!','#']:
                                self._sendCommand("block", unid, msg.ip, "")
                                self._sendCommand("delallmsg", unid, msg.ip, "")
                        else:
                                self._sendCommand("block", unid, msg.ip, user.name)
                                self._sendCommand("delallmsg", unid, msg.ip, user.name)
                        return True
                return False
        def requestBanlist(self):
                """Request an updated banlist."""
                self._sendCommand("blocklist", "block", "", "next", "500")
        def requestUnbanlist(self):
                """Request an updated unbanlist."""
                self._sendCommand("blocklist", "unblock", "", "next", "500")
        def unban(self, user):
                rec = self._getBanRecord(user)
                if rec:
                        self._sendCommand("removeblock", rec["unid"], rec["ip"], rec["target"].name)
                        return True
                else:
                        return False
        ####
        # Util
        ####
        def _getBanRecord(self, user):
                if user in self._banlist:
                        return self._banlist[user]
                return None
        def _getUnbanRecord(self, user):
                if user in self._unbanlist:
                        return self._unbanlist[user]
                return None
        def _callEvent(self, evt, *args, **kw):
                getattr(self.mgr, evt)(self, *args, **kw)
                self.mgr.onEventCalled(self, evt, *args, **kw)
        def _write(self, data):
                if self._wlock:
                        self._wlockbuf += data
                else:
                        self.mgr._write(self, data)
        def _setWriteLock(self, lock):
                self._wlock = lock
                if self._wlock == False:
                        self._write(self._wlockbuf)
                        self._wlockbuf = b""
        def _sendCommand(self, *args):
                if self._firstCommand:
                        terminator = b"\x00"
                        self._firstCommand = False
                else:
                        terminator = b"\r\n\x00"
                self._write(":".join(args).encode() + terminator)
        def getLevel(self, user):
                if user == self._owner: return 2
                if user.name in self.modnames: return 1
                return 0
        def getLastMessage(self, user = None):
                if user:
                        try:
                                i = 1
                                while True:
                                        msg = self._history[-i]
                                        if msg.user == user:
                                                return msg
                                        i += 1
                        except IndexError:
                                return None
                else:
                        try:
                                return self._history[-1]
                        except IndexError:
                                return None
                return None
        def findUser(self, name):
                name = name.lower()
                ul = self.getUserlist()
                udi = dict(zip([u.name for u in ul], ul))
                cname = None
                for n in udi.keys():
                        if n.find(name) != -1:
                                if cname: return None #ambigious!!
                                cname = n
                if cname: return udi[cname]
                else: return None
        ####
        # History
        ####
        def _addHistory(self, msg):
                self._history.append(msg)
                if len(self._history) > self.mgr._maxHistoryLength:
                        rest, self._history = self._history[:-self.mgr._maxHistoryLength], self._history[-self.mgr._maxHistoryLength:]
                        for msg in rest: msg.detach()

################################################################
# RoomManager class
################################################################
class RoomManager:
        """Class that manages multiple connections."""
        ####
        # Config
        ####
        _Room = Room
        _PM = PM
        _PMHost = "c1.chatango.com"
        _PMPort = 5222
        _TimerResolution = 0.2 #at least x times per second
        _pingDelay = 20
        _userlistMode = Userlist_Recent
        _userlistUnique = True
        _userlistMemory = 500
        _userlistEventUnique = False
        _tooBigMessage = BigMessage_Multiple
        _maxLength = 2000
        _maxHistoryLength = 15000000
        ####
        # Init
        ####
        def __init__(self, name = None, password = None, pm = True):
                self._name = name
                self._password = password
                self._running = False
                self._tasks = set()
                self._rooms = dict()
                self.bgtime = 0
                self.setFontColor("808080")
                self.setFontSize(10)
                self.setFontFace("Arial")
                self.setNameColor("808080")
                self.enableBg()
                if pm:
                        self._pm = self._PM(mgr = self)
                else:
                        self._pm = None
        ####
        # Join/leave
        ####
        def joinRoom(self, room):
                room = room.lower()
                if room not in self._rooms:
                        con = self._Room(room, mgr = self)
                        self._rooms[room] = con
                        return con
                else:
                        return None
        def leaveRoom(self, room):
                room = room.lower()
                if room in self._rooms:
                        con = self._rooms[room]
                        con.disconnect()
        def getRoom(self, room):
                room = room.lower()
                if room in self._rooms:
                        return self._rooms[room]
                else:
                        return None
        ####
        # Properties
        ####
        def getUser(self): return User(self._name)
        def getName(self): return self._name
        def getPassword(self): return self._password
        def getRooms(self): return set(self._rooms.values())
        def getRoomNames(self): return set(self._rooms.keys())
        def getPM(self): return self._pm
        user = property(getUser)
        name = property(getName)
        password = property(getPassword)
        rooms = property(getRooms)
        roomnames = property(getRoomNames)
        pm = property(getPM)
        ####
        # Virtual methods
        ####
        def onInit(self):
                """Called on init."""
                pass
        def safePrint(self, text):
                """ use this to safely print text with unicode"""
                while True:
                        try:
                                print(text)
                                break
                        except UnicodeEncodeError as ex:
                                text = (text[0:ex.start]+'(unicode)'+text[ex.end:])
        def onConnect(self, room):
                pass
        def onReconnect(self, room):
                pass
        def onConnectFail(self, room):
                pass
        def onDisconnect(self, room):
                pass
        def onLoginFail(self, room):
                pass
        def onFloodBan(self, room):
                pass
        def onFloodBanRepeat(self, room):
                pass
        def onFloodWarning(self, room):
                pass
        def onMessageDelete(self, room, user, message):
                pass
        def onClearAll(self, room):
                pass
        def onModChange(self, room):
                pass
        def onModAdd(self, room, user):
                pass
        def onModRemove(self, room, user):
                pass
        def onMessage(self, room, user, message):
                pass
        def onHistoryMessage(self, room, user, message):
                pass
        def onJoin(self, room, user):
                pass
        def onLeave(self, room, user):
                pass
        def onRaw(self, room, raw):
                pass
        def onPing(self, room):
                pass
        def onUserCountChange(self, room):
                pass
        def onBan(self, room, user, target):
                pass
        def onUnban(self, room, user, target):
                pass
        def onBanlistUpdate(self, room):
                pass
        def onUnbanlistUpdate(self, room):
                pass
        def onPremiumLow(self, string):
                pass
        def onPMConnect(self, pm):
                pass
        def onPMDisconnect(self, pm):
                pass
        def onPMPing(self, pm):
                pass
        def onPMMessage(self, pm, user, body):
                pass
        def onPMBlocklistReceive(self, pm):
                pass
        def onPMContactAdd(self, pm, user):
                pass
        def onPMConnect1(self, pm, user, idle, status):
                pass
        def onPMContactRemove(self, pm, user):
                pass
        def onPMBlock(self, pm, user):
                pass
        def onPMUnblock(self, pm, user):
                pass
        def onPMIdle(self, pm, idle):
                pass
        def onEventCalled(self, room, evt, *args, **kw):
                pass
        ####
        # Deferring
        ####
        def deferToThread(self, callback, func, *args, **kw):
                def f(func, callback, *args, **kw):
                        ret = func(*args, **kw)
                        self.setTimeout(0, callback, ret)
                threading._start_new_thread(f, (func, callback) + args, kw)
        ####
        # Scheduling
        ####
        class _Task:
                def cancel(self):
                        """Sugar for removeTask."""
                        self.mgr.removeTask(self)
        def _tick(self):
                now = time.time()
                for task in set(self._tasks):
                        if task.target <= now:
                                task.func(*task.args, **task.kw)
                                if task.isInterval:
                                        task.target = now + task.timeout
                                else:
                                        self._tasks.discard(task)
        def setTimeout(self, timeout, func, *args, **kw):
                task = self._Task()
                task.mgr = self
                task.target = time.time() + timeout
                task.timeout = timeout
                task.func = func
                task.isInterval = False
                task.args = args
                task.kw = kw
                self._tasks.add(task)
                return task
        def setInterval(self, timeout, func, *args, **kw):
                task = self._Task()
                task.mgr = self
                task.target = time.time() + timeout
                task.timeout = timeout
                task.func = func
                task.isInterval = True
                task.args = args
                task.kw = kw
                self._tasks.add(task)
                return task
        def removeTask(self, task):
                if task in self._tasks:
                        self._tasks.discard(task)
        ####
        # Util
        ####
        def _write(self, room, data):
                room._wbuf += data
        def getConnections(self):
                li = list(self._rooms.values())
                if self._pm:
                        li.append(self._pm)
                return [c for c in li if c._sock != None]
        ####
        # Main
        ####
        def main(self):
                self.onInit()
                self._running = True
                while self._running:
                        conns = self.getConnections()
                        socks = [x._sock for x in conns]
                        wsocks = [x._sock for x in conns if x._wbuf != b""]
                        rd, wr, sp = select.select(socks, wsocks, [], self._TimerResolution)
                        for sock in rd:
                                con = [c for c in conns if c._sock == sock][0]
                                try:
                                        data = sock.recv(1024)
                                        if(len(data) > 0):
                                                con._feed(data)
                                        else:
                                                con.disconnect()
                                except socket.error:
                                        pass
                        for sock in wr:
                                con = [c for c in conns if c._sock == sock][0]
                                try:
                                        size = sock.send(con._wbuf)
                                        con._wbuf = con._wbuf[size:]
                                except socket.error:
                                        pass
                        self._tick()
        @classmethod
        def easy_start(cl, rooms = None, name = None, password = None, pm = True):
                if not rooms: rooms = str(input("Room names separated by semicolons: ")).split(";")
                if len(rooms) == 1 and rooms[0] == "": rooms = []
                if not name: name = str(input("User name: "))
                if name == "": name = None
                if not password: password = str(input("User password: "))
                if password == "": password = None
                self = cl(name, password, pm = pm)
                for room in rooms:
                        self.joinRoom(room)
                self.main()
        def stop(self):
                for conn in list(self._rooms.values()):
                        conn.disconnect()
                self._running = False
        def restart(self):
                for conn in list(self._rooms.values()):
                        conn.reconnect()
                self._running = True
        ####
        # Commands
        ####
        def enableBg(self):
                """Enable background if available."""
                self.user._mbg = True
                for room in self.rooms:
                        room.setBgMode(1)
        def disableBg(self):
                """Disable background."""
                self.user._mbg = False
                for room in self.rooms:
                        room.setBgMode(0)
        def enableRecording(self):
                """Enable recording if available."""
                self.user._mrec = True
                for room in self.rooms:
                        room.setRecordingMode(1)
        def disableRecording(self):
                """Disable recording."""
                self.user._mrec = False
                for room in self.rooms:
                        room.setRecordingMode(0)
        def setNameColor(self, color3x):
                self.user._nameColor = color3x
        def setFontColor(self, color3x):
                self.user._fontColor = color3x
        def setFontFace(self, face):
                self.user._fontFace = face
        def setFontSize(self, size):
                if size < 9: size = 9
                if size > 22: size = 22
                self.user._fontSize = size
################################################################
# User class (well, yeah, i lied, it's actually _User)
################################################################
_users = dict()
def User(name, *args, **kw):
        name = name.lower()
        user = _users.get(name)
        if not user:
                user = _User(name = name, *args, **kw)
                _users[name] = user
        return user
class _User:
        """Class that represents a user."""
        ####
        # Init
        ####
        def __init__(self, name, **kw):
                self._name = name.lower()
                self._sids = dict()
                self._msgs = list()
                self._nameColor = "000"
                self._fontSize = 12
                self._fontFace = "0"
                self._fontColor = "000"
                self._mbg = False
                self._mrec = False
                for attr, val in kw.items():
                        if val == None: continue
                        setattr(self, "_" + attr, val)
        ####
        # Properties
        ####
        def getName(self): return self._name
        def getSessionIds(self, room = None):
                if room:
                        return self._sids.get(room, set())
                else:
                        return set.union(*self._sids.values())
        def getRooms(self): return self._sids.keys()
        def getRoomNames(self): return [room.name for room in self.getRooms()]
        def getFontColor(self): return self._fontColor
        def getFontFace(self): return self._fontFace
        def getFontSize(self): return self._fontSize
        def getNameColor(self): return self._nameColor
        name = property(getName)
        sessionids = property(getSessionIds)
        rooms = property(getRooms)
        roomnames = property(getRoomNames)
        fontColor = property(getFontColor)
        fontFace = property(getFontFace)
        fontSize = property(getFontSize)
        nameColor = property(getNameColor)
        ####
        # Util
        ####
        def addSessionId(self, room, sid):
                if room not in self._sids:
                        self._sids[room] = set()
                self._sids[room].add(sid)
        def removeSessionId(self, room, sid):
                try:
                        self._sids[room].remove(sid)
                        if len(self._sids[room]) == 0:
                                del self._sids[room]
                except KeyError:
                        pass
        def clearSessionIds(self, room):
                try:
                        del self._sids[room]
                except KeyError:
                        pass
        def hasSessionId(self, room, sid):
                try:
                        if sid in self._sids[room]:
                                return True
                        else:
                                return False
                except KeyError:
                        return False
        ####
        # Repr
        ####
        def __repr__(self):
                return "%s" %(self.name)
################################################################
# Message class
################################################################
class Message:
        """Class that represents a message."""
        ####
        # Attach/detach
        ####
        def attach(self, room, msgid):
                if self._msgid == None:
                        self._room = room
                        self._msgid = msgid
                        self._room._msgs[msgid] = self
        def detach(self):
                """Detach the Message."""
                if self._msgid != None and self._msgid in self._room._msgs:
                        del self._room._msgs[self._msgid]
                        self._msgid = None
        ####
        # Init
        ####
        def __init__(self, **kw):
                self._msgid = None
                self._time = None
                self._user = None
                self._body = None
                self._room = None
                self._raw = ""
                self._ip = None
                self._unid = ""
                self._nameColor = "000"
                self._fontSize = 12
                self._fontFace = "0"
                self._fontColor = "000"
                for attr, val in kw.items():
                        if val == None: continue
                        setattr(self, "_" + attr, val)
        ####
        # Properties
        ####
        def getId(self): return self._msgid
        def getTime(self): return self._time
        def getUser(self): return self._user
        def getBody(self): return self._body
        def getUid(self): return self._uid
        def getIP(self): return self._ip
        def getFontColor(self): return self._fontColor
        def getFontFace(self): return self._fontFace
        def getFontSize(self): return self._fontSize
        def getNameColor(self): return self._nameColor
        def getRoom(self): return self._room
        def getRaw(self): return self._raw
        def getUnid(self): return self._unid
        msgid = property(getId)
        time = property(getTime)
        user = property(getUser)
        body = property(getBody)
        uid = property(getUid)
        room = property(getRoom)
        ip = property(getIP)
        fontColor = property(getFontColor)
        fontFace = property(getFontFace)
        fontSize = property(getFontSize)
        raw = property(getRaw)
        nameColor = property(getNameColor)
        unid = property(getUnid)
