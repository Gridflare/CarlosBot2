"""
A Discord Bot
"""

import logging, logging.config, asyncio
import random, math, time, sys, json, re, html
import discord, requests

# TODO
# Implement Tarot, Madlib
# Add command to create join link
# Add test cases, will need to create a dummy command object
# Update main docstring

## STARTUP ##

# Start logger
loggingconf = dict( #TEMP move to config file when possible
    version=1,
    formatters={
        'simple':{'format':'%(name)s:%(levelname)s|%(message)s'},
        'detailed':{
            'format':'%(asctime)s|%(name)s:%(levelname)s|%(message)s',
            'datefmt': '%H:%M:%S'}
        },
    handlers={
        'console':{
            'class':'logging.StreamHandler',
            'formatter':'detailed',
            'level':'DEBUG'
            },
        'file':{
            'class':'logging.FileHandler',
            'formatter':'detailed',
            'level':'DEBUG',
            'filename':'bot.log',
            'mode':'w'
            }
        },
    loggers={
        'boot':{
            'level':'DEBUG' # Don't need handlers, will propagate to root
            # ~ 'handlers':['console','file']
            },
        'response':{
            'level':'DEBUG'
            # ~ 'handlers':['console','file']
            },
        'event':{
            'level':'DEBUG',
            'handlers':['console'],
            'propagate':False
            }
        },
    root={
        'level':'DEBUG',
        'handlers':['console','file']
        }
    )
logging.config.dictConfig(loggingconf)
bootlog = logging.getLogger('boot')

client = discord.Client()

def checkfiles():
    pass

def loadconfig():
    global config
    try:
        with open('config.json') as f:
            config = json.load(f)
        bootlog.info('config.json was loaded successfully')
    except FileNotFoundError:
        bootlog.warning('config.json file not found and will be created')
        config = {} # TODO walk user through config setup
        config['token'] = input('Please enter the bot\'s API token: ')
        config['owner'] = [input('Please enter your name of format name#0000 so the bot can recognize you (optional): ')]
        config['cmdpfx'] = input('Please enter the default command prefix: ')
        config['unassignablePermissions'] = ['kick_members','ban_members',
            'administrator','manage_channels','manage_guild','priority_speaker',
            'manage_messages','manage_roles','manage_webhooks']
        with open('config.json','w') as conffile:
            json.dump(config,conffile,indent=2)

    except json.decoder.JSONDecodeError:
        bootlog.exception('Failed to load config file,'
            'please ensure that it is not corrupt and/or delete it')
        sys.exit('Exiting due to previous error')


def loadpersistance():
    # Divide into user and server -specific persistance
    persistance = dict(servers={},users={})

    bootlog.warning('TODO Create persistance file')

def loadresources():
    global resources
    try:
        with open('resources.json') as f:
            resources = json.load(f)
        bootlog.info('loaded extra resources')
    except json.decoder.JSONDecodeError:
        bootlog.exception('Could not load resources file, please ensure that it is not corrupt')

def genHelpTxt():
    # Generate the help text procedurally
    global helptxt
    helptxt = f'```\nThe command prefix is set to {config["cmdpfx"]}\n'
    helpdict = {}
    bootlog.info('Generating help text')
    for cmd in (f for f in dir(response) if callable(getattr(response, f)) and not f.startswith("__")):
        cmdfunc = getattr(response, cmd)
        if hasattr(cmdfunc, 'hidden') and cmdfunc.hidden: continue # Skip hidden commands
        doc = cmdfunc.__doc__
        if doc is None:
            category = 'NONE'
            desc = ' : NONE'
        else:
            category, desc = getattr(response, cmd).__doc__.split('#', maxsplit=1)
        if category.upper() in helpdict:
            helpdict[category.upper()].append(cmd + desc)
        else:
            helpdict[category.upper()] = [cmd + desc]

    for category in helpdict.keys():
        helptxt += f'\n## {category} ##\n'
        for h in helpdict[category]:
            helptxt += h + '\n'

    helptxt += '```'

## DECORATORS/WRAPPERS ##

async def sendmsg(channel, msg, **kwargs):
    '''helper for concise message sending'''
    return await channel.send(msg.replace("@everyone", "@\u200beveryone"))

def hiddencmd(func):
    # Decorator that hides command from help
    func.hidden = True
    return func

