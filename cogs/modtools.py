from nextcord.ext import commands
import nextcord
from nextcord import Interaction, SlashOption, Member
from utils import db
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import os
import utils
import nextcord.ext.application_checks
import cooldowns
import math
import calendar


class modtools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.staff_role = 820249824757678080
        self.ticket_record_channel = 874005264846696449
        self.strike_log_channel = 884447914703859732
        self.staff_announcement_channel = 820289776933928981
        self.moderation = True
        self.warned = []
        
    @commands.Cog.listener()
    async def on_ready(self):
        print("Modtools cog ready!")

    @nextcord.slash_command(description="Show your ticket stats for yourself, or others",)
    @utils.Utils().get_permission_level(8)
    async def view_ticketstats(self, interaction: Interaction, _from: str = SlashOption(name="from", required=False, description="In format day-month-year (Defaults to start of the month)"), to: str = SlashOption(name="to", required=False, description="In format day-month-year (Defaults to end of the month)"), member: Member = SlashOption(name="member", description="Member to view stats for", required=False)):
        if member is None:
            member = interaction.user
        try:
            if(to is None):
                to = datetime.now().replace(day=calendar.monthrange(datetime.now().year, datetime.now().month)[1], hour=0, minute=0, second=0)
            else:
                to = datetime.strptime(to, "%d-%m-%Y")
            if(_from is None):
                _from = datetime.now().replace(day=1, hour=0, minute=0, second=0)
            else:
                _from = datetime.strptime(_from, "%d-%m-%Y")
        except:
            await interaction.response.send_message("Invalid date format! Use the format dd-mm-yyyy ex. 02-01-2023 (Jan 2nd 2023)", ephemeral=True)
            return
        _from = _from.replace(hour=0, minute=0, second=0)
        to = to.replace(hour=23, minute=59, second=59)
        days = (to - _from).days
        # Start time countdown
        time = datetime.now()
        status_message = await interaction.response.send_message(f"Generating stats... Eta: <t:{int((datetime.now() + timedelta(seconds=days*12)).timestamp())}:R>")
        # Make sure the datetime object is from the amount of days ago ignoring seconds, hours and minutes
        messages = await self.bot.get_channel(self.ticket_record_channel).history(limit=None, after=_from, before=to).flatten()
        print(len(messages))
        tickets = 0
        ticket_bonus = 0
        for message in messages:
            if(message.content.lower() == "ticket record loading..."):
                continue
            mult = 1.0
            multiplier = await db.ticketpurges.find_first(where={"start": {"lte": message.created_at}, "end": {"gte": message.created_at}})
            if multiplier is not None:
                mult = multiplier.multiplier
            if(message.author.id == member.id):
                tickets += 1
                ticket_bonus += mult-1.0
            elif(message.author.id == self.bot.user.id):
                try:
                    moderator_id = message.content.split("Moderator: ",1)[1][2:-1]
                    if(len(moderator_id.split("\n")) > 1):
                        moderator_id = moderator_id.split("\n")[0][:-1]
                except Exception as e:
                    await utils.Utils().log_error(self.bot, f"Error in ticketstats command: {e}. Message: {message.content}. Message ID: {message.id}. Message link https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}")
                    continue
                if(moderator_id == str(member.id)):
                    tickets += 1
                    if message.content.startswith("Appeal:"):
                        ticket_bonus -= 0.5
                    else:
                        ticket_bonus += mult-1.0
        # Add ticket bonus for each age verification
        age_verifications = await db.ageverification.find_many(where={"date": {"gte": _from, "lte": to}, "verified_by": str(member.id)})
        requested_verifications = await db.ageverification.find_many(where={"date": {"gte": _from, "lte": to}, "requested_by": str(member.id)})
        age_bonus = 0
        for age_verification in age_verifications:
            age_bonus += 0.5
        for requested_verification in requested_verifications:
            age_bonus += 0.2
        ticket_bonus += age_bonus if age_bonus < 100 else 100
        time = datetime.now() - time
        embed = nextcord.Embed(title=f"Ticket stats for {member}", description=f"From: <t:{int(_from.timestamp())}:f> to <t:{int(to.timestamp())}:f>", color=0x00ff00)
        embed.add_field(name="Tickets", value=f"{round(tickets)}")
        embed.add_field(name="Ticket bonus", value=f"{round(ticket_bonus)}")
        embed.add_field(name="Total tickets", value=f"{tickets+round(ticket_bonus)}")
        embed.add_field(name="Notice", value="Ticket bonus might be negative if you have done appeal tickets. This is because appeal tickets only count as half a ticket. Total tickets will still increase by 0.5 for an appeal ticket. If you are confused about the ticket bonus, just ignore it.", inline=False)
        embed.set_footer(text=f"Generated in {time.seconds}.{time.microseconds} seconds.")
        await status_message.edit(content="", embed=embed)

    @nextcord.slash_command(
        description="Show ticket stats",
        default_member_permissions=8,
    )
    @utils.Utils().get_permission_level(3)
    async def ticketstats(self, interaction: Interaction, _from: str = SlashOption(name="from", required=True, description="In format day-month-year"), to: str = SlashOption(name="to", required=True, description="In format day-month-year"), quota: int = SlashOption(name="quota", required=False, description="The amount of tickets that should be done in the given time period"), punish: bool = SlashOption(name="punish", required=False, description="Punish staff that didn't meet the quota")):
        await interaction.response.defer()
        try:
            _from = datetime.strptime(_from, "%d-%m-%Y")
            _from = _from.replace(hour=0, minute=0, second=0)
            to = datetime.strptime(to, "%d-%m-%Y")
        except:
            await interaction.followup.send("Invalid date format! Use the format dd-mm-yyyy ex. 02-01-2023 (Jan 2nd 2023)", ephemeral=True)
            return
        to = to.replace(hour=23, minute=59, second=59)
        days = (to - _from).days
        # Start time countdown
        time = datetime.now()
        status_message = await interaction.channel.send(f"Generating stats... Eta: <t:{int((datetime.now() + timedelta(seconds=days*12)).timestamp())}:R> <:amogus:1096138125232840756>")
        staff = utils.Utils().get_staff(self.bot, True)
        # Loop through all messages in the ticket record channel to get the amount of tickets by checking for messages sent by a staff member
        # Make sure the datetime object is from the amount of days ago ignoring seconds, hours and minutes
        messages = await self.bot.get_channel(self.ticket_record_channel).history(limit=None, after=_from, before=to).flatten()
        print(len(messages))
        tickets_done = {}
        for message in messages:
            # Check if staff is mentioned by bot in message
            bot_logged = False
            moderator = None
            if(message.content.lower() == "ticket record loading..."):
                continue
            if(message.author.id == self.bot.user.id):
                bot_logged = True
                try:
                    # Find text in message after "Moderator: " and before the next newline
                    moderator_id = message.content.split("Moderator: ",1)[1].split("\n")[0][2:-1]
                except Exception as e:
                    await utils.Utils().log_error(self.bot, f"Error in ticketstats command: {e}. Message: {message.content}. Message ID: {message.id}. Message link https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}")
                    continue
                
            if message.author in staff or bot_logged:
                ticket_staff_id = int(moderator_id) if message.author.id == self.bot.user.id else message.author.id
                mult = 1.0
                # Check if a multiplier was active on the date of the ticket
                multiplier = await db.ticketpurges.find_first(where={"start": {"lte": message.created_at}, "end": {"gte": message.created_at}})
                if multiplier:
                    mult = multiplier.multiplier
                if message.content.startswith("Appeal:"):
                    mult = 0.5
                if ticket_staff_id in tickets_done:
                    tickets_done[ticket_staff_id] += mult
                else:
                    tickets_done[ticket_staff_id] = mult
        # Loop through each staff member to add some bonus
        for staff_member in staff:
            age_verifications = await db.ageverification.find_many(where={"date": {"gte": _from, "lte": to}, "verified_by": str(staff_member.id)})
            requested_verifications = await db.ageverification.find_many(where={"date": {"gte": _from, "lte": to}, "requested_by": str(staff_member.id)})
            age_bonus = 0
            for age_verification in age_verifications:
                age_bonus += 0.5
            for requested_verification in requested_verifications:
                age_bonus += 0.2
            tickets_done[staff_member.id] = tickets_done.get(staff_member.id, 0) + age_bonus
        # Sort staff by amount of tickets done in descending order and include staff members who have not done any tickets
        staff = sorted(staff, key=lambda staff_member: tickets_done.get(staff_member.id, 0), reverse=True)
        # Filter out staff members who have done over the quota
        staff_quota = {}
        if quota:
            for staff_member in staff:
                # Check if staff member is quota exempt
                personal_quota = await utils.Utils().get_personal_quota(_from, to, staff_member.id)
                staff_quota[staff_member.id] = round(personal_quota)
            staff = [staff_member for staff_member in staff if (tickets_done.get(staff_member.id, 0) < quota or tickets_done.get(staff_member.id, 0) < staff_quota.get(staff_member.id, 0))]
        # Create a send embed to handle the stats
        # Make sure the plot is readable with the name sizes
        # Make sure staff names are not cut off
        plt.rcParams.update({'font.size': 70})
        # Make a lot of space for the staff names
        plt.rcParams.update({'figure.autolayout': True})
        # Make the bar chart plot large
        plt.figure(figsize=(100, 50))
        # Make sure staff names are readable and vertical
        plt.xticks(rotation=90)
        # Create a text file with information about how many tickets each staff member has done
        with open("chart.txt", "w") as file:
            for staff_member in staff:
                # Create a bar chart for each staff member
                file.write(f"{staff_member.name}#{staff_member.discriminator}: {tickets_done.get(staff_member.id, 0)}\n")
                plt.bar(f"{staff_member.name}#{staff_member.discriminator}", tickets_done.get(staff_member.id, 0))
        # Save the chart as a file object
        plt.savefig("chart.png")
        # Send the chart and text file
        await interaction.channel.send(file=nextcord.File("chart.png"))
        await interaction.channel.send(file=nextcord.File("chart.txt"))
        # Epoch timestamp from _from
        await interaction.followup.send(f"Showing ticket stats for the last {days} days. (From <t:{int(_from.timestamp())}:f>) to <t:{int(to.timestamp())}:f>)")
        # End time countdown
        time = datetime.now() - time
        # Edit the status message
        await status_message.edit(content=f"Generated stats in: {time.total_seconds()} seconds")
        # Delete the text file
        os.remove("chart.txt")
        # Delete the chart file
        os.remove("chart.png")
        staff = utils.Utils().get_staff(self.bot)
        # Round all the tickets done
        tickets_done = {staff_member.id: round(tickets_done.get(staff_member.id, 0)) for staff_member in staff}
        if punish:
            # Punish staff who did not meet the quota
            punishments = "**Punishments**\n"
            punishment_functions = []
            for staff_member in staff:
                # Check if staff member is quota exempt
                custom_quota = quota if staff_quota.get(staff_member.id, None) == None else staff_quota.get(staff_member.id, 0)
                if tickets_done.get(staff_member.id, 0) < custom_quota:
                    # Check how many times staff member is mentioned in strike-log channel
                    strikes = 0
                    warnings = 0
                    given_strike = False
                    given_warning = False
                    messages = await self.bot.get_channel(self.strike_log_channel).history(limit=None).flatten()
                    for message in messages:
                        # Warnings are invalid after 3 months and stikes are invalid after 4 months
                        # Check if staff member is mentioned in message
                        if staff_member.mention in message.content:
                            if("warning: " in message.content.lower() and (datetime.now() - message.created_at.replace(tzinfo=None)).days < 90):
                                warnings += 1
                            elif("strike: " in message.content.lower() and (datetime.now() - message.created_at.replace(tzinfo=None)).days < 120):
                                strikes += 1
                    # If staff member has done less than 10% of quota away from the quota give a warning
                    if tickets_done.get(staff_member.id, 0) > custom_quota*0.9:
                        given_warning = True
                        warnings += 1
                    else:
                        given_strike = True
                        strikes += 1
                        given_warning = False # Change if you want to give strikes instead of warnings
                        warnings += 1
                    if warnings > 2 and given_warning:
                        strikes += 1
                        warnings = 0
                        given_warning = False
                        given_strike = True
                    if given_warning:
                        warning_msg = await self.bot.get_channel(self.strike_log_channel).send(f"Name of the staff member: {staff_member.mention}\nReason for warning: Not meeting the ticket quota (Did {tickets_done.get(staff_member.id, 0)} had to do {custom_quota}).\nWarning number: {warnings}")
                        await self.add_warning(self.bot.user.id, staff_member, f"Not meeting the ticket quota (Did {tickets_done.get(staff_member.id, 0)} had to do {custom_quota}).", warning_msg.id)
                        punishments += f"{staff_member.mention} was given a warning for not meeting the ticket quota (Did {tickets_done.get(staff_member.id, 0)} had to do {custom_quota}).\n"
                    if strikes == 1 and given_strike:
                        # Warn staff member
                        # If a staff member is less than 10 away from the quota, give them a warning
                        strike_msg = await self.bot.get_channel(self.strike_log_channel).send(f"Name of the staff member: {staff_member.mention}\nReason for strike: Not meeting the ticket quota (Did {tickets_done.get(staff_member.id, 0)} had to do {custom_quota}).\nStrike number: {strikes}")
                        await self.add_strike(self.bot.user.id, staff_member, f"Not meeting the ticket quota (Did {tickets_done.get(staff_member.id, 0)} had to do {custom_quota}).", strike_msg.id)
                        punishments += f"{staff_member.mention} was given a strike for not meeting the ticket quota (Did {tickets_done.get(staff_member.id, 0)} had to do {custom_quota}).\n"
                    if strikes == 2 and given_strike:
                        # Demote staff member
                        new_rank = await utils.Utils().demote(staff_member)
                        #new_rank = "PLACEHOLDER"
                        strike_msg = await self.bot.get_channel(self.strike_log_channel).send(f"Name of the staff member: {staff_member.mention}\nReason for strike: Not meeting the ticket quota (Did {tickets_done.get(staff_member.id, 0)} had to do {custom_quota}).\nStrike number: {strikes}")
                        await self.add_strike(self.bot.user.id, staff_member, f"Not meeting the ticket quota (Did {tickets_done.get(staff_member.id, 0)} had to do {custom_quota}).", strike_msg.id)
                        punishments += f"{staff_member.mention} was demoted to {new_rank} for not meeting the ticket quota (Did {tickets_done.get(staff_member.id, 0)} had to do {custom_quota}). (Has {strikes} strikes)\n"
                    if strikes >= 3 and given_strike:
                        # Rank strip staff member
                        await utils.Utils().demote(staff_member, rank_strip=True)
                        strike_msg = await self.bot.get_channel(self.strike_log_channel).send(f"Name of the staff member: {staff_member.mention}\nReason for strike: Not meeting the ticket quota (Did {tickets_done.get(staff_member.id, 0)} had to do {custom_quota}).\nStrike number: {strikes}")
                        await self.add_strike(self.bot.user.id, staff_member, f"Not meeting the ticket quota (Did {tickets_done.get(staff_member.id, 0)} had to do {custom_quota}).", strike_msg.id)
                        punishments += f"{staff_member.mention} was rank stripped for not meeting the ticket quota. (Did {tickets_done.get(staff_member.id, 0)} had to do {custom_quota}) (Has {strikes} strikes)\n"
            if(punishments == "**Punishments**\n"):
                return
            #view = utils.ConfirmationButtons()
            #await self.bot.get_channel(996450841303191643).send("Are you sure you want to give these punishments?", view=view)
            #await view.wait()
            #if not view.value:
            #    return
            #else:
            #    for punishment_function in punishment_functions:
            #        await punishment_function
            #    # Send to staff announcement channel
            if(len(punishments) > 2000):
                # Write punishments to file
                with open("punishments.txt", "w") as file:
                    file.write(punishments)
                await self.bot.get_channel(self.staff_announcement_channel).send(file=nextcord.File("punishments.txt"))
                os.remove("punishments.txt")
            else:
                await self.bot.get_channel(self.staff_announcement_channel).send(punishments)
            #    #print(punishments)
    
    # Remove old strikes/warnings
    @nextcord.slash_command(name="fix_strikes", description="Remove strikes and warnings that are expired.")
    @utils.Utils().get_permission_level(8)
    @cooldowns.cooldown(1, 3, bucket=cooldowns.buckets.SlashBucket.author)
    async def fix_strikes(self, interaction: Interaction):
        await interaction.response.defer()
        # Remove old strikes (Older than 120 days)
        strikes = await db.strikes.find_many(where={"date": {"lte": datetime.now() - timedelta(days=120)}})
        print(strikes)
        strikes_removed = 0
        for strike in strikes:
            try:
                msg = await self.bot.get_channel(self.strike_log_channel).fetch_message(int(strike.message_id))
                await msg.delete()
                await db.strikes.delete(where={"id": strike.id})
                strikes_removed += 1
            except Exception as e:
                print(e)
                pass
        # Remove old warnings
        warnings = await db.warning.find_many(where={"date": {"lte": datetime.now() - timedelta(days=90)}})
        warnings_removed = 0
        for warning in warnings:
            try:
                msg = await self.bot.get_channel(self.strike_log_channel).fetch_message(int(warning.message_id))
                await msg.delete()
                await db.warning.delete(where={"id": warning.id})
                warnings_removed += 1
            except Exception as e:
                print(e)
                pass
        await interaction.followup.send(f"Removed {strikes_removed} strikes and {warnings_removed} warnings.")

    # Give strike
    @nextcord.slash_command(name="strike", description="Give a strike to a staff member.")
    @utils.Utils().get_permission_level(3)
    async def strike(self, interaction: Interaction, staff_member: nextcord.Member = SlashOption(name="staff_member", required=True, description="Staff member to give a strike to"), reason: str = SlashOption(name="reason", required=True, description="Reason for strike")):
        strikes = await db.staff.find_first(where={"discord_id": str(staff_member.id)}, include={"strikes": True})
        strike_number = len(strikes.strikes) + 1
        strike_msg = await self.bot.get_channel(self.strike_log_channel).send(f"Name of the staff member: {staff_member.mention}\nReason for strike: {reason}\nStrike number: {strike_number}\nGiven by: {interaction.user.mention}")
        await self.add_strike(str(interaction.user.id), staff_member, reason, strike_msg.id)
        await interaction.response.send_message(f"Strike given to {staff_member.mention} for {reason}.", ephemeral=True)
    
    # Give warning
    @nextcord.slash_command(name="warning", description="Give a warning to a staff member.")
    @utils.Utils().get_permission_level(3)
    async def warning(self, interaction: Interaction, staff_member: nextcord.Member = SlashOption(name="staff_member", required=True, description="Staff member to give a warning to"), reason: str = SlashOption(name="reason", required=True, description="Reason for warning")):
        warnings = await db.staff.find_first(where={"discord_id": str(staff_member.id)}, include={"warning": True})
        warning_number = len(warnings.warning) + 1 if warnings.warning != None else 1
        warning_msg = await self.bot.get_channel(self.strike_log_channel).send(f"Name of the staff member: {staff_member.mention}\nReason for warning: {reason}\nWarning number: {warning_number}\nGiven by: {interaction.user.mention}")
        await self.add_warning(str(interaction.user.id), staff_member, reason, warning_msg.id)
        await interaction.response.send_message(f"Warning given to {staff_member.mention} for {reason}.", ephemeral=True)

    # A command to view the amount of currently open ticekts
    @nextcord.slash_command(name="ticket_amount", description="View the amount of currently open tickets.")
    @utils.Utils().get_permission_level(8)
    async def ticket_count(self, interaction: Interaction):
        # Get the amount of tickets
        report_tickets = await db.reportticket.count()
        appeal_tickets = await db.appealticket.count()
        # Send the amount of tickets
        await interaction.response.send_message(f"There are currently {report_tickets} report tickets and {appeal_tickets} appeal tickets open. A total of {report_tickets+appeal_tickets}", ephemeral=True)

    # Create a ticket purge that allows for a multiplier on the amount of tickets that has been done so it counts towards the ticket quota
    @nextcord.slash_command(name="ticket_purge", description="Make tickets count towards the quota with a multiplier in a given time period.")
    @utils.Utils().get_permission_level(3)
    async def ticket_purge(self, interaction: Interaction, multiplier: float = SlashOption(name="multiplier", required=True, description="Multiplier for the amount of tickets done in the time period"), duration: int = SlashOption(name="duration", required=True, description="In hours from start"), start: str = SlashOption(name="from", required=False, description="In format day-month-year (Defaults to today)")):
        if(duration < 1):
            await interaction.response.send_message("Duration must be at least 1 hour.", ephemeral=True)
            return
        start = datetime.strptime(start, "%d-%m-%Y") if start else datetime.now()
        end = start + timedelta(hours=duration)
        # Create a new ticket purge in the database
        ticket_purge = await db.ticketpurges.create(data={"multiplier": multiplier, "end": end, "start": start, "created_by": str(interaction.user.id)})
        # Send a message to the staff announcement channel
        embed = nextcord.Embed(title="Ticket purge", description=f"A new ticket purge has been created!", color=nextcord.Color.green())
        embed.add_field(name="Multiplier", value=f"``{multiplier}``", inline=False)
        embed.add_field(name="Start", value=f"<t:{int(start.timestamp())}:R>", inline=False)
        embed.add_field(name="End", value=f"<t:{int(end.timestamp())}:R>", inline=False)
        embed.add_field(name="Created by", value=f"<@{interaction.user.id}>", inline=False)
        embed.set_footer(text=f"Ticket purge ID: {ticket_purge.id}")
        await self.bot.get_channel(1098530872933757019).send(embed=embed)
        # Send a message to the interaction
        await interaction.response.send_message(f"Ticket purge created with a multiplier of {multiplier} from <t:{int(start.timestamp())}:f> to <t:{int(end.timestamp())}:f>.", ephemeral=True)

    # Get recommended quota
    @nextcord.slash_command(name="get_recommended_quota", description="Get the recommended ticket quota.")
    @utils.Utils().get_permission_level(3)
    async def get_recommended_quota(self, interaction: Interaction, time_period: int = SlashOption(name="time_period", required=False, description="In days (Defaults to 7)")):
        time_period = time_period if time_period else 7
        # Get the amount of tickets
        tickets = await db.ticket.count(where={"date": {"gte": datetime.now() - timedelta(days=time_period)}})
        # Get the amount of staff members
        staff_members = utils.Utils().get_staff(self.bot, False)
        # Calculate the recommended quota
        recommended_quota = (math.ceil(tickets / len(staff_members))/time_period)*30
        # Send the recommended quota
        await interaction.response.send_message(f"The recommended ticket quota for the last {time_period} days is {recommended_quota}.", ephemeral=True)

    # Show a list over all the ticket purges
    @nextcord.slash_command(name="ticket_purge_list", description="Show a list over all the ticket purges.")
    @utils.Utils().get_permission_level(8)
    async def ticket_purge_list(self, interaction: Interaction, page: int = SlashOption(name="page", required=False, description="Page to show (Defaults to 1)")):
        # Get all the ticket purges
        pages = math.ceil(await db.ticketpurges.count() / 10)
        page = page if page else 1
        if page > pages or page < 1:
            page = pages
        ticket_purges = await db.ticketpurges.find_many(order={"start": "desc"}, skip=(page-1)*10, take=10)
        embed = nextcord.Embed(title="Ticket purges", description="List over all the ticket purges.", color=0x00ff00)
        # Loop over all the ticket purges
        for ticket_purge in ticket_purges:
            # Get the staff member who created the ticket purge
            staff_member = await self.bot.fetch_user(int(ticket_purge.created_by))
            # Add the ticket purge to the embed
            embed.add_field(name=f"Ticket purge #{ticket_purge.id}", value=f"Multiplier: {ticket_purge.multiplier}\nStart: <t:{int(ticket_purge.start.timestamp())}:f>\nEnd: <t:{int(ticket_purge.end.timestamp())}:f>\nCreated by: {staff_member.mention}", inline=True)
        embed.set_footer(text=f"Page {page}/{pages}")
        # Send the embed
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.slash_command(name="checkout_create", description="Register an inactivity checkout in a time period. (In format day-month-year)")
    @utils.Utils().get_permission_level(8)
    async def checkout_create(self, interaction: Interaction, reason: str = SlashOption(name="reason", required=True, description="Reason for inactivity"), _from: str = SlashOption(name="from", required=False, description="In format day-month-year (Defaults to today)"), to: str = SlashOption(name="to", required=False, description="In format day-month-year (Defaults to never end)"), staff_member: nextcord.Member = SlashOption(name="staff_member", required=False, description="Staff member who is marked as inactive")):
        await interaction.response.defer()
        try:
            if(_from == None):
                _from = datetime.now()
            else:
                _from = datetime.strptime(_from, "%d-%m-%Y")
            _from = _from.replace(hour=0, minute=0, second=0)
            if(to == None):
                to = datetime(3000, 1, 1)
            else:
                to = datetime.strptime(to, "%d-%m-%Y")
                to = to.replace(hour=23, minute=59, second=59)
        except ValueError:
            return await interaction.followup.send("Invalid date format. (In format dd-mm-yyyy)", ephemeral=True)
        days = (to - _from).days
        staff_member = interaction.user if staff_member == None else staff_member
        #approved = utils.Utils().get_permission_level(4).predicate(interaction) # If the user has permission level 4 or lower, the inactivity is automatically approved
        approved = True
        if staff_member != interaction.user and not utils.Utils().get_permission_level(4).predicate(interaction):
            return await interaction.followup.send("You do not have permission to register inactivity for other staff members.", ephemeral=True)
        if(_from > to):
            return await interaction.followup.send("From date cannot be after to date. <:amogus:1096138125232840756>", ephemeral=True)
        # Register inactivity in the database using the same way as quota_whitelist
        if(await db.staff.find_first(where={"discord_id": str(staff_member.id)}) == None):
            await db.staff.create(data={
                    "discord_id": str(staff_member.id),
                    "quota_exceptions": {
                        "create": [
                            {
                                "reason": reason,
                                "start_date": _from,
                                "end_date": to,
                                "approved": approved,
                            }
                        ]
                    }
                }
            )
        else:
            # Get the staff object from the database
            staff = await db.staff.find_first(where={"discord_id": str(staff_member.id)}, include={"quota_exceptions": True})
            # Find the active quota exception
            for quota_exception in staff.quota_exceptions:
                if(quota_exception.end_date > datetime.now(quota_exception.end_date.tzinfo)):
                    if(await utils.Utils().confirm(interaction, f"An inactivity checkout is already registered for {staff_member}. (Until <t:{int(quota_exception.end_date.timestamp())}:f>) Do you want to change it to <t:{int(to.timestamp())}:f>?")):
                        # Extend the whitelist by updating the already existing whitelist
                        await db.quota_exception.update(where={"id": quota_exception.id}, data={
                            "end_date": to
                        })
                        await self.bot.get_channel(utils.Utils().get_staff_inactivity_channel()).send(f"Inactivity checkout changed\nID: #{quota_exception.id}\nName: {staff_member.mention}\nReason: {reason}\nStarts: <t:{int(_from.timestamp())}:f>\nEnds: <t:{int(to.timestamp())}:f>")
                        return await interaction.followup.send(f"Extended inactivity checkout for {days} days. (Until <t:{int(to.timestamp())}:f>)", ephemeral=True)
                    else:
                        return await interaction.followup.send("Cancelled.", ephemeral=True)
                # Update the staff object in the database
            quota_exception = await db.staff.update(where={"discord_id": str(staff_member.id)}, data={
                "quota_exceptions": {
                    "create": [
                        {
                            "reason": reason,
                            "start_date": _from,
                            "end_date": to,
                            "approved": approved,
                        }
                    ]
                }
            })
            if(quota_exception.quota_exceptions != None and len(quota_exception.quota_exceptions) > 1):
                quota_id = quota_exception.quota_exceptions[0].id if quota_exception.quota_exceptions != [] else None
            else:
                quota_id = "<:ble:1017746610630955088>"
            await self.bot.get_channel(utils.Utils().get_staff_inactivity_channel()).send(f"ID: #{quota_id}\nName: {staff_member.mention}\nReason: {reason}\nStarts: <t:{int(_from.timestamp())}:f>\nEnds: <t:{int(to.timestamp())}:f>.")
            await interaction.followup.send(f"Registered {staff_member} as inactive from <t:{int(_from.timestamp())}:f> to <t:{int(to.timestamp())}:f>.", ephemeral=True)
    
    # Remove inactivity checkout
    @nextcord.slash_command(name="checkout_end", description="End an inactivity checkout.")
    @utils.Utils().get_permission_level(8)
    async def checkout_end(self, interaction: Interaction, staff_member: nextcord.Member = SlashOption(name="staff_member", required=False, description="Staff member who is marked as inactive")):
        await interaction.response.defer()
        staff_member = interaction.user if staff_member == None else staff_member
        if staff_member != interaction.user and not utils.Utils().get_permission_level(4).predicate(interaction):
            return await interaction.followup.send("You do not have permission to end checkouts for other staff members.", ephemeral=True)
        # Get the staff object from the database
        staff = await db.staff.find_first(where={"discord_id": str(staff_member.id)}, include={"quota_exceptions": True})
        # Find the active quota exception
        for quota_exception in staff.quota_exceptions:
            if(quota_exception.end_date > datetime.now(quota_exception.end_date.tzinfo)):
                if(await utils.Utils().confirm(interaction, f"Are you sure you want to end the inactivity checkout for {staff_member}?")):
                    # Remove the inactivity checkout
                    await db.quota_exception.update(where={"id": quota_exception.id}, data={
                        "end_date": datetime.now()
                    })
                    await self.bot.get_channel(utils.Utils().get_staff_inactivity_channel()).send(f"Inactivity checkout for {staff_member.mention} has ended.\nID: #{quota_exception.id}\n")
                    return await interaction.followup.send(f"Ended inactivity checkout for {staff_member}.", ephemeral=True)
                else:
                    return await interaction.followup.send("Cancelled.", ephemeral=True)
        return await interaction.followup.send(f"{staff_member} is not marked as inactive.", ephemeral=True)

    # Delete inactivity checkout
    @nextcord.slash_command(name="checkout_delete", description="Delete an inactivity checkout.")
    @utils.Utils().get_permission_level(8)
    async def checkout_delete(self, interaction: Interaction, checkout_id: int = SlashOption(name="checkout_id", required=True, description="ID of the inactivity checkout to delete")):
        await interaction.response.defer()
        # Get checkout from database with the given ID
        checkout = await db.quota_exception.find_first(where={"id": checkout_id}, include={"staff": True})
        if self.bot.get_user(checkout.staffId) != interaction.user and not utils.Utils().get_permission_level(3).predicate(interaction):
            return await interaction.followup.send("You do not have permission to end checkouts for other staff members. <:amogus:1096138125232840756>", ephemeral=True)
        if(checkout == None):
            return await interaction.followup.send("Could not find an inactivity checkout with that ID.", ephemeral=True)
        if(await utils.Utils().confirm(interaction, f"Are you sure you want to delete the inactivity checkout for {checkout.staff.discord_id}?")):
            # Delete the inactivity checkout
            await db.quota_exception.delete(where={"id": checkout_id})
            await self.bot.get_channel(utils.Utils().get_staff_inactivity_channel()).send(f"Inactivity checkout for {checkout.staff.discord_id} has been deleted.\nID: #{checkout_id}")
            return await interaction.followup.send(f"Deleted inactivity checkout #{checkout_id}.", ephemeral=True)
        else:
            return await interaction.followup.send("Cancelled.", ephemeral=True)

    @nextcord.slash_command(name="checkout_approve", description="Approve an inactivity checkout.")
    @utils.Utils().get_permission_level(3)
    async def checkout_approve(self, interaction: Interaction, checkout_id: int = SlashOption(name="checkout_id", required=True, description="ID of the inactivity checkout to approve")):
        await interaction.response.defer()
        # Get checkout from database with the given ID
        checkout = await db.quota_exception.find_first(where={"id": checkout_id}, include={"staff": True})
        if(checkout == None):
            return await interaction.followup.send("Could not find an inactivity checkout with that ID.", ephemeral=True)
        if(checkout.approved):
            return await interaction.followup.send("The inactivity checkout is already approved.", ephemeral=True)
        # Update the checkout in the database
        await db.quota_exception.update(where={"id": checkout_id}, data={
            "approved": True
        })
        await interaction.followup.send(f"Approved inactivity checkout for {self.bot.get_user(int(checkout.staff.discord_id))}.", ephemeral=True)

    
    @nextcord.slash_command(name="checkout_unapprove", description="Unapprove an inactivity checkout.")
    @utils.Utils().get_permission_level(3)
    async def checkout_unapprove(self, interaction: Interaction, checkout_id: int = SlashOption(name="checkout_id", required=True, description="ID of the inactivity checkout to unapprove")):
        await interaction.response.defer()
        # Get checkout from database with the given ID
        checkout = await db.quota_exception.find_first(where={"id": checkout_id}, include={"staff": True})
        if(checkout == None):
            return await interaction.followup.send("Could not find an inactivity checkout with that ID.", ephemeral=True)
        if(not checkout.approved):
            return await interaction.followup.send("The inactivity checkout is not approved.", ephemeral=True)
        # Update the checkout in the database
        await db.quota_exception.update(where={"id": checkout_id}, data={
            "approved": False
        })
        await interaction.followup.send(f"Unapproved inactivity checkout for {self.bot.get_user(int(checkout.staff.discord_id))}.")
    
    @nextcord.slash_command(name="checkout_list", description="List all whitelisted staff members.")
    @utils.Utils().get_permission_level(8)
    async def checkout_list(self, interaction: Interaction, page: int = SlashOption(name="page", required=False, description="Page to show (Defaults to 1)", default=1)):
        await interaction.response.defer()
        # Get all staff members from the database
        staff = await db.staff.find_many(include={"quota_exceptions": True}, where={"quota_exceptions": {"some": {"end_date": {"gte": datetime.now()}}}}, skip=(page-1)*5, take=5)
        # Create an embed
        embed = nextcord.Embed(title="Staff members with inactivity checkout", color=nextcord.Color.green())
        # Add all whitelisted staff members to the embed
        for staff_member in staff:
            for quota_exception in staff_member.quota_exceptions:
                if(quota_exception.end_date > datetime.now(quota_exception.end_date.tzinfo)):
                    user = self.bot.get_user(int(staff_member.discord_id))
                    embed.add_field(name=f"#{quota_exception.id} {user}", value=f"Approved: {quota_exception.approved}\nUntil <t:{int(quota_exception.end_date.timestamp())}:f> ({quota_exception.reason})", inline=False)
        # Get the amount of found things in staff
        count = await db.staff.count(
            where={
                "quota_exceptions": {
                    "some": {
                        "end_date": {"gte": datetime.now()}
                    }
                }
            }
        )        
        embed.set_footer(text=f"Page {page}/{math.ceil(count/5)}")
        await interaction.followup.send(embed=embed)

    @nextcord.slash_command(
        description="Fills out ticket-record",
    )
    @utils.Utils().get_permission_level(8)
    @cooldowns.cooldown(1, 3, bucket=cooldowns.buckets.SlashBucket.author)
    async def ticket_record(self, interaction: Interaction, name: str = SlashOption(name="name", required=True), punishment: str = SlashOption(name="punishment", required=True), reason: str = SlashOption(name="reason", required=True), evidence: str = SlashOption(name="evidence", required=True), reporter: Member = SlashOption(name="reporter", required=True), is_spoiler: bool = SlashOption(name="spoiler", required=False), additional_info: str = SlashOption(name="additional_info", required=False)):
        if interaction.channel.id == self.ticket_record_channel:
            await interaction.response.send_message("You cannot use this command in this channel!", ephemeral=True)
            return
        # Defer
        await interaction.response.defer()
        try:
            # Check if evidence is a discord message id
            files = []
            try:
                message = await interaction.channel.fetch_message(evidence.split(",")[0])
            except:
                message = False
            if message:
                if(len(evidence.split(",")) > 1):
                    for i in range(len(evidence.split(","))):
                        try:
                            message = await interaction.channel.fetch_message(evidence.split(",")[i])
                            for attachment in message.attachments:
                                files.append(await attachment.to_file(spoiler=True if is_spoiler else False))
                        except:
                            pass
                else:
                    files = [await f.to_file(spoiler=True if is_spoiler else False) for f in message.attachments]
                evidence = "Attached"
            ticket_msg = await self.bot.get_channel(self.ticket_record_channel).send(f"ticket record loading...")
            await utils.Utils().add_ticket(interaction, reporter.id, name, evidence, reason, punishment, ticket_msg.id, additional_info=additional_info)
            message_content = f"Name: {name}\nPunishment: {punishment}\nReason: {reason}\nEvidence: {evidence}\nReporter: {reporter.mention}\nModerator: {interaction.user.mention}"
            if additional_info:
                message_content += f"\nAdditional info: {additional_info}"
            if not files:
                await ticket_msg.edit(content=message_content)
            else:
                await ticket_msg.edit(content=message_content, files=files)
            await interaction.followup.send(f"Ticket-record logged in <#{self.ticket_record_channel}>")
        except Exception as e:
            if type(e) == nextcord.errors.NotFound:
                return
            print(e)
            # Send error message to owner
            await utils.Utils().log_error(self.bot, f"Error in ticket-record command: {e}. \nevidence: {evidence}\nname: {name}\npunishment: {punishment}\nreason: {reason}\nreporter: {reporter}\nis_spoiler: {is_spoiler}\nadditional_info: {additional_info}")
            await interaction.followup.send("Ticket-record not logged! (Error)", ephemeral=True)
            return

    async def add_strike(self, moderator: str, user, reason, message_id):
        # Add strike to the database
        staff = await db.staff.find_first(where={"discord_id": str(user.id)})
        if(staff == None):
            await db.staff.create(data={
                "discord_id": str(user.id),
                "strikes": {
                    "create": [
                        {
                            "reason": reason,
                            "moderator": str(moderator),
                            "message_id": str(message_id)
                        }
                    ]
                }
            })
        else:
            # Update the staff object in the database
            await db.strikes.create(data={
                "reason": reason,
                "moderator": str(moderator),
                "message_id": str(message_id),
                "staff": {
                    "connect": { "id": staff.id}
                }
            })

    async def add_warning(self, moderator, user, reason, message_id):
        # Add warning to the database
        staff = await db.staff.find_first(where={"discord_id": str(user.id)})
        if(staff == None):
            await db.staff.create(data={
                "discord_id": str(user.id),
                "warnings": {
                    "create": [
                        {
                            "reason": reason,
                            "moderator": str(moderator),
                            "message_id": str(message_id)
                        }
                    ]
                }
            })
        else:
            # Update the staff object in the database. Note warnings field may not exist
            await db.warning.create(data={
                "reason": reason,
                "moderator": str(moderator),
                "message_id": str(message_id),
                "staff": {
                    "connect": { "id": staff.id}
                }
            })

    @nextcord.slash_command(
        description="Toggle slap-battles-chat moderation",
    )
    @utils.Utils().get_permission_level(8)
    async def chat_moderation(self, interaction: Interaction):
        if self.moderation:
            self.moderation = False
            await utils.Utils().server_log(f"Slap-battles-chat moderation disabled in <#{interaction.channel.id}> by {interaction.user.id}", self.bot)
            await interaction.response.send_message(f"Slap-battles-chat moderation disabled in <#{interaction.channel.id}>", ephemeral=True)
        else:
            self.moderation = True
            await interaction.response.send_message(f"Slap-battles-chat moderation enabled in <#{interaction.channel.id}>", ephemeral=True)

    # Unban command
    @nextcord.slash_command(
        description="Unban a user",
    )
    @utils.Utils().get_permission_level(8)
    async def unban(self, interaction: Interaction, user: nextcord.User):
        try:
            await interaction.guild.unban(user)
        except:
            await interaction.response.send_message(f"User {user.mention} is not banned! <:amogus:1096138125232840756>", ephemeral=True)
            return
        await utils.Utils().server_log(f"User {user.mention} has been unbanned by {interaction.user.id}", self.bot)
        await interaction.response.send_message(f"User {user.mention} has been unbanned!", ephemeral=True)
    
    # Ban command
    @nextcord.slash_command(
        description="Ban a user",
    )
    @utils.Utils().get_permission_level(8)
    async def ban(self, interaction: Interaction, user: nextcord.User, reason: str):
        try:
            await interaction.guild.ban(user, reason=reason)
        except:
            await interaction.response.send_message(f"User {user.mention} is already banned!", ephemeral=True)
            return
        await utils.Utils().server_log(f"User {user.mention} has been banned by {interaction.user.id} for {reason}", self.bot)
        await interaction.response.send_message(f"User {user.mention} has been banned!", ephemeral=True)
    
    # Kick command
    @nextcord.slash_command(
        description="Kick a user",
    )   
    @utils.Utils().get_permission_level(8)
    async def kick(self, interaction: Interaction, user: nextcord.User, reason: str):
        try:
            await interaction.guild.kick(user, reason=reason)
        except:
            await interaction.response.send_message(f"User {user.mention} is not in the server!", ephemeral=True)
            return
        await utils.Utils().server_log(f"User {user.mention} has been kicked by {interaction.user.id} for {reason}", self.bot)
        await interaction.response.send_message(f"User {user.mention} has been kicked!", ephemeral=True)

    # Mute command
    @nextcord.slash_command(
        description="Mute a user",
    )
    @utils.Utils().get_permission_level(8)
    async def mute(self, interaction: Interaction, member: nextcord.Member, reason: str, seconds: int):
        try:
            # Timeout
            await member.edit(timeout=nextcord.utils.utcnow()+timedelta(seconds=seconds), reason=reason)
        except:
            await interaction.response.send_message(f"User {member.mention} is not in the server!", ephemeral=True)
            return
        await utils.Utils().server_log(f"User {member.mention} has been muted by {interaction.user.id} for {reason}", self.bot)
        await interaction.response.send_message(f"User {member.mention} has been muted!", ephemeral=True)

    # Modstats showing how many people have been ageverified by a moderator
    @nextcord.slash_command(
        description="Show how many people have been ageverified by a moderator",
    )
    @utils.Utils().get_permission_level(8)
    async def modstats(self, interaction: Interaction, moderator: nextcord.User, _from: str = SlashOption(name="from", required=True, description="In format day-month-year"), to: str = SlashOption(name="to", required=True, description="In format day-month-year")):
        try:
            _from = datetime.strptime(_from, "%d-%m-%Y")
            to = datetime.strptime(to, "%d-%m-%Y")
        except:
            await interaction.response.send_message("Invalid date format! Use the format dd-mm-yyyy ex. 02-01-2023 (Jan 2nd 2023)", ephemeral=True)
            return
        _from = _from.replace(hour=0, minute=0, second=0)
        to = to.replace(hour=23, minute=59, second=59)
        # Check how many times the moderator has ageverified people in AgeVerification modal
        ageverifs = await db.ageverification.count(where={"requested_by": str(moderator.id), "date": {"gte": _from, "lte": to}})
        await interaction.response.send_message(f"{moderator.mention} has ageverified {ageverifs} people!", ephemeral=True)

    # On message
    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            # Check if the user has staff team role and exempt them (ID 820249824757678080)
            if(message.author.id == 305246941992976386 or self.moderation == False or message.channel.id != 884509680414650429):
                return
            if(nextcord.utils.get(message.author.roles, id=820249824757678080)):
                return
            blocked_phrases = []
            duo_block = {}
            for phrase in duo_block:
                if phrase in message.content.lower() and duo_block[phrase] in message.content.lower() and message.channel.id == 884509680414650429:
                    await message.delete()
                    if(message.author.id in self.warned):
                        await message.author.timeout(nextcord.utils.utcnow() + timedelta(seconds=600), reason="Keeps advertising private servers in slap battles chat.")
                        try:
                            await message.author.send(f"{message.author.mention} You have been timed out since you keep advertising private server invite links.")
                        except:
                            await message.channel.send(f"{message.author.mention} You have been timed out since you keep advertising private server invite links.")
                        return
                    print(f"Message duo block {message.author}: {message.content}")
                    self.warned.append(message.author.id)
                    try:
                        await message.author.send(f"{message.author.mention} Please do not advertise private servers in <#884509680414650429>! If you want to post links go to the thread created for it: <#1073632094124777573>. Please note that false positives happen, if you did not advertise anything ignore this message.")
                    except:
                        await message.channel.send(f"{message.author.mention} Please do not advertise private servers in <#884509680414650429>! If you want to post links go to the thread created for it: <#1073632094124777573>. Please note that false positives happen, if you did not advertise anything ignore this message.", delete_after=20)
            for phrase in blocked_phrases:
                if phrase.lower() in message.content.lower():
                    await message.delete()
                    print(f"Message block {message.author}: {message.content}")
                    if(message.author.id in self.warned):
                        await message.author.timeout(nextcord.utils.utcnow() + timedelta(seconds=600), reason="Keeps advertising private servers in slap battles chat")
                        try:
                            await message.author.send(f"{message.author.mention} You have been timed out since you keep advertising private server invite links.")
                        except:
                            await message.channel.send(f"{message.author.mention} You have been timed out since you keep advertising private server invite links.")
                        return
                    self.warned.append(message.author.id)
                    try:
                        await message.author.send(f"{message.author.mention} Please do not advertise private servers in <#884509680414650429>! If you want to post links go to the thread created for it: <#1073632094124777573>. Please note that false positives happen, if you did not advertise anything ignore this message.")
                    except:
                        await message.channel.send(f"{message.author.mention} Please do not advertise private servers in <#884509680414650429>! If you want to post links go to the thread created for it: <#1073632094124777573>. Please note that false positives happen, if you did not advertise anything ignore this message.", delete_after=20)
            if "roblox.com/games/6403373529?privateServerLinkCode" in message.content and message.channel.id == 884509680414650429:
                if(not "https://web." in message.content):
                    await message.delete()
                print(f"Message block {message.author}: {message.content}")
                if(message.author.id in self.warned):
                    await message.author.timeout(nextcord.utils.utcnow() + timedelta(seconds=600), reason="Keeps advertising private servers in slap battles chat")
                    try:
                        await message.author.send(f"{message.author.mention} You have been timed out since you keep advertising private server invite links.")
                    except:
                        await message.channel.send(f"{message.author.mention} You have been timed out since you keep advertising private server invite links.")
                    return
                self.warned.append(message.author.id)
                try:
                    await message.author.send(f"{message.author.mention} Please do not advertise private server links in <#884509680414650429>! If you want to post links go to the thread created for it: <#1073632094124777573>")
                except:
                    await message.channel.send(f"{message.author.mention} Please do not advertise private server links in <#884509680414650429>! If you want to post links go to the thread created for it: <#1073632094124777573>", delete_after=20)
        except Exception as e:
            print(e)
            pass
    
    # When message is deleted in strike-log channel look for the message in the database and delete it
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        try:
            if(payload.channel_id == self.strike_log_channel):
                # Check if the message is a strike
                if(await db.strikes.find_first(where={"message_id": str(payload.message_id)}) != None):
                    await db.strikes.delete(where={"message_id": str(payload.message_id)})
                # Check if the message is a warning
                if(await db.warning.find_first(where={"message_id": str(payload.message_id)}) != None):
                    await db.warning.delete(where={"message_id": str(payload.message_id)})
        except Exception as e:
            print(e)
            pass

def setup(bot):
    bot.add_cog(modtools(bot))
