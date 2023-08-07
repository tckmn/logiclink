#!/usr/bin/env python3

SRC = 748375557049417758
DST = 696572772134158413

from datetime import datetime
import discord

class LogicLink(discord.Client):
    async def on_ready(self):
        self.dst_channel = self.get_channel(DST)

    async def on_message(self, message):
        if message.channel.id == SRC and ('http://' in message.content or 'https://' in message.content):
            await self.dst_channel.send(f'originally posted by **{message.author.display_name}** https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}\n' + message.content)

if SRC == DST: raise Exception('wtf')  # sanity check

intents = discord.Intents.default()
intents.messages = True
LogicLink(intents=intents).run(open('token').read())