def admincmd(func):
    # Decorator ensuring admin only usage and excluded from help
    @hiddencmd
    def adminonly(self,*args):
        if str(self.cmd.author) in config['owner']:
            func(self,*args)
        else:
            self.msg = 'You do not have permission to do that'
    return adminonly

def getcat(imgtype):
    while True: # if it fails try again
        resp = requests.get(f'http://thecatapi.com/api/images/get?format=src&type={imgtype}')
        if resp.url:
            return resp.url
        else:
            print('Failed to find cat')
            time.sleep(0.1)

## INTERACTION LOGIC ##

class response(): # designed this way for testability
    # 3 types of response: single, series and edits
    def __init__(self,cmd):
        self.cmd = cmd
        self.log = logging.getLogger('response')
        self.ch = self.cmd.channel # can be overidden later if needed
        self.type = 'single' # can be overidden later if needed

        try:
            func, args = cmd.content[len(config['cmdpfx']):].split(sep=None,maxsplit=1)
        except ValueError: # No args given
             func, args = cmd.content[len(config['cmdpfx']):], None

        if hasattr(self, func): # Call the command
            getattr(self, func)(args)
        else:
            self.log.exception(f'Unknown command called: {func}')
            # ~ self.msg=f'Unknown command `{func}`'
            self.type = 'silent'

    ####################
    # GREETINGS & More #
    ####################
    def ping(self, args):
        """GREETINGS# : Pong!"""
        self.msg=self.cmd.author.mention +' pong!'

    @hiddencmd
    def pong(self, args):
        self.msg=self.cmd.author.mention +' ping!'
    def hi(self, args):
        """GREETINGS# : Hello?"""
        self.msg=self.cmd.author.mention +' nice to meet you!'
    @hiddencmd
    def hello(self, args):
        self.msg=self.cmd.author.mention +' nice to meet you!'

    def hiss(self,args):
        """GREETINGS# : Don't you dare!"""
        self.msg=random.choice(resources['hissimgs'])
    def help(self,args):
        """UTILITIES# : Prints this"""
        self.msg = helptxt

    #############
    # RNG GAMES #
    #############

    def flip(self,args):
        """RNG# : Flip a coin"""
        self.msg = ('heads','tails')[random.randint(0, 1)]

    def roll(self,args):
        """RNG# [max]: Roll a die"""
        if args is not None and args.isdecimal():
            self.msg = 'You rolled a ' + str(random.randint(1, int(args)))
        else:
            self.msg = 'You rolled a ' + str(random.randint(1, 6))

    def rock(self,args):
        """RNG#, paper, scissors : I don\'t cheat, promise!"""
        self.msg = random.choice(('rock','paper','scissors'))
    @hiddencmd
    def scissors(self,args): self.rock(args)
    @hiddencmd
    def paper(self,args): self.rock(args)

    def insult(self,args):
        """RNG# : I will be creative, don\'t forget to tag your target(s)!"""
        insultAdjectives = resources['insults']['adjectives']
        insultNouns = resources['insults']['nouns']
        def genInsult():
            adj = random.choice(insultAdjectives)
            noun = random.choice(insultNouns)
            a = 'an' if adj.startswith(('a','e','i','o','u')) else 'a'
            return f', you are {a} {adj} {noun}!'
        if len(self.cmd.mentions) == 0:  # insults the author if they mention nobody
            target = self.cmd.author
            self.msg = target.name + genInsult()
        else:
            queue = []
            for i in self.cmd.mentions:  # insults all who are mentioned
                queue.append(i.name + genInsult())
            self.msg = '\n'.join(queue)

            # .mention replaced by .name because it was annoying
            # attempted to replace .name with .nick but then fails if the target has no nickname

    def slots(self, args):
        """RNG# : play the slot machine"""
        # TODO move to resources
        slots = [':dog:', ':cat:', ':mouse:', ':cow:', ':pig:', ':chicken:']
        self.type = 'edits'

        # Generator that produces the outputs
        def slotmachine():
            yield 'Please gamble responsibly (and take turns)'

            for i in range(random.randint(4,8)):
                slot1 = random.choice(slots)
                time.sleep(0.1) # this is to give the seed a chance to change
                slot2 = random.choice(slots)
                time.sleep(0.1)
                slot3 = random.choice(slots)
                time.sleep(0.1)
                yield f'|{slot1}|{slot2}|{slot3}|'
                time.sleep(0.7)

            if slot1 == slot2 and slot2 == slot3 and slot3 == slot1:
                endMessage = 'YOU WON!!'
            elif slot1 != slot2 and slot2 != slot3 and slot3 != slot1:
                endMessage = 'You lost...'
            else:
                endMessage = 'You almost won!'

            time.sleep(0.5)
            yield f'|{slot1}|{slot2}|{slot3}|\n{endMessage}'

        self.msgs = slotmachine()

    def tarot(self, args):
        """RNG# : Not Implemented"""
        self.msg = 'Not implemented'

    def rname(self, args):
        """RNG# : Not Implemented"""
        self.msg = 'Not implemented'

    def duckduckgun(self, args):
        """RNG# <num1> <num2> : a game of dodging bullets, pick two numbers 1-6"""
        if args is None or len(args) < 2:
            self.msg = f"Usage: {config['cmdpfx']}ddg <num1> <num2> : a game of dodging bullets, pick two numbers 1-6"
            return
        self.type = 'edits'
        if len(args) > 2: userInput = args[:2]
        else: userInput = args

        def gameSequence():
            yield ':grinning:         :gun:.'
            chamber = random.randint(1,6)
            for i in range(1, chamber):
                if str(i) in userInput:
                    yield (':arrow_double_down:         :gun:\n:grinning:\n' +
                        self.cmd.author.name + ' ducks\nthe gun clicks [' + str(i) +']')
                else:
                    yield (':grinning:         :gun:\n\n\nthe gun clicks [' + str(i) + ']')
                time.sleep(2)
            if str(chamber) in userInput:
                yield (':arrow_double_down: :boom::gun:\n:grinning:\n'
                    f'{self.cmd.author.name} ducks\nthe gun fires [{chamber}]\n'
                    f'{self.cmd.author.name} dodged the bullet')
            else:
                yield (':dizzy_face: :boom::gun:\n\nthe gun fires [' +
                     str(chamber) + ']\n' + self.cmd.author.name + ' is dead')

        self.msgs = gameSequence()

    def madlib(self, args):
        """RNG# [maxPrompts] : Fill in my blanks! Optionally specify a max size"""
        if 'bot' not in self.cmd.channel.name:
            self.msg = "This feature is restricted to bot channels"
            return

        titleRegex = re.compile(r'<title>(.+)</title>')
        wordRegex = re.compile(r'<td align=\'right\'>(.+) <b>\[(\d+)\]')
        adlibRegex = re.compile(r"<td align='left'>\n\s+(.+)")

        blacklist = [117, 163] # adlibs known to not work well

        maxPrompts = 30
        if args:
            try: maxPrompts = min(int(args), 10) # Need a minimum maximum
            except: pass

        # Find the range of adlibs we can get and choose one
        def findAndProcessAdlib():
            numAdlibs = int(
                re.search(r'<meta name="title" content="(\d+) Free Online ad-Lib',
                requests.get('https://www.madtakes.com/index.php').text).group(1))
            while True:
                adlibNum = random.randint(1,numAdlibs)
                if adlibNum not in blacklist: break

            adlibHTML = requests.get(
                f'https://www.madtakes.com/printglib.php?glibid={adlibNum}').text

            # Clean up globally
            adlibHTML = html.unescape(adlibHTML).replace('`',"'")

            # Get title
            adlibTitle = titleRegex.search(adlibHTML).group(1)

            # Get wordlist, as (TYPE, NUM) pairs, sort, and simplify
            wordPrompts = wordRegex.findall(adlibHTML)
            wordPrompts = sorted(wordPrompts, key=lambda t: int(t[1]))
            wordPrompts = [t[0].replace('<BR>',' ') for t in wordPrompts]

            # Get adlib
            adlibText = adlibRegex.search(adlibHTML).group(1)
            adlibText = adlibText.replace('<br>','\n')
            adlibText = re.sub( # Convert HTML to Python format string
                r"<sub><sub>.+?\[(\d+)\].+?<sup><\/sup>",
                r'*{\1}*',adlibText)

            if len(adlibText) > 1700 or len(wordPrompts) > maxPrompts:
                self.log.warning('Found adlib that was too long!')
                return findAndProcessAdlib()
            else:
                return adlibTitle, wordPrompts, adlibText, adlibNum, numAdlibs

        def madlibSequence():
            adlibTitle, wordPrompts, adlibText, adlibNum, numAdlibs = findAndProcessAdlib()
            self.log.info(f'Using adlib {adlibTitle} #{adlibNum}')
            promptResponses = []

            for prompt in wordPrompts:
                usrmsg = yield 'Give me a(n) ' + prompt
                promptResponses.append(usrmsg)

            completedAdlib = f'**{adlibTitle}** #{adlibNum}/{numAdlibs}\n'
            completedAdlib += adlibText.format(None, *promptResponses)
            yield completedAdlib

        self.type = 'convo'
        self.msg = 'Finding a madlib, this may take a moment...'
        self.msgs = madlibSequence()

    @hiddencmd
    def convotest(self, args):
        # Just a demo of how to use the 'convo' message type
        self.type = 'convo'
        self.msg = 'Repeat after me!'
        def convogen():
            mylist = ['one','two','three','four']
            for i in mylist:
                usrmsg = yield i
                if usrmsg != i:
                    yield 'You failed!'
                    raise StopIteration()
            yield 'You did it!'

        self.msgs = convogen()

    @hiddencmd
    def ddg(self, args): self.duckduckgun(args)

    ########################
    # CATS & Other Animals #
    ########################

    def cat(self, args):
        """ANIMALS# : Find a cute cat!"""
        self.msg = getcat('jpg,png') + ' :cat:'
    def catgif(self, args):
        """ANIMALS# : Find a cute cat gif!"""
        self.msg = getcat('gif') + ' :cat:'

    def shibe(self, args):
        """ANIMALS#, doge : Find a cute shibe!"""
        self.msg = requests.get('http://shibe.online/api/shibes?count=1&urls=true&httpsUrls=false').text.strip('[]""]') + ' :dog2:'
    @hiddencmd
    def dog(self, args):
        self.shibe(args)
    @hiddencmd
    def doge(self, args):
        self.shibe(args)

    ###############
    # ADMIN STUFF #
    ###############

    def userimg(self, args):
        """UTILITIES# : returns a url of the pinged user's avatar"""
        if len(self.cmd.mentions) == 0:  # uses the author if they mention nobody
            target = self.cmd.author
        else:
            target = self.cmd.mentions[0]
        self.msg = target.avatar_url

    @hiddencmd # Not even usuable as a command, definitely don't want in help
    def roleIsAssignable(self, role):
        if role.name == '@everyone': return False
        # If the requested role has a denied permission, return false
        if any(getattr(role.permissions,up) for up in config['unassignablePermissions']):
            return False
        # If the role is higher than us, return false
        if role >= self.cmd.guild.get_member(client.user.id).top_role:
            return False

        return True

    def source(self, args):
        """UTILITIES# : Link to my source code"""
        self.msg = 'https://github.com/Gridflare/CarlosBot2'

    def roles(self, args):
        """UTILITIES# : List the roles on this server"""
        validroles = ['```Roles I can give you:']
        validroles.extend(map(lambda r: r.name,
            filter(self.roleIsAssignable, self.cmd.guild.roles)))
        validroles.append('```')

        self.msg = '\n'.join(validroles)

    def role(self, targetRole):
        """UTILITIES# : Assign a role, if possible"""
        validroles = list(filter(self.roleIsAssignable, self.cmd.guild.roles))
        if targetRole.lower() not in list(map(lambda r: r.name.lower(), validroles)):
            self.msg = 'Invalid Role'
            return

        self.type = 'action'
        self.onError = 'Could not manage role'
        for role in validroles:
            if targetRole.lower() == role.name.lower():
                # check if user has the role, if so remove, else, add
                if role in self.cmd.author.roles:
                    self.action = (self.cmd.author.remove_roles, ([role]))
                    self.msg = 'You have been removed from the cult of ' + role.name
                else:
                    self.action = (self.cmd.author.add_roles, ([role]))
                    self.msg = 'Enjoy your new role!'
                break

    def link(self, args):
        """UTILITIES# : Get the link to add me to a server"""
        self.msg = ('https://discordapp.com/oauth2/authorize?client_id=' +
                    str(client.user.id) +
                    '&scope=bot&permissions=0')

    def jointime(self, user):
        """UTILITIES# <member>: Get the time a user joined the server"""
        guild = self.cmd.guild
        memberObj = guild.get_member_named(user)
        if memberObj is None:
            self.msg = 'Could not find user ' + user
        else:
            self.msg = str(memberObj.joined_at)

    @admincmd
    def stop(self, args):
        self.msg = 'Shutting down...'
        self.log.info('Shutting down...')
        sys.exit(0)


    # for remote restarting (if using runforever.sh)
    @admincmd
    def restart(self, args):
        self.msg = 'Restarting...'
        self.log.info('Restarting...')
        sys.exit(1)


