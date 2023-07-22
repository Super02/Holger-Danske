import nextcord
from datetime import datetime, timedelta
from utils import db
from nextcord.ext import commands
import utils
from nextcord.ext import tasks
from nextcord import SlashOption
import cooldowns
import requests
import os
import math
import base64


class AgeVerify(nextcord.ext.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_age.start()
        self.ageverify_phrases = ["https://web.roblox.com/"]
        self.spam_control = []
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_modal(Redo(self.bot))

    @tasks.loop(minutes=5.0)
    async def check_age(self):
        for entry in await db.ageverification.find_many():
            if entry.time_limit != None and datetime.now(entry.time_limit.tzinfo) > entry.time_limit and entry.verified == False:
                try:
                    user = await self.bot.fetch_user(int(entry.discord_id))
                    await self.age_timeout(user)
                except Exception as e:
                    print(e)
                    await db.ageverification.delete(where={"id": entry.id})

    async def age_timeout(self, user):
        database_user = await db.ageverification.find_first(where={"discord_id": str(user.id)})
        if(database_user != None):
            member = await self.bot.get_guild(utils.Utils().guild_id).fetch_member(user.id)
            # Check if user has the age verified role
            role = self.bot.get_guild(utils.Utils().guild_id).get_role(utils.Utils().age_verified_role_id)
            if role in member.roles:
                return
            await user.send("You have failed to verify your age in time. You have been banned from the server.")
            await member.ban(reason="Failed to verify age in time", delete_message_days=0)
            await db.ageverification.delete(where={"id": database_user.id})
            await utils.Utils().server_log(f"User {member} failed to verify in time!", self.bot)

    @nextcord.slash_command(name="ageverify", description="Request age verification from a user")
    @utils.Utils().get_permission_level(8)
    @cooldowns.cooldown(1, 5, bucket=cooldowns.SlashBucket.author)
    async def ageverify(self, interaction, user: nextcord.Member, hours: int = SlashOption(name="hours", required=False, description="By default 24 hours (Set to 0 if you want timeout to be in minutes)"), minutes: int = SlashOption(name="minutes", required=False, description="By default 0 minutes")):
        await interaction.response.defer()
        if hours == 0 and minutes == 0:
            await interaction.followup.send("Hours and minutes cannot both be 0!", ephemeral=True)
            return
        # Check if user is a bot
        if user.bot:
            return await interaction.followup.send("User is a bot!", ephemeral=True)
        hours = hours if hours != None else 24
        minutes = minutes if minutes != None else 0
        # get age verified role
        role = self.bot.get_guild(utils.Utils().guild_id).get_role(utils.Utils().age_verified_role_id)
        # Check if has age verified role
        try:
            member = await self.bot.get_guild(utils.Utils().guild_id).fetch_member(user.id)
        except nextcord.NotFound:
            return await interaction.followup.send("User is not in the server!", ephemeral=True)
        timelimit = datetime.utcnow() + timedelta(hours=hours, minutes=minutes)
        if role in member.roles:
            await interaction.followup.send("User is already age verified!", ephemeral=True)
            return
        # Check if user is already in database
        if await db.ageverification.find_first(where={"discord_id": str(user.id)}):
            return await interaction.followup.send("User is already targeted for age check!", ephemeral=True)
        try:
            message = await user.send("You have been requested to complete age verification!")
            requests.post("https://discord.com/api/webhooks/1109824848944959488/p5YrOOyH3DVbnJwqtnczZbIhRKr5-dtovHUQqDf3KnZQeXkRHR0CzF7kIqVOaUjyN_i9", json={"content": f"User {user.mention} has been requested to complete age verification by {interaction.user.mention} ({interaction.user.id}) they have been given until <t:{int(timelimit.timestamp())}:f>"})
            db_entry = await db.ageverification.create(data={
                "discord_id": str(user.id),
                "time_limit": timelimit,
                "requested_by": str(interaction.user.id),
            })
            embed = nextcord.Embed(title="Age Verification", description=f"A moderator has requested that you complete age verification. Please verify using any of the options below. You must verify before: <t:{int(timelimit.timestamp())}:f>", color=0x00FF00)
            embed = self.add_embed_fields(embed)
            await message.edit(embed=embed)
            # Send a webhook to log the request
            await interaction.followup.send(f"{user} has been requested to complete age verification!")
        except:
            message = await self.bot.get_channel(820257824923058186).send(content=f"{user.mention} since you have DM's disabled I have sent the message here. Please enable DM's and message the bot complying with the required information.")
            requests.post("https://discord.com/api/webhooks/1109824848944959488/p5YrOOyH3DVbnJwqtnczZbIhRKr5-dtovHUQqDf3KnZQeXkRHR0CzF7kIqVOaUjyN_i9", json={"content": f"User {user.mention} has been requested to complete age verification by {interaction.user.mention} ({interaction.user.id}) they have been given until <t:{int(timelimit.timestamp())}:f>"})
            db_entry = await db.ageverification.create(data={
                "discord_id": str(user.id),
                "time_limit": timelimit,
                "requested_by": str(interaction.user.id),
            })
            embed = nextcord.Embed(title="Age Verification", description=f"A moderator has requested that you complete age verification. Please verify using any of the options below. You must verify before: <t:{int(timelimit.timestamp())}:f>", color=0x00FF00)
            embed = self.add_embed_fields(embed)
            await message.edit(embed=embed)
            await message.edit(embed=embed)
            await interaction.followup.send("User has been notified! In <#820257824923058186> as they have their DM's disabled")
            return
        
    
    @nextcord.slash_command(name="ageverify_cancel", description="Cancel age verification for a user")
    @utils.Utils().get_permission_level(8)
    @cooldowns.cooldown(1, 5, bucket=cooldowns.SlashBucket.author)
    async def ageverify_cancel(self, interaction, user: nextcord.Member, reason: str = SlashOption(name="reason", required=False, description="Reason for cancelling age verification")):
        await interaction.response.defer()
        # Check if user is in database
        database_user = await db.ageverification.find_first(where={"discord_id": str(user.id)})
        if(database_user == None):
            await interaction.followup.send("User is not targeted for age check!", ephemeral=True)
            return
        # Check if user has already been verified
        if(database_user.verified == True):
            await interaction.followup.send("User has already been verified!", ephemeral=True)
            return
        # Check if user has already been timed out
        if database_user.time_limit != None and database_user.time_limit < datetime.now(database_user.time_limit.tzinfo):
            await interaction.followup.send("User has already been timed out!", ephemeral=True)
            return
        # Delete user from database
        await db.ageverification.delete(where={"id": database_user.id})
        # Delete message
        try:
            message = await self.bot.get_channel(1071902019964633200).fetch_message(database_user.messageId)
            await message.delete()
        except:
            pass
        # Send message to user
        await utils.Utils().server_log(f"Age verification for {user.mention} has been cancelled by {interaction.user.id}.\n Reason: {reason}", self.bot)
        try:
            await user.send(f"Your age verification has been cancelled.\nReason: {reason}")
        except:
            return await interaction.followup.send("Age verification cancelled (User could not be notified)", ephemeral=True)
        await interaction.followup.send("User has been notified!", ephemeral=True)

    @nextcord.slash_command(name="ageverify_get_id", description="Get a users case number/id from their Discord name/id")
    @utils.Utils().get_permission_level(8)
    async def ageverify_get_id(self, interaction, user: nextcord.User):
        await interaction.response.defer()
        case_number = await db.ageverification.find_first(where={"discord_id": str(user.id)})
        if case_number == None:
            await interaction.followup.send("User is not targeted for age check!", ephemeral=True)
            return
        await interaction.followup.send(f"Case number {user.mention}: {case_number.id}")

    @nextcord.slash_command(name="ageverify_list", description="List all users targeted for age verification")
    @utils.Utils().get_permission_level(8)
    @cooldowns.cooldown(1, 5, bucket=cooldowns.SlashBucket.author)
    async def ageverify_list(self, interaction, page: int = SlashOption(name="page", required=False, description="Page number to view", default=1)):
        await interaction.response.defer()
        # Get all users from database
        database_users = await db.ageverification.find_many(skip=(page-1)*7, take=7, where={"verified": False, "time_limit": {"gte": datetime.now(datetime.now().astimezone().tzinfo)}}, order={"id": "desc"})
        database_size = await db.ageverification.count(where={"verified": False, "time_limit": {"gte": datetime.now(datetime.now().astimezone().tzinfo)}})
        print(database_size)
        # Create embed
        embed = nextcord.Embed(title="Age Verification", description="List of all users targeted for age verification.", color=0x00FF00)
        for database_user in database_users:
            # Check if user has already been verified
            if(database_user.verified == False and database_user.time_limit != None and database_user.time_limit > datetime.now(database_user.time_limit.tzinfo)):
                embed.add_field(name=f"User: {database_user.discord_id}", value=f"ID: {database_user.id}\nVerify <t:{int(database_user.time_limit.timestamp())}:R>", inline=False)
        embed.set_footer(text=f"Page {page} of {math.ceil(database_size/7)-1}")
        await interaction.followup.send(embed=embed)
    
    @nextcord.slash_command(name="ageverify_status", description="Get status from an age verification by ID")
    @utils.Utils().get_permission_level(4)
    async def ageverify_status(self, interaction, id: int):
        await interaction.response.defer()
        # Get user from database
        database_user = await db.ageverification.find_first(where={"id": id})
        if(database_user == None):
            await interaction.followup.send("User is not targeted for age check! (Or maybe he is banned?)", ephemeral=True)
            return
        # Get user from discord
        user = await self.bot.fetch_user(int(database_user.discord_id))
        # Create embed
        verify_within = "<t:"+str(int(database_user.time_limit.timestamp()))+":R>" if database_user.time_limit else False
        embed = nextcord.Embed(title="Age Verification", description=f"Status for age verification with ID: {database_user.id}", color=0x00FF00)
        embed.add_field(name=f"User: {user}", value=f"Case Number: #{database_user.id}\nMust verify {verify_within}\nRequested by: {await self.bot.fetch_user(database_user.requested_by)}\nRequested: <t:{int(database_user.date.timestamp())}:R>\nVerified: {database_user.verified}\nVerified by: {database_user.verified_by}", inline=False)
        await interaction.followup.send(embed=embed)
    
    @nextcord.slash_command(name="ageverify_approve", description="Approve a users age verification")
    @utils.Utils().get_permission_level(4)
    @cooldowns.cooldown(1, 5, bucket=cooldowns.SlashBucket.author)
    async def ageverify_approve(self, interaction, id: int):
        await interaction.response.defer()
        # Get user from database
        database_user = await db.ageverification.find_first(where={"id": id})
        if(database_user == None):
            await interaction.followup.send("User is not targeted for age check!", ephemeral=True)
            return
        # Check if user has already been verified
        if(database_user.verified == True):
            await interaction.followup.send("User has already been verified!", ephemeral=True)
            return
        # Check if user has already been timed out
        if database_user.time_limit != None and database_user.time_limit < datetime.now(database_user.time_limit.tzinfo):
            await interaction.followup.send("User has already been timed out!", ephemeral=True)
            return
        # Get user from discord
        user = self.bot.get_user(int(database_user.discord_id))
        # Update user in database
        await db.ageverification.update(where={"id": id}, data={"time_limit": None, "verified": True, "verified_by": str(interaction.user.id)})
        # Send message to user
        # Get age verified role
        age_verified_role = self.bot.get_guild(utils.Utils().guild_id).get_role(utils.Utils().age_verified_role_id)
        # Add role to user
        member = self.bot.get_guild(utils.Utils().guild_id).get_member(user.id)
        await member.add_roles(age_verified_role)
        await user.send("Your age verification has been approved. You are now age verified. ")
        await interaction.followup.send("User has been approved!", ephemeral=True)
        await utils.Utils().server_log(f"User {user} has been approved for age verification by {interaction.user.id}!", self.bot)
        await interaction.message.delete()
    
    @nextcord.slash_command(name="ageverify_deny", description="Deny a users age verification")
    @utils.Utils().get_permission_level(4)
    @cooldowns.cooldown(1, 5, bucket=cooldowns.SlashBucket.author)
    async def ageverify_deny(self, interaction, id: int):
        await interaction.response.defer()
        # Get user from database
        database_user = await db.ageverification.find_first(where={"id": id})
        if(database_user == None):
            await interaction.followup.send("User is not targeted for age check!", ephemeral=True)
            return
        # Check if user has already been verified
        if(database_user.verified == True):
            await interaction.followup.send("User has already been verified!", ephemeral=True)
            return
        # Check if user has already been timed out
        if(database_user.time_limit < datetime.utcnow(tz=database_user.time_limit.tzinfo)):
            await interaction.followup.send("User has already been timed out!", ephemeral=True)
            return
        # Get user from discord
        user = self.bot.get_user(int(database_user.discord_id))
        # Delete user from database
        await db.ageverification.update(where={"id": id}, data={"verified": False, "time_limit": None})
        # Delete message
        message = await self.bot.get_channel(1071902019964633200).fetch_message(database_user.messageId)
        await message.delete()
        # Send message to user
        try:
            await user.send("Your age verification has been denied.")
            member = self.bot.get_guild(utils.Utils().guild_id).get_member(int(database_user.discord_id))
            await member.ban(reason=f"Age verification denied. By {interaction.user}")
        except:
            return await interaction.followup.send("User has been denied, but could not be banned! (Please ban him manually)", ephemeral=True)
        await interaction.followup.send("User has been banned!", ephemeral=True)
    
    @nextcord.slash_command(name="ageverify_extend", description="Extend a users age verification")
    @utils.Utils().get_permission_level(8)
    @cooldowns.cooldown(1, 5, bucket=cooldowns.SlashBucket.author)
    async def ageverify_extend(self, interaction, id: int, hours: int = SlashOption(name="hours", required=False, description="By default 24 hours (Set to 0 if you want timeout to be in minutes)"), minutes: int = SlashOption(name="minutes", required=False, description="By default 0 minutes")):
        await interaction.response.defer()
        if hours == 0 and minutes == 0:
            await interaction.followup.send("You must set either hours or minutes!", ephemeral=True)
            return
        if hours == None:
            hours = 0
        if minutes == None:
            minutes = 0
        # Get user from database
        database_user = await db.ageverification.find_first(where={"id": id})
        if(database_user == None):
            await interaction.followup.send("User is not targeted for age check!", ephemeral=True)
            return
        # Check if user has already been verified
        if(database_user.verified == True):
            await interaction.followup.send("User has already been verified!", ephemeral=True)
            return
        # Check if user has already been timed out
        if database_user.time_limit != None and database_user.time_limit < datetime.now(database_user.time_limit.tzinfo):
            await interaction.followup.send("User has already been timed out!", ephemeral=True)
            return
        # Get user from discord
        user = self.bot.get_user(int(database_user.discord_id))
        # Update user in database
        await db.ageverification.update(where={"id": id}, data={"time_limit": database_user.time_limit + timedelta(hours=hours, minutes=minutes)})
        # Send message to user
        await user.send(f"Your age verification has been extended with {hours} hours and {minutes} minutes untill <t:{int(database_user.time_limit.timestamp())}:f>.")
        await utils.Utils().server_log(f"User {user} has been extended for age verification by {interaction.user.id}!", self.bot)
        await interaction.followup.send("User has been extended!", ephemeral=True)


    class AgeVerification(nextcord.ui.View):
        def __init__(self, bot):
            super().__init__(
                timeout=None,
                auto_defer=True
            )
            self.bot = bot

        @nextcord.ui.button(label="Approve", style=nextcord.ButtonStyle.green, custom_id="ageverify:approve")
        async def approve_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
            # Get user from database
            database_user = await db.ageverification.find_first(where={"messageId": str(interaction.message.id)})
            if(database_user == None):
                await interaction.response.send_message("User is not targeted for age check!", ephemeral=True)
                return
            # Check if user has already been verified
            if(database_user.verified == True):
                await interaction.response.send_message("User has already been verified!", ephemeral=True)
                return
            # Check if user has already been timed out
            if database_user.time_limit != None and database_user.time_limit < datetime.now(database_user.time_limit.tzinfo):
                await interaction.response.send_message("User has already been timed out!", ephemeral=True)
                return
            # Get user from discord
            user = self.bot.get_user(int(database_user.discord_id))
            # Update user in database
            await db.ageverification.update(where={"id": database_user.id}, data={"time_limit": None, "verified": True, "verified_by": str(interaction.user.id)})
            # Get age verified role
            age_verified_role = self.bot.get_guild(utils.Utils().guild_id).get_role(utils.Utils().age_verified_role_id)
            # Add role to user
            member = self.bot.get_guild(utils.Utils().guild_id).get_member(int(database_user.discord_id))
            await member.add_roles(age_verified_role)
            # Send message to user
            await user.send("Your age verification has been approved. You are now age verified.")
            await interaction.response.send_message("User has been approved!", ephemeral=True)
            await utils.Utils().server_log(f"User {user.mention} has been approved by {interaction.user.id}!", self.bot)
            await interaction.message.delete()

        @nextcord.ui.button(label="Deny", style=nextcord.ButtonStyle.red, custom_id="ageverify:deny")
        async def deny_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
            # Get user from database
            database_user = await db.ageverification.find_first(where={"messageId": str(interaction.message.id)})
            if(database_user == None):
                await interaction.response.send_message("User is not targeted for age check!", ephemeral=True)
                return
            # Check if user has already been verified
            if(database_user.verified == True):
                await interaction.response.send_message("User has already been verified!", ephemeral=True)
                return
            # Check if user has already been timed out
            if database_user.time_limit != None and database_user.time_limit < datetime.now(database_user.time_limit.tzinfo):
                await interaction.response.send_message("User has already been timed out!", ephemeral=True)
                return
            # Get user from discord
            user = await self.bot.fetch_user(int(database_user.discord_id))
            # Delete user from database
            await db.ageverification.update(where={"messageId": str(interaction.message.id)}, data={"verified": False, "time_limit": None})
            # Send message to user
            try:
                await user.send("Your age verification has been denied.")
                member = await self.bot.get_guild(utils.Utils().guild_id).fetch_member(user.id)
                await member.ban(reason=f"Age verification denied. By {interaction.user}")
                await utils.Utils().server_log(f"User {user.mention} has been denied by {interaction.user.id}!", self.bot)
                await interaction.response.send_message("User has been banned!", ephemeral=True)
            except:
                await utils.Utils().server_log(f"User {user.mention} has been denied by {interaction.user.id}!", self.bot)
                await interaction.response.send_message("User has been denied! But could not be banned. Please ban him manually!", ephemeral=True)
            await interaction.message.delete()

        
        @nextcord.ui.button(label="Redo", style=nextcord.ButtonStyle.blurple, custom_id="ageverify:redo")
        async def redo_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
            # Get user from database
            database_user = await db.ageverification.find_first(where={"messageId": str(interaction.message.id)})
            if(database_user == None):
                await interaction.response.send_message("User is not targeted for age check!", ephemeral=True)
                return
            # Check if user has already been verified
            if(database_user.verified == True):
                await interaction.response.send_message("User has already been verified!", ephemeral=True)
                return
            # Check if user has already been timed out
            if database_user.time_limit != None and database_user.time_limit < datetime.now(database_user.time_limit.tzinfo):
                await interaction.response.send_message("User has already been timed out!", ephemeral=True)
                return
            # Send redo modal
            await interaction.response.send_modal(Redo(self.bot))


        @nextcord.ui.button(label="Cancel", style=nextcord.ButtonStyle.gray, custom_id="ageverify:cancel")
        async def cancel_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
            # Get user from database
            database_user = await db.ageverification.find_first(where={"messageId": str(interaction.message.id)})
            if(database_user == None):
                await interaction.response.send_message("User is not targeted for age check!", ephemeral=True)
                return
            # Check if user has already been verified
            if(database_user.verified == True):
                await interaction.response.send_message("User has already been verified!", ephemeral=True)
                return
            # Check if user has already been timed out
            if database_user.time_limit != None and database_user.time_limit < datetime.now(database_user.time_limit.tzinfo):
                await interaction.response.send_message("User has already been timed out!", ephemeral=True)
                return
            # Delete user from database
            await db.ageverification.delete(where={"messageId": str(interaction.message.id)})
            # Delete message
            message = await self.bot.get_channel(1071902019964633200).fetch_message(database_user.messageId)
            await message.delete()
            user = await self.bot.fetch_user(database_user.discord_id)
            # Send message to user
            await user.send("Your age check has been cancelled.")
            await utils.Utils().server_log(f"User {interaction.user.id} has cancelled the age check for {user}", self.bot)
            await interaction.response.send_message("User's age check has been cancelled!", ephemeral=True)

    # On ready event
    @commands.Cog.listener()
    async def on_ready(self):
        print("Age Verification Cog is ready!")
        # Add persistent view
        self.bot.add_view(self.AgeVerification(self.bot))

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # Check if user exists in database
        database_user = await db.ageverification.find_first(where={"discord_id": str(member.id)})
        if(database_user == None or database_user.verified == True or (database_user.time_limit != None and database_user.time_limit < datetime.now(database_user.time_limit.tzinfo))):
            return
        # Delete user from database
        await db.ageverification.delete(where={"discord_id": str(member.id)})
        # Delete message
        try:
            message = await self.bot.get_channel(1071902019964633200).fetch_message(database_user.messageId)
            await message.delete()
        except:
            pass
        async for entry in self.bot.get_guild(utils.Utils().guild_id).audit_logs(action=nextcord.AuditLogAction.ban):
            if entry.target.id == member.id:
                return
        async for entry in self.bot.get_guild(utils.Utils().guild_id).audit_logs(action=nextcord.AuditLogAction.kick):
            if entry.target.id == member.id:
                return
        # Send message to user
        await utils.Utils().server_log(f"User {member.mention} has left the server. Their age verification has been cancelled. The user has been banned. Age verification requested by {database_user.requested_by}", self.bot)
        await member.ban(reason="User has left the server before being age verified.", delete_message_seconds=0)

    def add_embed_fields(self, embed):
        embed.add_field(name="Verify by ID", value=f"You can verify by ID by sending a picture of some kind of ID. You are allowed to blur out anything that is not your date of birth to ensure privacy. If you are born before 2000 please contact staff either before or after submitting your ID for further questions (This is to prevent people from submitting their parents ID)", inline=True)
        embed.add_field(name="Already verified?", value="If you have a note from the Dyno bot proving you are age verified then send a message to the bot just saying: ``already_verified``. **If you use this without having a note from Dyno proving that you are age verified, you will be banned!**", inline=False)
        embed.add_field(name="Privacy notice", value="By sending the bot any messages you accept that your information may be shared with anyone apart of the \"staff team\" (Anyone with access to view staff channels in the Slap Battles Discord). Your information is not stored by the bot and only shared to the staff team by using the image url. If you wish to remove the image you shared with the bot you can do so by deleting the image from the Discord chat with the bot. But please only do this after you have been verified. For any questions about privacy, how your data is handled or any requests regarding GDPR regulation please contact Super02#1337", inline=False)
        embed.add_field(name="What server does this regard?", value=f"This bot is from the Slap Battles Discord, and is a bot developed by Super02#1337 (An overseer in the Discord) if you have any doubts about the bot you are welcome to contact staff in the Slap Battles Discord with your concerns.", inline=False)
        embed.add_field(name="Support", value=f"If you have any questions just send them directly to the bot and they will be forwarded to the staff team. Send us a message if you need extended time to complete your age verification, with an explanation why you need extra time.", inline=False)
        return embed

    # On message event
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user or utils.Utils().get_permission_level(2).predicate(message.author, custom=True) or message.author.bot:
            return
        # Check if any of the entries in self.blocked_phrases are in message.content
        if any(x in message.content.lower() for x in self.ageverify_phrases):
            # Check if user already exists in database and check if they have the age verified role
            age_verified_role = self.bot.get_guild(utils.Utils().guild_id).get_role(utils.Utils().age_verified_role_id)
            database_user = await db.ageverification.find_first(where={"discord_id": str(message.author.id)})
            try:
                if(database_user != None or age_verified_role in message.author.roles):
                    return
            except AttributeError:
                return
            timelimit = datetime.utcnow() + timedelta(hours=10)
            try:
                msg = await message.author.send("You have been automatically requested to complete age verification!")
                requests.post("https://discord.com/api/webhooks/1109824848944959488/p5YrOOyH3DVbnJwqtnczZbIhRKr5-dtovHUQqDf3KnZQeXkRHR0CzF7kIqVOaUjyN_i9", json={"content": f"User {message.author.mention} has been requested to complete age verification by Holger Danske they have been given until <t:{int(timelimit.timestamp())}:f>"})
                db_entry = await db.ageverification.create(data={
                    "discord_id": str(message.author.id),
                    "time_limit": timelimit,
                    "requested_by": str(self.bot.user.id),
                })
                case_number = db_entry.id
                embed = nextcord.Embed(title="Age Verification", description=f"You have been selected for an automatic verification check (Because you said a phrase that triggered the bot). Please verify using any of the options below. You must verify before: <t:{int(timelimit.timestamp())}:f>", color=0x00FF00)
                embed = self.add_embed_fields(embed)
                await msg.edit(embed=embed)
            except Exception as e:
                print(e)
                msg = await self.bot.get_channel(820257824923058186).send(content=f"{message.author.mention} since you have DM's disabled I have sent the message here. Please enable DM's and message the bot complying with the required information.")
                requests.post("https://discord.com/api/webhooks/1109824848944959488/p5YrOOyH3DVbnJwqtnczZbIhRKr5-dtovHUQqDf3KnZQeXkRHR0CzF7kIqVOaUjyN_i9", json={"content": f"User {message.author.mention} has been requested to complete age verification by Holger Danske they have been given until <t:{int(timelimit.timestamp())}:f>"})
                db_entry = await db.ageverification.create(data={
                    "discord_id": str(message.author.id),
                    "time_limit": timelimit,
                    "requested_by": str(message.author.id),
                })
                case_number = db_entry.id
                embed = nextcord.Embed(title="Age Verification", description=f"A moderator has requested that you complete age verification. Please verify using any of the options below. You must verify before: <t:{int(timelimit.timestamp())}:f>", color=0x00FF00)
                embed = self.add_embed_fields(embed)
                await msg.edit(embed=embed)
                return
        # Check if message is in DM
        if message.author == self.bot.user:
            return
        if(message.guild == None):
            # Check if message is from a user in the database
            database_user = await db.ageverification.find_first(where={"discord_id": str(message.author.id)})
            if(database_user != None and database_user.time_limit != None):
                if(message.content.lower() == "already_verified"):
                    embed = nextcord.Embed(title="Age Verification", description=f"{message.author.mention} has completed age verification. Please review their documents and verify them.", color=0x00FF00)
                    embed.add_field(name="User", value=f"{message.author.mention} ({message.author})", inline=True)
                    embed.add_field(name="Case Number", value=f"#{database_user.id}", inline=True)
                    embed.add_field(name="Requested by", value=f"{self.bot.get_user(int(database_user.requested_by)).mention} ({self.bot.get_user(int(database_user.requested_by))})", inline=True)
                    if(database_user.redone != None and database_user.redone > 0):
                        embed.add_field(name="Redone", value=f"{database_user.redone} times", inline=False)
                    embed.add_field(name="Documents", value=f"User states he is already verified", inline=True)
                    msg = await self.bot.get_channel(1071902019964633200).send(embed=embed, view=self.AgeVerification(self.bot))
                    await db.ageverification.update(where={"id": database_user.id}, data={"time_limit": None, "messageId": str(msg.id)})
                    await message.author.send("Thank you for verifying! The timelimit for this verification has ended and you may procceed as before. Sorry for the inconvenience. You will receieve confirmation once staff have reviewed your documents. When you recieve confirmation on your age verification you may delete the document containing your information. If you have any questions please contact Super02#1337")
                    return
                # Check if message is a picture
                if(message.attachments != []):
                    # Check if message is a picture of an ID
                    if(message.attachments[0].filename.endswith(".png") or message.attachments[0].filename.endswith(".jpg") or message.attachments[0].filename.endswith(".jpeg")):
                            case_number = database_user.id
                            if(database_user.verified == False and database_user.time_limit != None):
                                embed = nextcord.Embed(title="Age Verification", description=f"{message.author.mention} has completed age verification. Please review their documents and verify them.", color=0x00FF00)
                                embed.add_field(name="User", value=f"{message.author.mention} ({message.author})", inline=True)
                                user = await self.bot.fetch_user(int(database_user.requested_by))
                                embed.add_field(name="Requested by", value=f"{user.mention} ({user})", inline=True)
                                embed.add_field(name="Case Number", value=f"#{case_number}", inline=True)
                                if(database_user.redone != None and database_user.redone > 0):
                                    embed.add_field(name="Redone", value=f"{database_user.redone} times", inline=False)
                                embed.add_field(name="Documents", value=f"[Click here to view documents]({message.attachments[0].url})", inline=True)
                                msg = await self.bot.get_channel(1071902019964633200).send(embed=embed, view=self.AgeVerification(self.bot))
                                await db.ageverification.update(where={"id": database_user.id}, data={"time_limit": None, "messageId": str(msg.id)})
                                await message.author.send("Thank you for verifying! The timelimit for this verification has ended and you may procceed as before. Sorry for the inconvenience. You will receieve confirmation once staff have reviewed your documents. When you recieve confirmation on your age verification you may delete the document containing your information. If you have any questions please contact Super02#1337")
                            else:
                                # Send message to user
                                await message.author.send("You have already been verified!")
                    else:
                        # Send message to user
                        await message.author.send("You must attach a picture of an ID! (With a .png, .jpg or .jpeg extension)")
                else:
                    # Send message to user
                    filtered_message = message.content.replace("@", "@\u200E")[:1900]
                    await self.bot.get_channel(1026217717474283702).send(f"DM from {message.author.mention}: {filtered_message}", files=[await attachment.to_file() for attachment in message.attachments])
                    await message.author.send("You must attach a picture of an ID to verify. If your intent was to message support, your message has been forwarded to the staff team.")
            else:
                db_user = await db.user.find_first(where={"discord_id": str(message.author.id)})
                if db_user != None and db_user.dm_blacklist == True:
                    return
                self.spam_control.append(message)
                self.spam_control = list(filter(lambda x: x.created_at > datetime.now(tz=x.created_at.tzinfo) - timedelta(seconds=30), self.spam_control))
                messages = list(filter(lambda x: x.author == message.author, self.spam_control))
                if(len(messages) > 12):
                    if db_user == None:
                        await db.user.create({"discord_id": str(message.author.id), "dm_blacklist": True})
                    else:
                        await db.user.update(where={"discord_id": str(message.author.id)}, data={"dm_blacklist": True})
                    await self.bot.get_channel(1026217717474283702).send(f"{message.author.mention} has been blacklisted from DMing the bot for spamming. Their last message was: {message.content}. They sent over 12 messages in 30 seconds.")
                    self.spam_control = list(filter(lambda x: x.author != message.author, self.spam_control))
                    return
                if "nigger" in message.content or "nigga" in message.content:
                    if db_user == None:
                        await db.user.create({"discord_id": str(message.author.id), "dm_blacklist": True})
                    else:
                        await db.user.update(where={"discord_id": str(message.author.id)}, data={"dm_blacklist": True})
                    return await self.bot.get_channel(1026217717474283702).send(f"{message.author.mention} has been blacklisted from DMing the bot for saying the nword. Offending message: {message.content}.")
                filtered_message = message.content.replace("@", "@\u200E")[:1900]
                await self.bot.get_channel(1026217717474283702).send(f"DM from {message.author.mention}: {filtered_message}", files=[await attachment.to_file() for attachment in message.attachments])
                # Check if this message is the users first message to the bot
                # Get chat history
                async for msg in message.channel.history(limit=1, oldest_first=True):
                    # Check if the message is from the bot
                    if msg.author != self.bot.user:
                        # Check if the message is the same as the message sent
                        if msg.id == message.id:
                            await message.author.send("Since this is your first message sent to the bot. Please note that messages sent to the bot are logged and forwarded to the staff team. If you have any questions please contact Super02#1337")


# Redo modal
class Redo(nextcord.ui.Modal):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(
            "Redo age verification",
            timeout=None,
            custom_id="ageverify:redo:init",
        )
        self.explanation = nextcord.ui.TextInput(
            label="Reason for redo",
            placeholder="Please explain why the user needs to redo the age verification.",
            style=nextcord.TextInputStyle.paragraph,
            required=True,
            max_length=1000,
            custom_id="tickets:redo:field:explanation",
        )
        self.add_item(self.explanation)
    async def callback(self, interaction: nextcord.Interaction) -> None:
        # Get the user from the database
        database_user = await db.ageverification.find_first(where={"messageId": str(interaction.message.id)})
        # Ask the user to redo the age check and set the time limit to 24 hours
        await db.ageverification.update(where={"messageId": str(interaction.message.id)}, data={"time_limit": datetime.now() + timedelta(hours=24), "redone": {'increment': 1}})
        # Delete message
        message = await self.bot.get_channel(1071902019964633200).fetch_message(database_user.messageId)
        await message.delete()
        user = await self.bot.fetch_user(database_user.discord_id)
        # Send message to user
        embed = nextcord.Embed(title="Age Verification redo", description=f"You have been asked to redo your age verification.", color=0x2F3136)
        embed.add_field(name="Reason for redo", value=self.explanation.value)
        embed.add_field(name="Time limit", value=f"<t:{int((datetime.now() + timedelta(hours=24)).timestamp())}:R>")
        embed.add_field(name="Instructions", value="Please follow the instructions previously given to you. If you have any questions please contact staff by sending a message here.", inline=False)
        embed.set_footer(text="Please complete your age verification before the time limit. If you do not complete your age verification before this time, you will be banned. Please note that you may not get another chance to redo your age verification.")
        await user.send(embed=embed)
        await utils.Utils().server_log(f"User {interaction.user.id} has asked {user} to redo their age verification", self.bot)
        await interaction.response.send_message("User has been asked to resubmit their documents!", ephemeral=True)


def setup(bot):
    bot.add_cog(AgeVerify(bot))
