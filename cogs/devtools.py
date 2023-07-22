import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, TextChannel, Intents
from io import StringIO
import sys
from utils import db # Used for code eval
import inspect
import codecs
import utils
import datetime # Used for code eval
import json
import cooldowns
from cooldowns import CallableOnCooldown
import requests
from random import choice
from string import ascii_lowercase



class devtools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.eval = []
        self.permitted = []

    @nextcord.slash_command(
        description="Echoes a message to a channel",
    )
    @utils.Utils().get_permission_level(8)
    async def echo(self, interaction: Interaction, message: str = SlashOption(name="message", required=True), channel: TextChannel = SlashOption(name="channel", required=False)):
        if not utils.Utils().get_permission_level(2).predicate(interaction) and not interaction.user.id in self.permitted:
            raise nextcord.errors.ApplicationCheckFailure("You are not permitted to use this command!")
        if channel is None:
            channel = interaction.channel
        try:
            await self.bot.get_channel(channel.id).send(message)
        except:
            await interaction.response.send_message("Message not sent!", ephemeral=True)
            return
        requests.post("https://discord.com/api/webhooks/1105131060066537494/MS1OZjjgy8wBJE32bP4ExcqfCIvQc8LoLva-nI6EfAZkDsDsZ9KYhz6Ky4CMMKW-zBkw", json={"content": f"**Echo:**:\nBy: {interaction.user.id}\nIn: {channel.mention}\nContent: {message}"})
        await interaction.response.send_message("Message sent!", ephemeral=True)

    @nextcord.slash_command(
        description="Replies to a message in a channel",
    )
    @utils.Utils().get_permission_level(8)
    async def reply(self, interaction: Interaction, messageid: str = SlashOption(name="messageid", required=True), message: str = SlashOption(name="message", required=True)):
        if not utils.Utils().get_permission_level(2).predicate(interaction) and not interaction.user.id in self.permitted:
            raise nextcord.errors.ApplicationCheckFailure("You are not permitted to use this command!")
        channel = interaction.channel
        try:
            msg = await self.bot.get_channel(channel.id).fetch_message(int(messageid))
        except (nextcord.errors.NotFound, ValueError):
            await interaction.response.send_message(embed=utils.Utils().error_embed(f"Message not found from message id. Does the message exist in {interaction.channel.mention}?"), ephemeral=True)
            return
        await msg.reply(message)
        requests.post("https://discord.com/api/webhooks/1105131060066537494/MS1OZjjgy8wBJE32bP4ExcqfCIvQc8LoLva-nI6EfAZkDsDsZ9KYhz6Ky4CMMKW-zBkw", json={"content": f"**Reply:**\nBy:{interaction.user.id}\nIn: {channel.mention}\nContent: {message}\nReply message ID: {msg.id}"})
        await interaction.response.send_message("Message sent!", ephemeral=True)
    
    @nextcord.slash_command(
        description="Give a staff member permission to use the echo and reply commands",
        default_member_permissions=8,
    )
    @utils.Utils().get_permission_level(2)
    async def add_echo_permit(self, interaction: Interaction, member: nextcord.Member = SlashOption(name="member", required=True)):
        self.permitted.append(member.id)
        await interaction.response.send_message(f"{member.mention} permitted access to use reply/echo commands!")
    
    @nextcord.slash_command(
        description="Remove a staff members permission to use the echo and reply commands",
        default_member_permissions=8,
    )
    @utils.Utils().get_permission_level(2)
    async def remove_echo_permit(self, interaction: Interaction, member: nextcord.Member = SlashOption(name="member", required=True)):
        if not member.id in self.permitted:
            return await interaction.response.send_message(f"{member.mention} does not have permission to use reply/echo commands!", ephemeral=True)
        self.permitted.remove(member.id)
        await interaction.response.send_message(f"{member} has gotten their echo/reply permissions revoked!", ephemeral=True)

    @nextcord.slash_command(
        description="Unloads a cog",
        default_member_permissions=8,
    )
    @utils.Utils().get_permission_level(0)
    async def unload(self, interaction: Interaction, cog: str = SlashOption(name="cog", required=True)):
        try:
            self.bot.unload_extension(cog)
        except:
            await interaction.response.send_message("Cog not found!", ephemeral=True)
            return
        await interaction.response.send_message("Cog unloaded!", ephemeral=True)
    
    @nextcord.slash_command(
        description="Loads a cog",
        default_member_permissions=8,
    )
    @utils.Utils().get_permission_level(0)
    async def load(self, interaction: Interaction, cog: str = SlashOption(name="cog", required=True)):
        try:
            self.bot.load_extension(cog)
        except:
            await interaction.response.send_message("Cog not found!", ephemeral=True)
            return
        await interaction.response.send_message("Cog loaded!", ephemeral=True)

    @nextcord.slash_command(
        description="Reloads a cog",
        default_member_permissions=8,
    )
    @utils.Utils().get_permission_level(0)
    async def reload(self, interaction: Interaction, cog: str = SlashOption(name="cog", required=True)):
        try:
            self.bot.reload_extension(cog)
        except:
            await interaction.response.send_message("Cog not found!", ephemeral=True)
            return
        await interaction.response.send_message("Cog reloaded!", ephemeral=True)
    
    @nextcord.slash_command(
        description="Restarts the bot",
        default_member_permissions=8,
    )
    @utils.Utils().get_permission_level(1)
    async def restart(self, interaction: Interaction):
        await interaction.response.send_message("Restarting...", ephemeral=True)
        await self.bot.close()

    @nextcord.slash_command(
        description="Pings the bot",
    )
    @cooldowns.cooldown(1, 10, bucket=cooldowns.buckets.SlashBucket.author)
    async def ping(self, interaction: Interaction):
        await interaction.response.send_message(f"Pong! {round(self.bot.latency * 1000)}ms", ephemeral=True)

    class test_view(nextcord.ui.View):
        def __init__(self):
            super().__init__()

        @nextcord.ui.button(label="Test", style=nextcord.ButtonStyle.primary)
        @cooldowns.cooldown(1, 10, bucket=cooldowns.buckets.SlashBucket.author)
        async def test(self, button: nextcord.ui.Button, interaction: Interaction):
            await interaction.response.send_message("You pressed the button!")


    @nextcord.slash_command(
        description="Test button (dev only)",
        default_member_permissions=8,
    )
    @utils.Utils().get_permission_level(8)
    async def testbutton(self, interaction: Interaction):
        view = self.test_view()
        await interaction.response.send_message("Test", view=view)

    @nextcord.slash_command(
        description="Demote",
        default_member_permissions=8,
    )
    @utils.Utils().get_permission_level(3)
    @cooldowns.cooldown(1, 10, bucket=cooldowns.buckets.SlashBucket.author)
    async def demote(self, interaction: Interaction, user: nextcord.Member = SlashOption(name="user", required=True), rank_strip: bool = SlashOption(name="rank_strip", required=False)):
        await interaction.defer()
        await utils.Utils().demote(user, rank_strip)
        await interaction.followup.send(f"Demoted {user.mention}!", ephemeral=True)

    # Set status command where you can choose the status and what if it is playing, streaming, listening, watching, or competing
    @nextcord.slash_command(
        description="Sets the bot's status",
        default_member_permissions=8,
    )
    @utils.Utils().get_permission_level(1)
    async def status(self, interaction: Interaction, type: str = SlashOption(name="type", required=True, choices=["playing", "streaming", "listening", "watching", "competing"]), status: str = SlashOption(name="status", required=False), online_status: str = SlashOption(name="online_status", required=False, choices=["online", "idle", "dnd", "invisible"])):
        if online_status == "dnd":
            online_status = nextcord.Status.dnd
        elif online_status == "idle":
            online_status = nextcord.Status.idle
        elif online_status == "invisible":
            online_status = nextcord.Status.invisible
        if type == "playing":
            await self.bot.change_presence(activity=nextcord.Game(name=status), status=online_status)
        elif type == "streaming":
            await self.bot.change_presence(activity=nextcord.Streaming(name=status, url="https://twitch.tv/"), status=online_status)
        elif type == "listening":
            await self.bot.change_presence(activity=nextcord.Activity(type=nextcord.ActivityType.listening, name=status), status=online_status)
        elif type == "watching":
            await self.bot.change_presence(activity=nextcord.Activity(type=nextcord.ActivityType.watching, name=status), status=online_status)
        elif type == "competing":
            await self.bot.change_presence(activity=nextcord.Activity(type=nextcord.ActivityType.competing, name=status), status=online_status)
        await interaction.response.send_message("Status set!", ephemeral=True)

    # Eval command
    @nextcord.slash_command(
        description="Evaluates a command",
        default_member_permissions=8,
    )
    @utils.Utils().get_permission_level(0)
    async def eval(self, interaction: Interaction, code: str = SlashOption(name="code", required=True)):
        try:
            await interaction.response.defer()
            old_stdout = sys.stdout
            sys.stdout = mystdout = StringIO()
            code = codecs.decode(code, 'unicode_escape')
            result = eval(code, globals(), locals())
            if inspect.isawaitable(result):
                result = await result

            sys.stdout = old_stdout
            result = (str(result) + "\n" + mystdout.getvalue())[:1988]
            await interaction.followup.send(f"```py\n{result}\n```", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"```{e}```", ephemeral=True)
    
    # Cycle status command
    @nextcord.slash_command(
        description="Cycles the bot's status",
        default_member_permissions=8,
    )
    @utils.Utils().get_permission_level(1)
    async def cycle_status(self, interaction: Interaction):
        await interaction.response.send_message("Cycling status...", ephemeral=True)
        await utils.Utils().update_status(self.bot)
    
    # Listen for errors
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # Send error to owner
        await self.bot.get_user(305246941992976386).send(f"Error in {ctx.guild.name} ({ctx.guild.id}) in {ctx.channel.name} ({ctx.channel.id}) by {ctx.author.name} ({ctx.author.id}): {error}")
    
    # On application error
    @commands.Cog.listener()
    async def on_application_command_error(self, interaction: Interaction, error):
        error = getattr(error, "original", error)

        if isinstance(error, CallableOnCooldown):
            # Create embed
            embed = nextcord.Embed(
                title="Cooldown",
                description=f"You are being rate-limited! Retry <t:{int(error.resets_at.timestamp())}:R>.",
                color=0xff0000
            )
            # Send embed
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif isinstance(error, nextcord.errors.ApplicationCheckFailure):
            # Create embed
            embed = nextcord.Embed(
                title="Error",
                description=f"You do not have permission to use this command.",
                color=0xff0000
            )
            # Send embed
            await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            # Create UUID
            uuid = ''.join([choice(ascii_lowercase) for _ in range(32)])
            # Create embed
            message = interaction.message.content if interaction.message else None
            r = requests.post("https://discord.com/api/webhooks/1094252579753570314/c2F8lOLZi4mWh1E7ykGPLy32sGrpz4VrUoqZPfeE8GCRX2z2UtKu2WnA79J_UN66frBK", json={"content": f"ID: ``{uuid}``\nAttempted by: {interaction.user}\nIn: <#{interaction.channel.id}>\nCommand: {interaction.application_command.name}```{error}```Message: {message}"})
            embed = nextcord.Embed(
                title="Error",
                description=f"Ooh no! An error occured!\n Please report this to Super02#1337 including the ID below, if this is unintended.",
                color=0xff0000
            )
            embed.add_field(name="ID:", value=f"``{uuid}``")

            # Send embed
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)
            raise error

    # Command to send a DM to a user
    @nextcord.slash_command(
        description="Sends a DM to a user",
        default_member_permissions=8,
    )
    @utils.Utils().get_permission_level(2)
    async def dm(self, interaction: Interaction, user: nextcord.User = SlashOption(name="user", required=True), message: str = SlashOption(name="message", required=True)):
        try:
            await user.send(message)
        except:
            await interaction.response.send_message("Could not send DM!", ephemeral=True)
            return
        requests.post("https://discord.com/api/webhooks/1105131060066537494/MS1OZjjgy8wBJE32bP4ExcqfCIvQc8LoLva-nI6EfAZkDsDsZ9KYhz6Ky4CMMKW-zBkw", json={"content": f"**DM sent to user**\nDone by: {interaction.user} ({interaction.user.id})\nMessage: {message}\nSent to: {user.name} ({user.id})"})
        await interaction.response.send_message("DM sent!", ephemeral=True)

    # Block a user from messaging the bot
    @nextcord.slash_command(
        description="Blocks a user from messaging the bot",
    )
    @utils.Utils().get_permission_level(8)
    @cooldowns.cooldown(1, 3, bucket=cooldowns.buckets.SlashBucket.author)
    async def block(self, interaction: Interaction, user: nextcord.User = SlashOption(name="user", required=True)):
        # Check if user is already blocked
        db_user = await db.user.find_first(where={"discord_id": str(user.id)})
        if db_user is None:
            await db.user.create({"discord_id": str(user.id), "dm_blacklist": True})
        else:
            if db_user.dm_blacklist:
                return await interaction.response.send_message("User is already blocked!", ephemeral=True)
            await db.user.update(where={"discord_id": str(user.id)}, data={"dm_blacklist": True})
        # Add user to blacklist
        await utils.Utils().server_log(f"**User blocked**\nDone by: {interaction.user} ({interaction.user.id})\nBlocked: {user.name} ({user.id})", self.bot)
        await interaction.response.send_message("User blocked!", ephemeral=True)

    # Export DMS
    @nextcord.slash_command(
        description="Exports all DMs",
    )
    @utils.Utils().get_permission_level(4)
    async def export_dms(self, interaction: Interaction, user: str = SlashOption(name="user", required=True)):
        # Get all DMs
        user = await self.bot.fetch_user(int(user))
        dms = await user.history(limit=None, oldest_first=True).flatten()
        # Check if there are any
        if len(dms) == 0:
            return await interaction.response.send_message("No DMs found!", ephemeral=True)
        # Create file
        file = nextcord.File(StringIO("\n".join([f"{dm.created_at} {dm.author.name} ({dm.author.id}): {dm.content}" + (str(dm.attachments) if dm.attachments else "") for dm in dms])), filename="dms.txt")
        # Send file
        await interaction.response.send_message("DMs exported!", file=file, ephemeral=True)

    # Unblock a user from messaging the bot
    @nextcord.slash_command(
        description="Unblocks a user from messaging the bot",
    )
    @utils.Utils().get_permission_level(2)
    @cooldowns.cooldown(1, 3, bucket=cooldowns.buckets.SlashBucket.author)
    async def unblock(self, interaction: Interaction, user: nextcord.User = SlashOption(name="user", required=True)):
        # Check if user is blocked
        db_user = await db.user.find_first(where={"discord_id": str(user.id)})
        if db_user is None:
            return await interaction.response.send_message("User is not blocked! <:amogus:1096138125232840756>", ephemeral=True)
        else:
            if not db_user.dm_blacklist:
                return await interaction.response.send_message("User is not blocked!", ephemeral=True)
            await db.user.update(where={"discord_id": str(user.id)}, data={"dm_blacklist": False})
        # Add user to blacklist
        await interaction.response.send_message("User unblocked!", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.reference is not None and message.channel.id == 1026217717474283702 and message.author.id != self.bot.user.id:
            target_msg = await message.channel.fetch_message(message.reference.message_id)
            if target_msg.author.id != self.bot.user.id:
                return
            # Check if reply ping is enabled
            if not self.bot.user in message.mentions:
                return
            try:
                await target_msg.mentions[0].send(message.content, files=[await attachment.to_file() for attachment in message.attachments])
            except nextcord.errors.Forbidden:
                # React to the message
                await message.add_reaction("❌")
                return await message.channel.send(f"Error sending DM to <@{target_msg.mentions[0].id}>. User either has his DM's disabled or maybe he is banned from the Discord? <:amogus:1096138125232840756>")
            await message.channel.send(f"DM sent by {message.author.mention} to <@{target_msg.mentions[0].id}>: {message.content}", files=[await attachment.to_file() for attachment in message.attachments])
            await message.delete()

def setup(bot):
  bot.add_cog(devtools(bot))