## EVENT HANDLING ##

@client.event # runs to start bot
async def on_ready():
    print('------')
    print('Logged in as')
    print(client.user.name)
    botid = str(client.user)
    print(botid)
    print(client.user.id)
    print('------')
    print('Discord.py version: ' + discord.__version__)
    print(client.user.name + ' is on ' + str(len(client.guilds)) + ' servers')
    print(client)

@client.event
async def on_message(message):
    logging.getLogger('event').debug(
        f'{message.guild}|{message.channel}|{message.author}:{message.content}')
    if message.content.startswith(config['cmdpfx']) and not message.author.bot:
        resp = response(message)
        if resp.type == 'single':
            await sendmsg(resp.ch, resp.msg)

        elif resp.type == 'series':
            for msg in resp.msgs: # Handle long running routines
                await sendmsg(resp.ch, msg)

        elif resp.type == 'convo': # For conversations
            # Handle a pre-message if it exists
            if hasattr(resp, 'msg'): await sendmsg(resp.ch, resp.msg)

            def check(m):
                return m.channel == resp.ch and not m.author.bot

            try: # Run to completion
                await sendmsg(resp.ch, resp.msgs.send(None))
                while True:
                    usermsg = await client.wait_for('message', check=check, timeout=120)
                    await sendmsg(resp.ch, resp.msgs.send(usermsg.content))
            except asyncio.TimeoutError:
                try: # establish whether the routine finished or not
                    resp.msgs.send(None)
                except StopIteration:
                    pass # if it is finished, be silent
                else:
                    await sendmsg(resp.ch, 'Timed out waiting for a response')
            except StopIteration:
                pass

        elif resp.type == 'edits':
            tmp = await sendmsg(resp.ch,next(resp.msgs))
            for msg in resp.msgs: # Handle long running routines
                await tmp.edit(content=msg)

        elif resp.type == 'silent':
            return

        elif resp.type == 'action':
            func, args = resp.action
            try:
                await func(*args)
                if hasattr(resp, 'msg'): await sendmsg(resp.ch, resp.msg)
            except Exception as e:
                if hasattr(resp, 'onError'):
                    await sendmsg(resp.ch, resp.onError)
                else:
                    await sendmsg(resp.ch, 'An unhandled error has occcured')

        else:
            resp.log.error(f'Unknown response type {resp.type}')

