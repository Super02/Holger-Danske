import re
from nextcord.ext import commands
from nextcord import Interaction
import nextcord
import os
import requests
import json
import time

GUILD_IDS = [
    822208355984605205, # Test server
    820093197933740062 # Slap Battles 
]

debug = False
dansk_channel = 1012674704902979604 if not debug else 1050447006302224444
guild = 820093197933740062 if not debug else 822208355984605205
stumhed_id = 1017679964327399474 if not debug else 1050480051289870478
godkendt_id = 1047593571215224913 if not debug else 1050456059510280202
hvidliste_id = 1068953525473783949 if not debug else 1068955603730452542
log_channel = 1026217717474283702 if not debug else 1050447006302224444

warned = {}
approved_messages = ["hej", "goddag", "død kanal"]
blacklisted_messages = ["hej", "goddag", "halløj", "hej gutter"]
approved_language = ['da', 'no', 'sv']
class dansksnak(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.hvidliste_rolle = None
        self.dansk_stumhed = None
        self.dansk_godkendt = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.hvidliste_rolle = self.bot.get_guild(guild).get_role(hvidliste_id)
        self.dansk_stumhed = self.bot.get_guild(guild).get_role(stumhed_id)
        self.dansk_godkendt = self.bot.get_guild(guild).get_role(godkendt_id)
        

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id == dansk_channel and message.author.id != self.bot.user.id:
            if self.hvidliste_rolle in message.author.roles:
                return
            if(message.author.bot):
                await message.delete()
                return
            if message.content.lower() in blacklisted_messages:
                if message.author.id in warned.keys() and time.time() - warned[message.author.id] < 172800:
                    await message.delete()
                    try:
                        await message.author.remove_roles(self.dansk_godkendt)
                        await message.author.add_roles(self.dansk_stumhed)
                    except Exception as e:
                        print(e)
                        return
                    await message.channel.send(f"{message.author.mention} Din besked og adgang til kanalen er blevet fjernet da du skriver for meget {message.content}.")
                    await self.bot.get_channel(log_channel).send(f"dansk-snak automod (user used forbidden word too often): {message.author.mention} : {message.content}")
                    return
                await message.add_reaction("😡")
                await message.reply(f"Dette er en advarsel. Hvis du fortsætter med at skrive {message.content}, vil du blive smidt ud af kanalen.")
                warned[message.author.id] = time.time()
            response = get_language(message.content)
            if (not response[0] in approved_language) and response[1] > 0.75:
                await message.delete()
                try:
                    await message.author.remove_roles(self.dansk_godkendt)
                    await message.author.add_roles(self.dansk_stumhed)
                except Exception as e:
                    print(e)
                    return
                await message.channel.send(f"{message.author.mention} Din besked og adgang til kanalen er blevet fjernet da du ikke taler dansk.")
                await self.bot.get_channel(log_channel).send(f"dansk-snak automod: {response[0]}:{response[1]}-{message.author.mention} : {message.content}")


    @nextcord.slash_command(
        description="Grants you permission to talk in dansk-snak."
    )
    async def dansksnak(self, interaction: Interaction):
        dansk_stumhed = self.bot.get_guild(guild).get_role(stumhed_id)
        member = self.bot.get_guild(guild).get_member(interaction.user.id)
        if(member.roles.count(dansk_stumhed) == 0):
            role = self.bot.get_guild(guild).get_role(godkendt_id)
            try:
                await interaction.user.add_roles(role)
            except Exception as e:
                await interaction.response.send_message("Der skete en fejl!.", ephemeral=True)
                print(e)
                return
            await interaction.response.send_message(f"Du har nu adgang til dansk-snak kanalen! Tilgå den her <#{dansk_channel}>", ephemeral=True)
        else:
            await interaction.response.send_message("Du er blevet udelukket fra dansk-snak kanalen.", ephemeral=True)


def get_language(message):
    if(message in approved_messages):
        return ['da', 1]
    if(len(message) <= 4 or len(message.split(' ')) <= 2):
        return ['da', 1]
    message = re.sub(r'<@*(\d+)>|:(.*):','',message)
    print("Performing language detection on: " + message)
    headers = {"Authorization": "Bearer " + os.getenv('TEXT_EDENAI_KEY')}
    url ="https://api.edenai.run/v2/translation/language_detection"
    payload={"providers": "neuralspace,amazon", 'text': message}
    response = requests.post(url, json=payload, headers=headers)
    result = json.loads(response.text)
    print(result)
    confidence = result['neuralspace']['items'][0]['confidence'] if result['neuralspace']['items'][0]['confidence'] < result['amazon']['items'][0]['confidence'] else result['amazon']['items'][0]['confidence']
    ret_val = [result['neuralspace']['items'][0]['language'] if confidence > result['amazon']['items'][0]['confidence'] else result['amazon']['items'][0]['language'], confidence]
    if(result['neuralspace']['items'][0]['language'] in approved_language or result['amazon']['items'][0]['language'] in approved_language):
        return ['da', 1]
    return ret_val

def setup(bot):
  bot.add_cog(dansksnak(bot))
