#!/usr/bin/env python3

import discord
import json
import pickle
import sys

class Conf():
    def __init__(self, data):
        for k in ['src', 'src_extra', 'dst', 'admin', 'token', 'threshold']:
            if k not in data: raise Exception(f'conf missing key {k}')
            setattr(self, k, data[k])
        if self.dst in self.src or self.dst in self.src_extra: raise Exception('wtf')  # sanity check

class Owner():
    def __init__(self):
        try:
            with open('owners', 'rb') as f:
                self.data, self.posted = pickle.load(f)
        except:
            self.data = {}
            self.posted = set()
    def get(self, k): return self.data.get(k)
    def set(self, k, v):
        self.data[k] = v
        with open('owners', 'wb') as f:
            pickle.dump((self.data, self.posted), f)
    def had(self, k):
        if k in self.posted: return True
        self.posted.add(k)
        return False

conf = Conf(json.load(open('conf.json' if len(sys.argv) < 2 else sys.argv[1])))
owner = Owner()
header = lambda msg: f'originally posted by **{msg.author.display_name}** https://discord.com/channels/{msg.guild.id}/{msg.channel.id}/{msg.id}\n'

class LogicLink(discord.Client):
    async def on_ready(self):
        self.dst_channel = self.get_channel(conf.dst)

    async def on_message(self, msg):
        if msg.channel.id == conf.src and ('http://' in msg.content or 'https://' in msg.content):
            await self.post(msg)

        if msg.author.id == conf.admin and msg.content.startswith('!eval '):
            exec('async def __stupid(self):return ' + msg.content[6:])
            await msg.reply(await locals()['__stupid'](self))

    async def on_raw_reaction_add(self, ev):
        if ev.emoji.name == '📥' and ev.channel_id in conf.src_extra and (msg := await self.check_react(ev)):
            await self.post(msg)

        if ev.emoji.name == '📤' and ev.channel_id == conf.dst and (msg := await self.check_react(ev)):
            await msg.delete()

    async def post(self, message):
        if owner.had(message.id): return
        msg = await self.dst_channel.send(header(message) + message.content)
        await msg.add_reaction('✅')
        owner.set(msg.id, message.author.id)

    async def check_react(self, ev):
        msg = await self.get_channel(ev.channel_id).fetch_message(ev.message_id)
        if msg.author.id == ev.user_id or owner.get(msg.id) == ev.user_id: return msg
        if next((r for r in msg.reactions if r.emoji == ev.emoji.name and r.count >= conf.threshold), None): return msg

LogicLink(intents=discord.Intents.all()).run(conf.token)
