#!/usr/bin/env python3

import discord
import json
import pickle
import sys

class Conf():
    def __init__(self, data):
        for k in ['src', 'src_extra', 'dst', 'admin', 'token', 'table', 'threshold']:
            if k not in data: raise Exception(f'conf missing key {k}')
            setattr(self, k, data[k])
        if self.dst in self.src or self.dst in self.src_extra: raise Exception('wtf')  # sanity check

ORIG = 0
FEED = 1
OWNER = 2
lookup_keys = [ORIG, FEED]

class Lookup():
    def __init__(self, table, n):
        self.table = table
        self.n = n
    def has(self): return self.n is not None
    def at(self, k): return None if self.n is None else self.table.data[self.n][k]
    def rm(self):
        self.table.data.pop(self.n)
        self.table.save()
        self.table.rebuild()

class Table():
    def __init__(self, path):
        self.path = path
        try:
            with open(path, 'rb') as f: self.data = pickle.load(f)
        except: self.data = []
        self.rebuild()
    def rebuild(self):
        self.lookup = {q: {x[q]: i for i,x in enumerate(self.data)} for q in lookup_keys}
    def save(self):
        with open(self.path, 'wb') as f: pickle.dump(self.data, f)
    def add(self, a, b, c):
        self.data.append(d := (a,b,c))
        self.save()
        for k in lookup_keys: self.lookup[k][d[k]] = len(self.data)-1
    def by(self, fr, q):
        return Lookup(self, self.lookup[fr].get(q))

conf = Conf(json.load(open('conf.json' if len(sys.argv) < 2 else sys.argv[1])))
table = Table(conf.table)
afmt = lambda a: (lambda s: f'\n{"<"*s}{a.url}{">"*s}')(a.is_spoiler())
fmt = lambda msg: f'originally posted by **{msg.author.display_name}** https://discord.com/channels/{msg.guild.id}/{msg.channel.id}/{msg.id}\n{msg.content}{"".join(map(afmt, msg.attachments))}'

class LogicLink(discord.Client):
    async def on_ready(self):
        self.dst_channel = self.get_channel(conf.dst)

    async def on_message(self, msg):
        if msg.channel.id in conf.src and ('http://' in msg.content or 'https://' in msg.content):
            await self.post(msg)

        if msg.author.id == conf.admin and msg.content.startswith('!eval '):
            exec('async def __stupid(self):return ' + msg.content[6:])
            await msg.reply(await locals()['__stupid'](self))

    async def on_raw_reaction_add(self, ev):
        if ev.emoji.name == '📥' and ev.channel_id in conf.src_extra and (msg := await self.check_react(ev)):
            await self.post(msg)

        if ev.emoji.name == '📤' and ev.channel_id == conf.dst and (msg := await self.check_react(ev)):
            await self.unpost(msg)

    async def on_raw_message_edit(self, ev):
        if (res := table.by(ORIG, ev.message_id)).has():
            origmsg = await self.get_channel(ev.channel_id).fetch_message(ev.message_id)
            feedmsg = await self.dst_channel.fetch_message(res.at(FEED))
            await feedmsg.edit(content=fmt(origmsg))

    async def on_raw_message_delete(self, ev):
        if (res := table.by(ORIG, ev.message_id)).has():
            feedmsg = await self.dst_channel.fetch_message(res.at(FEED))
            await self.unpost(feedmsg)

    async def post(self, message):
        if table.by(ORIG, message.id).has(): return
        msg = await self.dst_channel.send(fmt(message))
        await msg.add_reaction('✅')
        table.add(message.id, msg.id, message.author.id)

    async def unpost(self, message):
        await message.delete()
        table.by(FEED, message.id).rm()

    async def check_react(self, ev):
        msg = await self.get_channel(ev.channel_id).fetch_message(ev.message_id)
        if conf.admin == ev.user_id: return msg
        if msg.author.id == ev.user_id or table.by(FEED, msg.id).at(OWNER) == ev.user_id: return msg
        if next((r for r in msg.reactions if r.emoji == ev.emoji.name and r.count >= conf.threshold), None): return msg

LogicLink(intents=discord.Intents.all()).run(conf.token)
