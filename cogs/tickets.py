# A ticket cog that uses discord panels
from nextcord.ext import commands, tasks
from nextcord import Interaction
import nextcord
import utils
import requests
from datetime import datetime, timedelta
import re
import traceback
import math
from mee6_py_api import API
import cooldowns
import os
import calendar
import aiohttp


class tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mee6API = API(820093197933740062)

    # On ready add modal
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_modal(Report(self.bot))
        self.bot.add_modal(Appeal(self.bot))
        self.bot.add_view(CreateReportTicketButton(self.bot))
        self.bot.add_view(CreateAppealTicketButton(self.bot))
        self.bot.add_view(StaffAppealTicketButtons(self.bot))
        self.bot.add_view(StaffReportTicketButtons(self.bot))
        self.bot.add_view(InvestigateAppealTicketButtons())
        self.bot.add_view(InvestigateReportTicketButtons())
        self.check_ticket_amount.start()
        await self.check_ticket_amount()
    
    # Check if ticket amount is over 169, if so, ping the staff team. Only ping again after 24 hours. Check both reporttickets and appealtickets
    @tasks.loop(minutes=20.0)
    async def check_ticket_amount(self):
        # Get all tickets
        tickets = await utils.db.reportticket.count() + await utils.db.appealticket.count()
        # Check if tickets is over 200
        if(tickets > 200):
            lastping = await utils.db.botstorage.find_first(where={"id": 1})
            if lastping != None:
                lastping = lastping.last_ping
            # Check if last ping is over 6 hours ago
            if(lastping == None or lastping < datetime.now(tz=lastping.tzinfo) - timedelta(hours=10)):
                # Ping staff team
                await self.bot.get_channel(1098530872933757019).send("<@&820249824757678080> there are over 200 tickets. Please check them! <:amogus:1096138125232840756>")
                if lastping == None:
                    await utils.db.botstorage.create(data={"id": 1, "last_ping": datetime.now()})
                else:
                    # Set last ping to now
                    await utils.db.botstorage.update(where={"id": 1}, data={"last_ping": datetime.now()})
                if(tickets > 300):
                    start = datetime.now()
                    end = start + timedelta(hours=round(tickets/100) if round(tickets/100) < 10 else 10)
                    multiplier = round(math.log2(tickets)/2-3, 1) if round(math.log2(tickets)/2-3, 1) < 2 else 2
                    if multiplier < 1:
                        multiplier = 1.1
                    await utils.db.ticketpurges.create(data={"multiplier": multiplier, "end": end, "start": start, "created_by": str(self.bot.user.id)})
                    # Send a message to the staff announcement channel
                    embed = nextcord.Embed(title="Ticket purge", description=f"A new ticket purge has been created as there are over 300 tickets! <:amogus:1096138125232840756>", color=nextcord.Color.green())
                    embed.add_field(name="Multiplier", value=f"``{multiplier}``", inline=False)
                    embed.add_field(name="Start", value=f"<t:{int(start.timestamp())}:R>", inline=False)
                    embed.add_field(name="End", value=f"<t:{int(end.timestamp())}:R>", inline=False)
                    await self.bot.get_channel(1098530872933757019).send(embed=embed)
        
        # Check how many percent of staff has completed their quota this month
        start = datetime.today().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
        staff = utils.Utils().get_staff(self.bot, True)
        completed = 0
        for member in staff:
            staff_member = await utils.db.staff.find_first(where={"discord_id": str(member.id)})
            try:
                ticket_amount = await utils.db.ticket.count(where={"staffId": staff_member.id, "date": {"gte": start}})
                ticket_quota = await utils.db.botstorage.find_first(where={"id": 1})
                if(ticket_amount >= ticket_quota.ticket_quota):
                    completed += 1
            except:
                pass
        # Check if completed is over 80%
        percentage = int(completed / len(staff) * 100)
        await utils.db.botstorage.update(where={"id": 1}, data={"quota_complete_percentage": percentage})


    # Persistant ticket blacklist
    @commands.Cog.listener()
    async def on_member_join(self, member):
        db_user = await utils.db.user.find_first(where={"discord_id": str(member.id)})
        if(db_user != None):
            if(db_user.ticket_blacklist):
                # Give ticket blacklist role
                await member.add_roles(self.bot.get_guild(utils.Utils().guild_id).get_role(864248045226819634))
    
    # When a message is deleted in reports or appeals channel, delete the ticket
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        message = payload.cached_message
        if(message == None):
                content = "Message was not cached"
        else:
            content = message.content
        # Check if message is in reports channel
        if(payload.channel_id == 1072630661933965342):
            # Get ticket
            ticket = await utils.db.reportticket.find_first(where={"messageId": str(payload.message_id)})
            if ticket == None:
                return
            # Delete ticket
            await utils.db.reportticket.delete(where={"id": ticket.id})
            async with aiohttp.ClientSession() as session:
                await session.post("https://discord.com/api/webhooks/1091323194671124621/Wlhzf9E4iQKbMkTbsSDtKMbC24k_i8y4P-krPS8qkJJ-svScZerxI_BzyNwwMVTDWxcw", json={"content": f"Message deleted in reports channel: {content} id {payload.message_id}"})
        # Check if message is in appeals channel
        elif(payload.channel_id == 1077293993756463226):
            # Get ticket
            ticket = await utils.db.appealticket.find_first(where={"messageId": str(payload.message_id)})
            if ticket == None:
                return
            # Delete ticket
            await utils.db.appealticket.delete(where={"id": ticket.id})
            requests.post("https://discord.com/api/webhooks/1091323194671124621/Wlhzf9E4iQKbMkTbsSDtKMbC24k_i8y4P-krPS8qkJJ-svScZerxI_BzyNwwMVTDWxcw", json={"content": f"Message deleted in appeals channel: {content} id {payload.message_id}"})

    @nextcord.slash_command(description="Send report panel")
    @utils.Utils().get_permission_level(2)
    async def report(self, interaction: Interaction):
        # Create embed
        embed = nextcord.Embed(
            title="Report rulebreakers",
            description="To create a ticket react with 📩",
            color=nextcord.Color.green()
        )
        # Set embed footer
        embed.set_footer(text="Made by @Super02#1337")
        # Create CreateReportTicketButton
        view = CreateReportTicketButton(self.bot)
        # Send message
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("Report panel sent!", ephemeral=True)
    
    @nextcord.slash_command(description="Send appeal panel")
    @utils.Utils().get_permission_level(2)
    async def appeal(self, interaction: Interaction):
        # Create embed
        embed = nextcord.Embed(
            title="False ban appeal",
            description="Note: if you use this to appeal exploiter bans that are not false, you will be punished",
            color=nextcord.Color.red()
        )
        # Set embed footer
        embed.set_footer(text="Made by @Super02#1337")
        # Create button
        view = CreateAppealTicketButton(self.bot)
        # Send message
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("Appeal panel sent!", ephemeral=True)
    
    @nextcord.slash_command(description="Get the amount of tickets that you have created, and have gotten accepted")
    async def ticket_count(self, interaction: Interaction, user: nextcord.User = nextcord.SlashOption(name="user", required=False, description="The user to get the ticket count of", default=None)):
        if user == None:
            user = interaction.user
        tickets = await utils.db.ticket.count(where={"reporter": str(user.id)})
        name = "You have" if user.id == interaction.user.id else f"{user.display_name} has"
        embed = nextcord.Embed(
            title="Ticket count",
            description=f"{name} a total of ``{tickets}`` accepted tickets",
            color=nextcord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    
    @nextcord.slash_command(description="Claim a role")
    @cooldowns.cooldown(1, 3, bucket=cooldowns.buckets.SlashBucket.author)
    async def claim_role(self, interaction: Interaction, role: str = nextcord.SlashOption(name="role", required=True, choices={role: role_id for role, role_id in utils.Utils().get_claimable_roles().items()})):
        member = self.bot.get_guild(utils.Utils().guild_id).get_member(interaction.user.id)
        if(nextcord.utils.get(member.roles, id=int(role)) != None):
             return await interaction.response.send_message("You already have this role!", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        tickets = await utils.db.ticket.count(where={"reporter": str(interaction.user.id)})
        role_name = list(utils.Utils().get_claimable_roles().keys())[list(utils.Utils().get_claimable_roles().values()).index(role)]
        if(role_name == "Master Detective"): # Master Detective
            # Check if user has the role
            if(tickets < 10):
                return await interaction.followup.send(embed=utils.Utils().error_embed(f"You need at least 10 accepted tickets to claim this role! You currently have ``{tickets}`` accepted tickets."), ephemeral=True)
            else:
                await member.add_roles(self.bot.get_guild(utils.Utils().guild_id).get_role(int(role)))
                embed = nextcord.Embed(
                    title="Master Detective",
                    description="You have claimed the Master Detective role! This role is given to people who have created at least 10 accepted tickets.",
                    color=nextcord.Color.green()
                )
                return await interaction.followup.send(embed=embed, ephemeral=True)
        elif(role_name == "Exploiter Hunter"): # Exploiter Hunter
            if(tickets < 100):
                return await interaction.followup.send(embed=utils.Utils().error_embed(f"You need at least 100 accepted tickets to claim this role! You currently have ``{tickets}`` accepted tickets."), ephemeral=True)
            else:
                await member.add_roles(self.bot.get_guild(utils.Utils().guild_id).get_role(int(role)))
                embed = nextcord.Embed(
                    title="Exploiter Hunter",
                    description="You have claimed the Exploiter Hunter role! This role is given to people who have created at least 100 accepted tickets.",
                    color=nextcord.Color.green()
                )
                return await interaction.followup.send(embed=embed, ephemeral=True)
        elif(role_name == "Active"): # Active
            level = await self.mee6API.levels.get_user_level(interaction.user.id)
            if(level is None or level < 15):
                return await interaction.followup.send(embed=utils.Utils().error_embed(f"You need to be at least level 15 in the mee6 leaderboard to claim this role! You are currently level {level}."), ephemeral=True)
            else:
                await member.add_roles(self.bot.get_guild(utils.Utils().guild_id).get_role(int(role)))
                embed = nextcord.Embed(
                    title="Active",
                    description="You have claimed the Active role! This role is given to people who are at least level 15 in the mee6 leaderboard.",
                    color=nextcord.Color.green()
                )
                return await interaction.followup.send(embed=embed, ephemeral=True)
        elif(role_name == "Known"): # Known
            level = await self.mee6API.levels.get_user_level(interaction.user.id)
            if(level is None or level < 25):
                return await interaction.followup.send(embed=utils.Utils().error_embed(f"You need to be at least level 25 in the mee6 leaderboard to claim this role! You currently are level ``{level}``."), ephemeral=True)
            else:
                await member.add_roles(self.bot.get_guild(utils.Utils().guild_id).get_role(int(role)))
                embed = nextcord.Embed(
                    title="Known",
                    description="You have claimed the Known role! This role is given to people who are at least level 25 in the mee6 leaderboard.",
                    color=nextcord.Color.green()
                )
                return await interaction.followup.send(embed=embed, ephemeral=True)
        elif(role_name == "Respected"): # Respected
            level = await self.mee6API.levels.get_user_level(interaction.user.id)
            if(level is None or level < 30):
                return await interaction.followup.send(embed=utils.Utils().error_embed(f"You need to be at least level 30 in the mee6 leaderboard to claim this role! You currently are level ``{level}``."), ephemeral=True)
            else:
                await member.add_roles(self.bot.get_guild(utils.Utils().guild_id).get_role(int(role)))
                embed = nextcord.Embed(
                    title="Respected",
                    description="You have claimed the Respected role! This role is given to people who are at least level 30 in the mee6 leaderboard.",
                    color=nextcord.Color.green()
                )
                return await interaction.followup.send(embed=embed, ephemeral=True)
        elif(role_name == "Legend"): # Legend
            level = await self.mee6API.levels.get_user_level(interaction.user.id)
            if(level is None or level < 40):
                return await interaction.followup.send(embed=utils.Utils().error_embed(f"You need to be at least level 40 in the mee6 leaderboard to claim this role! You currently are level ``{level}``."), ephemeral=True)
            else:
                await member.add_roles(self.bot.get_guild(utils.Utils().guild_id).get_role(int(role)))
                embed = nextcord.Embed(
                    title="Legend",
                    description="You have claimed the Legend role! This role is given to people who are at least level 40 in the mee6 leaderboard.",
                    color=nextcord.Color.green()
                )
                return await interaction.followup.send(embed=embed, ephemeral=True)
        elif(role_name == "Level 69"): # Level 69
            level = await self.mee6API.levels.get_user_level(interaction.user.id)
            if(level is None or level < 69):
                return await interaction.followup.send(f"You need to be at least level 69 in the mee6 leaderboard to claim this role! You currently are level ``{level}``.", ephemeral=True)
            else:
                await member.add_roles(self.bot.get_guild(utils.Utils().guild_id).get_role(int(role)))
                embed = nextcord.Embed(
                    title="Level 69",
                    description="You have claimed the Level 69 role! This role is given to people who are at least level 69 in the mee6 leaderboard.",
                    color=nextcord.Color.green()
                )
                return await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            return await interaction.followup.send(embed=utils.Utils().error_embed("Unknown role... Please report this to Super02#1337 or by sending Holger Danske a message."), ephemeral=True)

    @nextcord.slash_command(description="Get a list of your active reports/appeals and their status")
    @cooldowns.cooldown(1, 3, bucket=cooldowns.buckets.SlashBucket.author)
    async def my_tickets(self, interaction: Interaction, page: int = nextcord.SlashOption(name="page", required=False, description="The page to get", default=1)):
        report_count = await utils.db.reportticket.count(where={"reporter": str(interaction.user.id)})
        appeal_count = await utils.db.appealticket.count(where={"discord_id": str(interaction.user.id)})
        if(page < 1 or page > math.ceil((report_count+appeal_count)/10)+1):
            return await interaction.response.send_message(embed=utils.Utils().error_embed("Invalid page..."), ephemeral=True)
        reports = await utils.db.reportticket.find_many(where={"reporter": str(interaction.user.id)}, take=10, skip=(page-1)*10)
        appeals = await utils.db.appealticket.find_many(where={"discord_id": str(interaction.user.id)}, take=1, skip=(page-1)*10)
        embed = nextcord.Embed(
            title="Your tickets",
            description="A list of your active reports and appeals",
            color=nextcord.Color.green()
        )
        if(len(reports) == 0):
            embed.add_field(name="Reports", value="You have no active reports")
        else:
            # List reports and their id
            embed.add_field(name="Reports", value="\n".join([f"report-{report.id} - {report.reported}" for report in reports]), inline=False)
        if(len(appeals) == 0):
            embed.add_field(name="Appeals", value="You have no active appeals")
        else:
            # There can only be one active appeal
            claimed = "Yes" if appeals[0].claimed_by is not None else "No"
            embed.add_field(name="Appeals", value=f"appeal-{appeals[0].id} | Seen by staff: {claimed}", inline=False)
        embed.set_footer(text=f"Page {page}/{math.ceil((report_count+appeal_count)/10)+1}")
        await interaction.response.send_message(embed=embed)
    
    # Cancel ticket
    @nextcord.slash_command(description="Cancel a ticket")
    @cooldowns.cooldown(1, 3, bucket=cooldowns.buckets.SlashBucket.author)
    async def cancel_ticket(self, interaction: Interaction, ticket_id: str):
        # Check if it is a report or appeal
        if(ticket_id.startswith("report-")):
            # Report
            ticket_id = ticket_id.replace("report-", "")
            ticket = await utils.db.reportticket.find_first(where={"id": int(ticket_id), "reporter": str(interaction.user.id)})
            if(ticket is None):
                return await interaction.response.send_message(embed=utils.Utils().error_embed("Unknown ticket..."), ephemeral=True)
            else:
                # Get message id
                messageId = ticket.messageId
                # Get message
                message = await self.bot.get_channel(1072630661933965342).fetch_message(messageId)
                # Delete message
                await message.delete()
                # Delete ticket
                await utils.db.reportticket.delete(where={"id": int(ticket_id)})
                # Send message
                await interaction.response.send_message("Ticket deleted!")
        elif(ticket_id.startswith("appeal-")):
            # Appeal
            ticket_id = ticket_id.replace("appeal-", "")
            ticket = await utils.db.appealticket.find_first(where={"id": int(ticket_id), "discord_id": str(interaction.user.id)})
            if(ticket is None):
                return await interaction.response.send_message(embed=utils.Utils().error_embed("Unknown ticket..."), ephemeral=True)
            else:
                # Get message id
                messageId = ticket.messageId
                # Get message
                message = await self.bot.get_channel(1077293993756463226).fetch_message(messageId)
                # Delete message
                await message.delete()
                # Delete ticket
                await utils.db.appealticket.delete(where={"id": int(ticket_id)})
                # Send message
                await interaction.response.send_message("Ticket deleted!")
        

    @nextcord.slash_command(description="Set quota")
    @utils.Utils().get_permission_level(3)
    async def set_quota(self, interaction: Interaction, quota: int):
        await utils.db.botstorage.update(where={"id": 1}, data={"ticket_quota": quota})
        await interaction.response.send_message(f"Quota set to ``{quota}``")
    
    @nextcord.slash_command(description="Get quota")
    @utils.Utils().get_permission_level(8)
    async def get_quota(self, interaction: Interaction, user: nextcord.User = nextcord.SlashOption(name="user", required=False, description="The user to get the quota of", default=None), month: int = nextcord.SlashOption(name="month", required=False, description="The month to get the quota of", default=None), quota = nextcord.SlashOption(name="quota", required=False, description="The quota to set", default=None)):
        quota = (await utils.db.botstorage.find_first(where={"id": 1})).ticket_quota if quota == None else quota
        user = interaction.user if user == None else user
        start = datetime.now().replace(day=1, hour=0, minute=0, month=month if month != None else datetime.now().month)
        end = datetime.now().replace(day=calendar.monthrange(datetime.now().year, datetime.now().month)[1], hour=23, minute=59, month=month if month != None else datetime.now().month)
        personal_quota = await utils.Utils().get_personal_quota(start, end, user.id)
        embed = nextcord.Embed(
            title="Quota",
            description=f"Quota for this month is ``{quota}``\nPersonal quota is ``{round(personal_quota)}``",
            color=nextcord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    
    @nextcord.slash_command(description="Fix tickets")
    @utils.Utils().get_permission_level(0)
    async def fix_tickets(self, interaction: Interaction, delete: bool = True):
        await interaction.response.defer()
        # Get all tickets
        tickets = await utils.db.reportticket.find_many()
        category = nextcord.utils.get(self.bot.get_guild(utils.Utils().guild_id).categories, id=utils.Utils().report_category)
        i = 0
        bugged_tickets = []
        for ticket in tickets:
            # Get message
            if f"report-{ticket.id}" in map(lambda x: x.name, category.channels):
                continue
            try:
                await self.bot.get_channel(1072630661933965342).fetch_message(ticket.messageId)
            except:
                # Delete ticket
                i = i + 1
                if(delete):
                    await utils.db.reportticket.delete(where={"id": ticket.id})
                else:
                    bugged_tickets.append(ticket)
                continue
        if not delete:
            return await interaction.followup.send(f"Done! {i}\n{str(bugged_tickets)[:1900]}", ephemeral=True)
        await interaction.followup.send(f"Done! {i}", ephemeral=True)

    # Get the average ticket time today
    @nextcord.slash_command(description="Get the average ticket time last 24 hours")
    async def ticket_average(self, interaction: Interaction):
        # Get all tickets that has the completedIn field and is today. Make sure to use graphql queries
        tickets = await utils.db.ticket.find_many(
            where={
                "completedIn": {
                    "not": None
                },
                "date": {
                    "gte": datetime.now() - timedelta(days=1)
                }
            }
        )
        # Check if there are no tickets
        if(len(tickets) == 0):
            await interaction.response.send_message("No tickets have been done the last 24 hours!", ephemeral=True)
            return
        # Get the average time
        average = sum([ticket.completedIn for ticket in tickets]) / len(tickets)
        # Format average using datetime
        average = str(datetime.fromtimestamp(average).strftime("%H:%M:%S"))
        # Send message
        await interaction.response.send_message(f"The average ticket time the last 24 hours is ``{average}``", ephemeral=True)

    # Ticket blacklist command
    @nextcord.slash_command(description="Blacklist a user from creating tickets")
    @utils.Utils().get_permission_level(8)
    async def ticket_blacklist(self, interaction: Interaction, user: nextcord.User):
        # Check if user is already ticket blacklisted
        db_user = await utils.db.user.find_first(where={"discord_id": str(user.id)})
        if(db_user != None):
            if(db_user.ticket_blacklist):
                await interaction.response.send_message("User is already ticket blacklisted! <:amogus:1096138125232840756>", ephemeral=True)
                return
        # Add ticket blacklist to db
        await utils.db.user.update(where={"discord_id": str(user.id)}, data={"ticket_blacklist": True})
        # Add ticket blacklist role
        await user.add_roles(self.bot.get_guild(utils.Utils().guild_id).get_role(864248045226819634))
        await interaction.response.send_message(f"Added {user.mention} to ticket blacklist!", ephemeral=True)
    
    # Ticket unblacklist command
    @nextcord.slash_command(description="Unblacklist a user from creating tickets")
    @utils.Utils().get_permission_level(8)
    async def ticket_unblacklist(self, interaction: Interaction, user: nextcord.User):
        # Check if user is already ticket blacklisted
        db_user = await utils.db.user.find_first(where={"discord_id": str(user.id)})
        if(db_user != None):
            if(not db_user.ticket_blacklist):
                await interaction.response.send_message("User is not ticket blacklisted! <:amogus:1096138125232840756>", ephemeral=True)
                return
        # Remove ticket blacklist role
        await user.remove_roles(self.bot.get_guild(utils.Utils().guild_id).get_role(864248045226819634))
        # Remove ticket blacklist from db
        await utils.db.user.update(where={"discord_id": str(user.id)}, data={"ticket_blacklist": False})
        await interaction.response.send_message(f"Removed {user.mention} from ticket blacklist!", ephemeral=True)
    
    # If ticket blacklist role is removed, remove from db. If ticket blacklist role is added, add to db
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if(before.guild.id == utils.Utils().guild_id):
            if(before.roles != after.roles):
                blacklist_role = after.guild.get_role(864248045226819634)
                db_user = await utils.db.user.find_first(where={"discord_id": str(after.id)})
                if(blacklist_role not in before.roles and not blacklist_role in after.roles):
                    return
                if(db_user == None):
                    # Add user to db
                    await utils.db.user.create({"discord_id": str(after.id)})
                if(not blacklist_role in after.roles):
                    # Remove ticket blacklist from db
                    await utils.db.user.update(where={"discord_id": str(after.id)}, data={"ticket_blacklist": False})
                elif(blacklist_role in after.roles):
                    # Add ticket blacklist to db
                    await utils.db.user.update(where={"discord_id": str(after.id)}, data={"ticket_blacklist": True})

#--------------------------------------------------------------------------------------------------------------------------------#


async def get_avatar(name: str = None, userid: int = None):
    if not name and not userid:
        return None
    try:
        if name:
            payload = {"usernames": [name]}
            async with aiohttp.ClientSession() as session:
                async with session.post("https://users.roblox.com/v1/usernames/users", json=payload) as response:
                    userid = await response.json()
                    if not userid["data"]:
                        return None
                    userid = userid["data"][0]["id"]
    except Exception as e:
        print(traceback.format_exc())
        return None
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?&size=352x352&format=Png&isCircular=false&userIds={userid}") as response:
            avatar_url = (await response.json())["data"][0]["imageUrl"]
    return avatar_url

class CreateReportTicketButton(nextcord.ui.View):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(
            timeout=None,
        )
    
    @nextcord.ui.button(label="📩Submit report", style=nextcord.ButtonStyle.gray, custom_id="tickets:button:report:submit")
    async def submit(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(Report(self.bot))
    
    """ @nextcord.ui.button(label="📩Create ticket", style=nextcord.ButtonStyle.gray, custom_id="tickets:button:report:create")
    async def create(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_message("This feature is currently disabled! Please use submit report instead.", ephemeral=True) """

class CreateAppealTicketButton(nextcord.ui.View):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(
            timeout=None,
        )
    
    @nextcord.ui.button(label="📩Submit appeal", style=nextcord.ButtonStyle.gray, custom_id="tickets:button:appeal:submit")
    async def submit(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(Appeal(self.bot))
    
    """ @nextcord.ui.button(label="📩Create ticket", style=nextcord.ButtonStyle.gray, custom_id="tickets:button:appeal:create")
    async def create(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_message("This feature is currently disabled! Please use submit appeal instead.", ephemeral=True) """

#--------------------------------------------------------------------------------------------------------------------------------#

# Prompt staff asking what punishment to give
class StaffPunishmentPrompt(nextcord.ui.Modal):
    def __init__(self, bot, reporter, reported, evidence, reason, additional_info=None):
        self.bot = bot
        self.reporter = reporter
        self.reported = reported
        self.evidence = evidence
        self.reason = reason
        self.additional_info = additional_info
        super().__init__(
            "Punishment prompt",
            timeout=None,
            custom_id="tickets:StaffPunishmentPrompt",
            auto_defer=True,
        )
        
        self.punishment = nextcord.ui.TextInput(
            label="Punishment",
            placeholder="Punishment",
            custom_id="tickets:StaffPunishmentPrompt:punishment"
        )
        self.add_item(self.punishment)
    
    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        user = await self.bot.fetch_user(int(self.reporter))
        ticket = await utils.db.reportticket.find_first(where={"messageId": str(interaction.message.id)})
        ticket_msg = await self.bot.get_channel(utils.Utils().ticket_records_channel).send("ticket record loading...")
        time = datetime.utcnow().timestamp() - ticket.date.timestamp()
        await ticket_msg.edit(content=f"Name: {self.reported}\nPunishment: {self.punishment.value}\nReason: {self.reason}\nEvidence: {self.evidence}\nReporter: <@{self.reporter}>\nModerator: {interaction.user.mention}" + (f"\nAdditional info: {self.additional_info}" if self.additional_info != None else ""))
        await utils.Utils().add_ticket(interaction, self.reporter, self.reported, self.evidence, self.reason, self.punishment.value, ticket_msg.id, additional_info=self.additional_info, completedIn=time)
        await utils.db.reportticket.delete(where={"messageId": str(interaction.message.id)})
        await interaction.message.delete()
        try:
            await user.send(f"Thank you for reporting ``{self.reported}``. Your report with ID ``report-{ticket.id}`` was accepted and the user has been punished. Thank you for the report!")
        except:
            pass

class AppealStaffNotesModal(nextcord.ui.Modal):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(
            "Add note to appeal",
            timeout=None,
            custom_id="tickets:appeal:notesmodal:init",
        )

        self.notes = nextcord.ui.TextInput(
            label="Notes",
            min_length=2,
            required=False,
            max_length=500,
            custom_id="tickets:appeal:notesmodal:field:username",
        )
        self.add_item(self.notes)
    
    async def callback(self, interaction: nextcord.Interaction) -> None:
        ticket = await utils.db.appealticket.find_first(where={"messageId": str(interaction.message.id)})
        user = await self.bot.fetch_user(ticket.discord_id)
        channel = await self.bot.get_guild(utils.Utils().guild_id).fetch_channel(utils.Utils().ticket_records_channel)
        msg = await channel.send("ticket record loading...")
        response = f"Appeal:\nUsername: {ticket.username}\nDiscord user: {user.mention}\nReason: {ticket.reason}\nDecision: Accepted\nModerator: {interaction.user.mention}"
        if ticket.notes != None:
            response += f"\nNotes: {ticket.notes}"
        await msg.edit(response)
        await utils.db.appealticket.delete(where={"messageId": str(interaction.message.id)})
        await interaction.response.send_message("Appeal accepted!", ephemeral=True)
        await utils.Utils().server_log(f"{interaction.user.id} accepted {user.mention}'s appeal", self.bot)
        await interaction.message.delete()
        try:
            await user.send("Your appeal has been accepted!")
        except:
            pass

class StaffDenyTicketPrompt(nextcord.ui.Modal):
    def __init__(self, bot, interaction):
        self.bot = bot
        self.interaction = interaction
        super().__init__(
            "Deny ticket",
            timeout=None,
            custom_id="tickets:StaffDenyTicketPrompt",
            auto_defer=True,
        )
        
        self.reason = nextcord.ui.TextInput(
            label="Reason",
            placeholder="Reason",
            custom_id="tickets:StaffDenyTicketPrompt:reason"
        )
        self.add_item(self.reason)
    
    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        ticket = await utils.db.reportticket.find_first(where={"messageId": str(interaction.message.id)})
        user = await self.bot.fetch_user(int(ticket.reporter))
        await utils.db.reportticket.delete(where={"messageId": str(interaction.message.id)})
        await interaction.message.delete()
        try:
            await user.send(f"Thank you for reporting ``{ticket.reported}``. Unfortunately, your report was denied. The reason for this is: ``{self.reason.value}``")
        except:
            pass

class StaffReportTicketButtons(nextcord.ui.View):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(
            timeout=None,
            auto_defer=True,
        )
    
    @nextcord.ui.button(label="Accept", style=nextcord.ButtonStyle.green, custom_id="tickets:StaffTicketButtons:accept")
    async def accept(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        ticket = await utils.db.reportticket.find_first(where={"messageId": str(interaction.message.id)})
        response = await utils.Utils().ticket_interaction_check(ticket, interaction)
        if response != True:
            return await interaction.response.send_message(response, ephemeral=True)
        await interaction.response.send_modal(StaffPunishmentPrompt(self.bot, ticket.reporter, ticket.reported, ticket.evidence, ticket.reason, additional_info=ticket.additionalInfo))
    
    @nextcord.ui.button(label="Deny", style=nextcord.ButtonStyle.red, custom_id="tickets:StaffTicketButtons:deny")
    async def close(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Delete ticket information from database and delete message
        ticket = await utils.db.reportticket.find_first(where={"messageId": str(interaction.message.id)})
        response = await utils.Utils().ticket_interaction_check(ticket, interaction)
        if response != True:
            return await interaction.response.send_message(response, ephemeral=True)
        # Ask for reason why ticket was denied using a modal
        await interaction.response.send_modal(StaffDenyTicketPrompt(self.bot, interaction))

    @nextcord.ui.button(label="Investigate", style=nextcord.ButtonStyle.gray, custom_id="tickets:StaffTicketButtons:investigate")
    async def investigate(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Get ticket information
        ticket = await utils.db.reportticket.find_first(where={"messageId": str(interaction.message.id)})
        response = await utils.Utils().ticket_interaction_check(ticket, interaction)
        if response != True:
            return await interaction.response.send_message(response, ephemeral=True)
        # Check if ticket is an report
        guild = self.bot.get_guild(utils.Utils().guild_id)
        category = nextcord.utils.get(guild.categories, id=utils.Utils().report_category)
        channel = await guild.create_text_channel("report-" + str(ticket.id), category=category, overwrites={
            guild.default_role: nextcord.PermissionOverwrite(read_messages=False),
            guild.get_member(int(ticket.reporter)): nextcord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True),
            guild.get_member(int(interaction.user.id)): nextcord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(utils.Utils().staff_role): nextcord.PermissionOverwrite(read_messages=True, send_messages=False),
        })
        embed = nextcord.Embed(
            title=f"Report #{ticket.id}",
            description=f"**Reporter:** {guild.get_member(int(ticket.reporter))}\n**Reported:** {ticket.reported}\n**Reason:** {ticket.reason}\n**Evidence:** {ticket.evidence}",
            color=nextcord.Color.green()
        )
        embed.add_field(name="Status", value=f"Your report is being investigated by staff. Please wait patiently, and answer any potential questions you may get from staff.")
        embed.add_field(name="Claimed by", value=f"{interaction.user.mention}", inline=False)
        embed.add_field(name="Closing the ticket", value="Only staff are able to close your ticket by reacting with 🔒.", inline=False)
        embed.set_footer(text="By Super02#1337")
        avatar = await get_avatar(name=ticket.reported)
        if avatar:
            embed.set_thumbnail(url=avatar)
        view = InvestigateReportTicketButtons()
        msg = await channel.send(content=f"{guild.get_member(int(ticket.reporter)).mention} Welcome", embed=embed, view=view)
        await utils.db.reportticket.update(where={"id": ticket.id}, data={"messageId": str(msg.id)})
        await interaction.message.delete()
        await interaction.response.send_message(f"Ticket channel created! {channel.mention}", ephemeral=True)
    
    @nextcord.ui.button(label="Edit", style=nextcord.ButtonStyle.gray, custom_id="tickets:StaffTicketButtons:edit")
    async def edit(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Get ticket information
        ticket = await utils.db.reportticket.find_first(where={"messageId": str(interaction.message.id)})
        response = await utils.Utils().ticket_interaction_check(ticket, interaction)
        if response != True:
            return await interaction.response.send_message(response, ephemeral=True)
        # Check if ticket is an report
        await interaction.response.send_modal(StaffEditPrompt(self.bot, ticket.reporter, ticket.reported, ticket.evidence, ticket.reason, interaction.message.id, additional_info=ticket.additionalInfo))

    @nextcord.ui.button(label="Claim", style=nextcord.ButtonStyle.blurple, custom_id="tickets:StaffTicketButtons:claim")
    async def claim(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        ticket = await utils.db.reportticket.find_first(where={"messageId": str(interaction.message.id)})
        response = await utils.Utils().ticket_interaction_check(ticket, interaction)
        if response != True:
            if response == "You can't interact with this ticket as it is claimed by someone else." and self.children[4].label == "Claim":
                msg.content += f"**\nClaimed by** <@{ticket.claimed_by}>"
                # Change button label
                self.children[4].label = "Unclaim"
                self.children[4].style = nextcord.ButtonStyle.red
                await interaction.message.edit(content=msg.content, view=self)
                return await interaction.response.send_message(f"Bug encountered while claiming ticket. Unfortunately you can't claim the ticket as <@{ticket.claimed_by}> claimed it before, but for some reason the ticket message was not updated. Sorry for the inconvenience.", ephemeral=True)
            return await interaction.response.send_message(response, ephemeral=True)
        msg = await interaction.channel.fetch_message(ticket.messageId)
        if ticket.claimed_by != None:
            await utils.db.reportticket.update(where={"id": ticket.id}, data={"claimed_by": None})
            # Change button label
            self.children[4].label = "Claim"
            self.children[4].style = nextcord.ButtonStyle.blurple
            # Remove claimed by from message by recreating it
            reporter = await self.bot.fetch_user(ticket.reporter)
            msg.content = f"**Ticket opened by:** {reporter.mention}\n**Rulebreaker username:** {ticket.reported}\n**Evidence:** {ticket.evidence}\n**Reason:** {ticket.reason}\n**ID:** report-{ticket.id}"
            if ticket.additionalInfo:
                msg.content += f"\n**Additional information:** {ticket.additionalInfo}"
        else:
            await utils.db.reportticket.update(where={"id": ticket.id}, data={"claimed_by": str(interaction.user.id)})
            msg.content += f"**\nClaimed by** {interaction.user.mention} <t:{int(datetime.now().timestamp())}:R>"
            # Change button label
            self.children[4].label = "Unclaim"
            self.children[4].style = nextcord.ButtonStyle.red
        await interaction.response.edit_message(view=self, content=msg.content)

class StaffTicketBlacklistButtons(nextcord.ui.View):
    def __init__(self, bot, userid, message):
        self.bot = bot
        self.userid = userid
        self.message = message
        super().__init__(
            timeout=None,
        )
    
    @nextcord.ui.button(label="Blacklist", style=nextcord.ButtonStyle.red, custom_id="tickets:StaffTicketBlacklistButtons:blacklist")
    async def blacklist(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        db_user = await utils.db.user.find_first(where={"discord_id": str(self.userid)})
        if db_user == None:
            await utils.db.user.create({"discord_id": str(self.userid), "ticket_blacklist": True})
        else:
            await utils.db.user.update(where={"discord_id": str(self.userid)}, data={"ticket_blacklist": True})
        # Give ticket blacklist role
        try:
            member = self.bot.get_guild(utils.Utils().guild_id).get_member(self.userid)
            await member.add_roles(self.bot.get_guild(utils.Utils().guild_id).get_role(864248045226819634))
        except:
            await self.message.delete()
            return await interaction.response.edit_message(content=f"{self.bot.get_guild(utils.Utils().guild_id).get_member(self.userid).mention} has been blacklisted from creating tickets, but I couldn't give them the ticket blacklist role (Probably not in the discord).", view=None)
        await self.message.delete()
        await interaction.response.edit_message(content=f"{member.mention} has been blacklisted from creating tickets.", view=None)

    @nextcord.ui.button(label="No blacklist", style=nextcord.ButtonStyle.green, custom_id="tickets:StaffTicketBlacklistButtons:noblacklist")
    async def unblacklist(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.message.delete()
        await interaction.response.edit_message(content=f"{self.bot.get_guild(utils.Utils().guild_id).get_member(self.userid).mention} has not been blacklisted from creating tickets.", view=None)


class StaffAppealTicketButtons(nextcord.ui.View):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(
            timeout=None,
        )
    
    @nextcord.ui.button(label="Accept", style=nextcord.ButtonStyle.green, custom_id="tickets:StaffAppealTicketButtons:accept")
    async def create(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        ticket = await utils.db.appealticket.find_first(where={"messageId": str(interaction.message.id)})
        if (ticket.claimed_by != None and ticket.claimed_by != str(interaction.user.id)) and not utils.Utils().get_permission_level(2).predicate(interaction):
            return await interaction.response.send_message("You can't accept this ticket, as you didn't claim it!", ephemeral=True)
        await interaction.response.send_modal(AppealStaffNotesModal(self.bot))

    @nextcord.ui.button(label="Deny", style=nextcord.ButtonStyle.red, custom_id="tickets:StaffAppealTicketButtons:deny")
    async def close(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer()
        ticket = await utils.db.appealticket.find_first(where={"messageId": str(interaction.message.id)})
        if ticket == None:
            return await interaction.followup.send("This ticket doesn't exist! (Please log manually and delete the message after)", ephemeral=True)
        if (ticket.claimed_by != None and ticket.claimed_by != str(interaction.user.id)) and not utils.Utils().get_permission_level(2).predicate(interaction):
            return await interaction.followup.send("You can't deny this ticket, as you didn't claim it!", ephemeral=True)
        user = await self.bot.fetch_user(ticket.discord_id)
        channel = await self.bot.get_guild(utils.Utils().guild_id).fetch_channel(utils.Utils().ticket_records_channel)
        msg = await channel.send("ticket record loading...")
        response = f"Appeal:\nUsername: {ticket.username}\nDiscord user: {user.mention}\nReason: {ticket.reason}\nDecision: denied\nModerator: {interaction.user.mention}"
        if ticket.notes != None:
            response += f"\nNotes: {ticket.notes}"
        await msg.edit(response)
        await utils.db.appealticket.delete(where={"messageId": str(interaction.message.id)})
        await utils.Utils().server_log(f"{interaction.user.id} denied {user.mention}'s appeal", self.bot)
        try:
            await user.send("Your appeal has been denied!")
        except:
            pass
        # Ask the staff member if they want to ticket blacklist the user by sending a new ephermal message with a view
        await interaction.followup.send("Do you want to ticket blacklist this user?", view=StaffTicketBlacklistButtons(self.bot, user.id, interaction.message), ephemeral=True)
    
    @nextcord.ui.button(label="Investigate", style=nextcord.ButtonStyle.gray, custom_id="tickets:StaffAppealTicketButtons:investigate")
    async def investigate(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Get ticket information
        ticket = await utils.db.appealticket.find_first(where={"messageId": str(interaction.message.id)})
        if(ticket == None):
            return await interaction.response.send_message("This ticket doesn't exist! (Please log manually and delete the message after)", ephemeral=True)
        if (ticket.claimed_by != None and ticket.claimed_by != str(interaction.user.id)) and not utils.Utils().get_permission_level(2).predicate(interaction):
            return await interaction.response.send_message("You can't investigate this ticket, as you didn't claim it!", ephemeral=True)
        # Check if ticket is an report
        guild = self.bot.get_guild(utils.Utils().guild_id)
        category = nextcord.utils.get(guild.categories, id=utils.Utils().appeal_category)
        channel = await guild.create_text_channel("appeal-" + str(ticket.id), category=category, overwrites={
            guild.default_role: nextcord.PermissionOverwrite(read_messages=False),
            guild.get_member(int(ticket.discord_id)): nextcord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True),
            guild.get_member(int(interaction.user.id)): nextcord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(utils.Utils().staff_role): nextcord.PermissionOverwrite(read_messages=True, send_messages=False),
        })
        embed = nextcord.Embed(
            title=f"Appeal #{ticket.id}",
            description=f"**Appealer:** {ticket.username}\n**Reason for punishment:** {ticket.reason}\n**Appeal:** {ticket.appeal}",
            color=nextcord.Color.green()
        )
        embed.add_field(name="Status", value=f"Your appeal is being investigated by staff. Please wait patiently, and answer any potential questions you may get from staff. This ticket was created <t:{int(datetime.now().timestamp())}:R>")
        embed.add_field(name="Claimed by", value=f"{interaction.user.mention}", inline=False)
        embed.add_field(name="Closing the ticket", value="Only staff are able to close your ticket by reacting with 🔒.", inline=False)
        avatar_url = await get_avatar(name=ticket.username)
        if avatar_url != None:
            embed.set_thumbnail(url=avatar_url)
        embed.set_footer(text="By Super02#1337")
        view = InvestigateAppealTicketButtons()
        msg = await channel.send(content=f"{guild.get_member(int(ticket.discord_id)).mention} Welcome", embed=embed, view=view)
        await utils.db.appealticket.update(where={"id": ticket.id}, data={"messageId": str(msg.id)})
        await interaction.message.delete()
        await interaction.response.send_message(f"Ticket channel created! {channel.mention}", ephemeral=True)
    
    @nextcord.ui.button(label="Claim", style=nextcord.ButtonStyle.blurple, custom_id="tickets:StaffAppealTicketButtons:claim")
    async def claim(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        ticket = await utils.db.appealticket.find_first(where={"messageId": str(interaction.message.id)})
        if not utils.Utils().get_permission_level(2).predicate(interaction) and ticket.claimed_by != None and ticket.claimed_by != str(interaction.user.id):
            return await interaction.response.send_message("You can't unclaim this ticket, as it's already claimed! <:amogus:1096138125232840756>", ephemeral=True)
        msg = await interaction.channel.fetch_message(ticket.messageId)
        embed = msg.embeds[0]
        if ticket.claimed_by != None:
            await utils.db.appealticket.update(where={"id": ticket.id}, data={"claimed_by": None})
            # Change button label
            self.children[3].label = "Claim"
            self.children[3].style = nextcord.ButtonStyle.blurple
            embed.color = nextcord.Color.green()
            # Remove claimed by from message by recreating it
            embed.remove_field(3)
        else:
            await utils.db.appealticket.update(where={"id": ticket.id}, data={"claimed_by": str(interaction.user.id)})
            embed.add_field(name="Claimed by", value=f"{interaction.user.mention} <t:{int(datetime.now().timestamp())}:R>", inline=False)
            embed.color = nextcord.Color.blue()
            # Change button label
            self.children[3].label = "Unclaim"
            self.children[3].style = nextcord.ButtonStyle.red
        await interaction.response.edit_message(view=self, embed=embed)

class StaffEditPrompt(nextcord.ui.Modal):
    def __init__(self, bot, reporter, reported, evidence, reason, message_id, additional_info=None):
        self.bot = bot
        super().__init__(
            "Rulebreaker report",
            timeout=None,
            custom_id="tickets:staffeditprompt:init",
        )

        self.username = nextcord.ui.TextInput(
            label="Rulebreaker username",
            placeholder=reported[:100],
            min_length=2,
            required=False,
            max_length=50,
            custom_id="tickets:staffeditprompt:field:username",
        )
        self.add_item(self.username)

        self.evidence = nextcord.ui.TextInput(
            label="Evidence",
            placeholder=evidence[:100],
            required=False,
            max_length=180,
            custom_id="tickets:staffeditprompt:field:evidence",
        )
        self.add_item(self.evidence)

        self.reason = nextcord.ui.TextInput(
            label="Reason",
            placeholder=reason[:100],
            min_length=2,
            required=False,
            max_length=50,
            custom_id="tickets:staffeditprompt:field:reason",
        )
        self.add_item(self.reason)

        self.info = nextcord.ui.TextInput(
            label="Additional info",
            style=nextcord.TextInputStyle.paragraph,
            placeholder=additional_info[:100] if additional_info else None,
            required=False,
            max_length=500,
            custom_id="tickets:staffeditprompt:field:info",
        )
        self.add_item(self.info)
    
    async def callback(self, interaction: Interaction) -> None:
        # Get ticket information
        ticket = await utils.db.reportticket.find_first(where={"messageId": str(interaction.message.id)})
        # Set default values
        fields = {
            "reported": self.username.value,
            "evidence": self.evidence.value,
            "reason": self.reason.value,
            "additionalInfo": self.info.value
        }
        edited = {}
        for field, value in fields.items():
            if value != "":
                edited[field] = None if value == "none" and field == "additionalInfo" else value
                setattr(ticket, field, edited[field])
        reporter = await self.bot.fetch_user(ticket.reporter)
        response = f"**Ticket opened by:** {reporter.mention}."
        # Create embed
        embed = nextcord.Embed(
            title="Rulebreaker report",
            description=response,
            color=nextcord.Color.green()
        )
        # Set embed footer
        embed.set_footer(text="Made by @Super02#1337")

        # Set embed fields
        embed.add_field(name="Rulebreaker username", value=ticket.reported, inline=False)
        embed.add_field(name="Evidence", value=ticket.evidence, inline=False)
        embed.add_field(name="Reason", value=ticket.reason, inline=False)
        # Set thumbnail
        avatar = await get_avatar(name=ticket.reported)
        embed.set_thumbnail(avatar)
        # Staff ticket buttons
        view = StaffReportTicketButtons(self.bot)
        # Edit ticket message
        #await interaction.message.edit(embed=embed, view=view)
        response += f"\n**Rulebreaker username:** {ticket.reported}\n**Evidence:** {ticket.evidence}\n**Reason:** {ticket.reason}\n**ID:** report-{ticket.id}"
        if ticket.additionalInfo:
            response += f"\n**Additional info:** {ticket.additionalInfo}"
            embed.add_field(name="Additional info", value=ticket.additionalInfo, inline=False)
        # If the ticket is claimed, add the claimed by field
        if ticket.claimed_by:
            claimed_by = await self.bot.fetch_user(ticket.claimed_by)
            response += f"\n**Claimed by:** {claimed_by.mention} <t:{int(datetime.now().timestamp())}:R>"
            embed.add_field(name="Claimed by", value=claimed_by.mention, inline=False)
            embed.color = nextcord.Color.blue()
            # Change button label
            view.children[4].label = "Unclaim"
            view.children[4].style = nextcord.ButtonStyle.red
        await interaction.message.edit(content=response, view=view)
        # Create ticket in database
        await utils.db.reportticket.update(where={"messageId": str(interaction.message.id)}, data={"reported": ticket.reported, "evidence": ticket.evidence, "reason": ticket.reason, "additionalInfo": ticket.additionalInfo})
        reporter = await self.bot.fetch_user(ticket.reporter)
        changes = ""
        for key, value in edited.items():
            if value == None:
                changes += f"\n**{key}:** *Removed the field*"
            else:
                changes += f"\n**{key}:** {value}"
        await reporter.send(f"Your report ticket with the ID: report-{ticket.id} reporting {ticket.reported} has been edited with the following changes:{changes}")

class InvestigateReportTicketButtons(nextcord.ui.View):
    def __init__(self):
        super().__init__(
            timeout=None,
        )

    @nextcord.ui.button(label="🔒Close ticket", style=nextcord.ButtonStyle.red, custom_id="tickets:button:report:investigate:close")
    async def close(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if not utils.Utils().get_permission_level(8).predicate(interaction):
            await interaction.response.send_message("You don't have permission to do this!", ephemeral=True)
            return
        requests.post("https://discord.com/api/webhooks/1091383511304388618/SH6aiMCaxNWWcWWbXOIYLqDs_iHqWjtOyrMlb6_b1DEmkYDEdbQOmvabFtBYiaLIiaJi", json={"content": f"Report ticket closed by {interaction.user.mention} message ID: {interaction.message.id} channel name {interaction.channel.name}"})
        # Delete ticket information from database and delete message
        await utils.db.reportticket.delete(where={"messageId": str(interaction.message.id)})
        # Delete ticket channel
        await interaction.channel.delete()

class InvestigateAppealTicketButtons(nextcord.ui.View):
    def __init__(self):
        super().__init__(
            timeout=None,
        )

    @nextcord.ui.button(label="🔒Close ticket", style=nextcord.ButtonStyle.red, custom_id="tickets:button:appeal:investigate:close")
    async def close(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if not utils.Utils().get_permission_level(8).predicate(interaction):
            await interaction.response.send_message("You don't have permission to do this!", ephemeral=True)
            return
        # Delete ticket information from database and delete message
        await utils.db.appealticket.delete(where={"messageId": str(interaction.message.id)})
        # Delete ticket channel
        await interaction.channel.delete()


class Report(nextcord.ui.Modal):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(
            "Rulebreaker report",
            timeout=None,
            custom_id="tickets:report:init",
        )

        self.username = nextcord.ui.TextInput(
            label="Rulebreaker username",
            min_length=2,
            required=True,
            max_length=50,
            custom_id="tickets:report:field:username",
        )
        self.add_item(self.username)

        self.evidence = nextcord.ui.TextInput(
            label="Evidence",
            placeholder="https://youtube.com/watch?v=dQw4w9WgXcQ",
            required=True,
            max_length=90,
            custom_id="tickets:report:field:evidence",
        )
        self.add_item(self.evidence)

        self.reason = nextcord.ui.TextInput(
            label="Reason",
            placeholder="Don't put \"exploiting\" put the type of exploit",
            min_length=2,
            required=True,
            max_length=50,
            custom_id="tickets:report:field:reason",
        )
        self.add_item(self.reason)

        self.info = nextcord.ui.TextInput(
            label="Additional info",
            style=nextcord.TextInputStyle.paragraph,
            placeholder="If you have any additional info, put it here. If not, leave it blank.",
            required=False,
            max_length=500,
            custom_id="tickets:report:field:info",
        )
        self.add_item(self.info)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        if nextcord.utils.get(interaction.user.roles, id=864248045226819634): # Ticket blacklist role
            return await interaction.response.send_message("You are ticket blacklisted! You can't report!", ephemeral=True)
        await interaction.response.defer()
        # Check if there are over 1000 tickets
        tickets = await utils.db.reportticket.count()
        if tickets >= 1000:
            return await interaction.followup.send("There are too many tickets! Please try to create a report later.", ephemeral=True)
        # Check if the user being reported has already been banned
        if await utils.db.ticket.find_first(where={"reported": self.username.value, "punishment": "pban", "date": {"gte": datetime.now() - timedelta(days=3)}}):
            return await interaction.followup.send("This user has already been banned!", ephemeral=True)
        # Check if an active ticket already exists
        if await utils.db.reportticket.find_first(where={"reported": self.username.value}):
            return await interaction.followup.send("An active ticket already exists for this user!", ephemeral=True)
        # Check if evidence is a valid URL and if it is a Streamable link
        if "streamable.com" in self.evidence.value or self.evidence.value.startswith("file://"):
            await interaction.followup.send("Invalid evidence URL! (Please use medal.tv or YouTube to upload the video evidence)", ephemeral=True)
            return
        response = f"**Ticket opened by:** {interaction.user.mention}."
        # Create embed
        embed = nextcord.Embed(
            title="Rulebreaker report",
            description=response,
            color=nextcord.Color.green()
        )
        # Set embed footer
        embed.set_footer(text="Made by @Super02#1337")
        # Set embed fields
        embed.add_field(name="Rulebreaker username", value=self.username.value, inline=False)
        embed.add_field(name="Evidence", value=self.evidence.value, inline=False)
        embed.add_field(name="Reason", value=self.reason.value, inline=False)
        filtered_username = self.username.value.replace("_", "\_").replace("*", "\*").replace("`", "\`")
        async with aiohttp.ClientSession() as session:
            headers = {"api-key": os.getenv("BLOXLINK_API_KEY")}
            async with session.get(f"https://v3.blox.link/developer/discord/{interaction.user.id}?guildId={interaction.guild.id}", headers=headers) as http_response:
                if http_response.status == 200:
                    json_response = await http_response.json()
                    r_username = json_response['user']['primaryAccount']
                    async with session.get(f"https://users.roblox.com/v1/users/{r_username}") as username_response:
                        username_data = await username_response.json()
                        reporter_username = username_data["name"]
                else:
                    reporter_username = interaction.user.display_name
            reporter_username = reporter_username.replace("_", "\_").replace("*", "\*").replace("`", "\`").replace(" ", "")
        response = f"\n**Rulebreaker username:** {filtered_username}\n**Evidence:** {self.evidence.value}\n**Reason:** {self.reason.value}\n**Reporter:** {reporter_username}"
        if self.info.value:
            response += f"\n**Additional info:** {self.info.value}"
            embed.add_field(name="Additional info", value=self.info.value, inline=False)
        # Set thumbnail
        avatar_url = await get_avatar(name=self.username.value)
        if(avatar_url == None):
            await self.bot.get_channel(1082774385145954324).send(f"{interaction.user} attempted to report ``{self.username.value}`` but the user does not exist!")
            return await interaction.followup.send("Reported user does not exist! If you wish to report multiple rulebreakers please create a ticket for each user. You can use the same clip multiple times and specify timestamps in the additional info box.", ephemeral=True)
        embed.set_thumbnail(avatar_url)
        # Staff ticket buttons
        #open_ticket = await self.bot.get_channel(1072630661933965342).send(embed=embed, view=StaffReportTicketButtons(self.bot))
        open_ticket = await self.bot.get_channel(1072630661933965342).send("New ticket loading...")
        # Create ticket in database
        ticket = await utils.db.reportticket.create({
            "messageId": str(open_ticket.id),
            "reporter": str(interaction.user.id),
            "reported": self.username.value,
            "evidence": self.evidence.value,
            "reason": self.reason.value,
            "additionalInfo": self.info.value,
        })
        response += f"\n**ID:** report-{ticket.id}"
        await open_ticket.edit(content=response, view=StaffReportTicketButtons(self.bot))
        requests.post("https://discord.com/api/webhooks/1090697011168297020/a8Z_u4uiFxKU5aQ_ROiUKCNeNftGn79wjNge4Ll-uR4hqQwzwFW6-drX-9J8A5W-Vo53", json={"content": f"New report ticket opened by {interaction.user} report number: ``report-{ticket.id}`` and the message ID: ``{open_ticket.id}``"})
        # Send message to user
        await interaction.followup.send(f"Your ticket reporting ``{self.username.value}`` has the report number: ``report-{ticket.id}``. If we need further details you will be notified.", ephemeral=True)


class Appeal(nextcord.ui.Modal):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(
            "False ban appeal",
            timeout=None,
            custom_id="tickets:appeal:init",
        )
        self.reason = nextcord.ui.TextInput(
            label="Ban reason",
            min_length=2,
            required=True,
            max_length=50,
            custom_id="tickets:appeal:field:reason",
        )
        self.add_item(self.reason)

        self.explanation = nextcord.ui.TextInput(
            label="Explanation",
            placeholder="Do not use this to appeal exploiter bans",
            style=nextcord.TextInputStyle.paragraph,
            required=True,
            max_length=1000,
            custom_id="tickets:appeal:field:evidence",
        )
        self.add_item(self.explanation)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        if nextcord.utils.get(interaction.user.roles, id=864248045226819634):
            return await interaction.response.send_message("You are ticket blacklisted! You can't appeal!", ephemeral=True)
        await interaction.response.defer()
        async with aiohttp.ClientSession() as session:
            headers = {"api-key": os.getenv("BLOXLINK_API_KEY")}
            async with session.get(f"https://v3.blox.link/developer/discord/{interaction.user.id}?guildId={interaction.guild.id}", headers=headers) as response:
                if response.status != 200:
                    avatar_url = await get_avatar(name=interaction.user.name)
                    r_username = interaction.user.name
                else:
                    json_response = await response.json()
                    r_username = json_response['user']['primaryAccount']
                    avatar_url = await get_avatar(userid=r_username)
                if avatar_url is None:
                    return await interaction.followup.send("The username does not exist!", ephemeral=True)
                async with session.get(f"https://users.roblox.com/v1/users/{r_username}") as username_response:
                    username_data = await username_response.json()
                    r_username = username_data["name"]
        if r_username == None:
            r_username = interaction.user.display_name
        db_user = await utils.db.user.find_first(where={"discord_id": str(interaction.user.id)})
        if db_user == None:
            await utils.db.user.create({
                "discord_id": str(interaction.user.id),
                "last_appeal": str(datetime.now().timestamp())
            })
        else:
            if db_user.last_appeal != None and not utils.Utils().get_permission_level(2).predicate(interaction):
                if datetime.now().timestamp() < float(db_user.last_appeal)+604800:
                    return await interaction.followup.send("You can only appeal once every 7 days!", ephemeral=True)
            await utils.db.user.update(where={"id": db_user.id}, data={"last_appeal": str(datetime.now().timestamp())})
        response = f"Ticket opened by {interaction.user.mention}."
        # Create embed
        embed = nextcord.Embed(
            title="Appeal",
            description=response,
            color=nextcord.Color.green()
        )
        # Set embed footer
        embed.set_footer(text="Made by @Super02#1337")
        # Set embed fields
        embed.add_field(name="Username", value=r_username, inline=False)
        embed.add_field(name="Ban reason", value=self.reason.value, inline=False)
        embed.add_field(name="Explanation", value=self.explanation.value, inline=False)
        # Set thumbnail
        embed.set_thumbnail(avatar_url)
        view=StaffAppealTicketButtons(self.bot)
        msg = await self.bot.get_channel(1077293993756463226).send(embed=embed, view=view)
        ticket = await utils.db.appealticket.create({
            "discord_id": str(interaction.user.id),
            "messageId": str(msg.id),
            "reason": self.reason.value,
            "appeal": self.explanation.value,
            "username": r_username,
        })
        # Send message
        await interaction.followup.send(f"Your ticket number is: ``appeal-{ticket.id}``. If we need further details you will be notified.", ephemeral=True)

def setup(bot):
  bot.add_cog(tickets(bot))