def getDefaultChannel(guild):
    # TODO move to config
    candidates = ['general','log']

    guildchannels = guild.channels

    for chan in guildchannels:
        if chan.name in candidates:
            return chan

    raise Exception('Member joined but no suitable channel found')

@client.event # greets new members
async def on_member_join(member):
    server = member.guild

    fmt = '**{0.name}**, welcome to {1.name}! :grinning:'
    logging.getLogger('event').info(
        time.strftime('%X') + '|' + member.name + ' has joined ' + server.name)
    msg = await sendmsg(getDefaultChannel(server), fmt.format(member, server))
    await msg.add_reaction('\U0001F44B')

@client.event # announces departures
async def on_member_remove(member):
    server = member.guild

    fmt = '**{0.name}** has departed :disappointed:'
    logging.getLogger('event').info(
    time.strftime('%X') + '|' + member.name + ' has left ' + server.name)
    await sendmsg(getDefaultChannel(server), fmt.format(member))

@client.event # Log msg deletion
async def on_message_delete(message):
    msgBy = message.author.name
    logging.getLogger('event').info(f'Message by {msgBy} deleted')
    g = message.guild

    log_chan = None
    for c in g.channels:
        if c.name == 'deletion_log':
            log_chan = c
            break
    else: return # Channel does not exist

    delBy = None
    async for entry in g.audit_logs(action=discord.AuditLogAction.message_delete):
        delBy = entry.user

    deletionMsg = f'{delBy} deleted message by {msgBy} in #{message.channel.name}: "{message.content}"'

    await sendmsg(log_chan, deletionMsg)


if __name__ == '__main__':

    loadconfig()
    # ~ print(response.rock.__doc__.format(config))
    loadpersistance()
    loadresources()
    genHelpTxt()
    bootlog.info('Initialising bot...')
    client.run(config['token'])
    sys.exit('END OF FILE') # Using sys.exit to raise a non-zero code so the bot restarts in the runforever code

