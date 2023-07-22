from prisma import Prisma
import asyncio
import nextcord
import nextcord.ext.application_checks
import random
import datetime
import calendar

class Utils:
    def __init__(self):
        self.db = None
        self.connected = False
        self.inactivity_channel = 860374696457142292
        self.ticket_records_channel = 874005264846696449
        self.appeal_category = 996499392582393996
        self.report_category = 912761558608797706
        self.guild_id = 820093197933740062
        self.staff_role = 820249824757678080
        self.age_verified_role_id = 1071220294557126676
    
    def get_staff_inactivity_channel(self):
        return self.inactivity_channel


    def get_db(self):
        if(self.connected == False):
            self.db = Prisma(auto_register=True)
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.db.connect())
            print("Connected to database!")
            self.connected = True
        return self.db
    
    def view_cooldown(self, *args, **kwargs):
        return False
    
    def get_claimable_roles(self):
        role_ids = {"Master Detective": "830134790278610994", "Exploiter Hunter": "1093278561164611737", "Active": "884490621799247883", "Known": "884490169380638741", "Respected": "883479748083322890", "Legend": "962336428623265802", "Level 69": "969668114784583681"}
        return role_ids
    
    async def get_personal_quota(self, start, end, discord_id):
        quota = await db.botstorage.find_first(where={"id": 1})
        print(discord_id)
        staff_id = (await db.staff.find_first(where={"discord_id": str(discord_id)})).id
        exceptions = await db.quota_exception.find_many(where={"staffId": staff_id, "start_date": {"lte": end}, "end_date": {"gte": start}, "approved": True})
        # Days is the amount of days in this month
        if(exceptions):
            exempt_days = 0
            for quota_exception in exceptions:
                days = calendar.monthrange(end.year, end.month)[1]
                start_date = quota_exception.start_date if quota_exception.start_date.month == start.month else quota_exception.start_date.replace(day=1, month=start.month, year=start.year)
                end_date = quota_exception.end_date if quota_exception.end_date.month == end.month else quota_exception.end_date.replace(day=days, month=end.month, year=end.year)
                print(start_date, end_date)
                exempt_days += (end_date - start_date).days + 1 # Add 1 since the end date is inclusive
                print(exempt_days)
            return quota.ticket_quota-(quota.ticket_quota/days*exempt_days)
        else:
            return quota.ticket_quota

    async def ticket_interaction_check(self, ticket, interaction: nextcord.Interaction):
        if self.get_permission_level(2).predicate(interaction):
            return True
        if ticket == None:
            return "This ticket does not exist. (This is a bug, please report it to the developer)"
        if (ticket.claimed_by != None and ticket.claimed_by != str(interaction.user.id)):
            return "You can't interact with this ticket as it is claimed by someone else."
        if ticket.claimed_by != None and ticket.claimed_by == str(interaction.user.id):
            return True
        percentage = await db.botstorage.find_first(where={"id": 1})
        if percentage.quota_complete_percentage >= 80:
            return True
        ticket_amount = await db.reportticket.count()
        if(ticket_amount >= 50):
            return True
        quota = await db.botstorage.find_first(where={"id": 1})
        staff = await db.staff.find_first(where={"discord_id": str(interaction.user.id)})
        # Find the newest ticket that is not done by the staff member
        last_ticket_time = await db.ticket.find_first(where={'NOT': [{"staffId": staff.id}]}, order={"date": "desc"})
        if(last_ticket_time != None and last_ticket_time.date < datetime.datetime.now(last_ticket_time.date.tzinfo) - datetime.timedelta(minutes=30) and ticket_amount > 5):
            return True
        if(last_ticket_time != None and last_ticket_time.date < datetime.datetime.now(last_ticket_time.date.tzinfo) - datetime.timedelta(minutes=10) and ticket_amount > 75):
            return True
        staff_tickets = await db.ticket.count(where={"staffId": staff.id, "date": {"gt": datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, day=1)}})
        tickets_today = await db.ticket.count(where={"staffId": staff.id, "date": {"gt": datetime.datetime.now() - datetime.timedelta(days=1)}})
        if(staff_tickets >= quota.ticket_quota):
            return "You can't interact with this ticket as you have already completed your quota."
        if(tickets_today > round(quota.ticket_quota/4)):
            return f"You can't interact with this ticket as you have already completed {round(quota.ticket_quota/4)} tickets in the last 24 hours."
        return True
    
    def get_permission_level(self, max_level: int):
        def predicate(Interaction, custom=False):
            if custom:
                user = Interaction
            else:
                user = Interaction.user
            try:
                if user.roles is None:
                    return False
            except:
                return False
            # Check if command is run in DMs
            if Interaction.guild is None:
                return False
            if(user.id == 305246941992976386):
                return 0 <= max_level
            elif(nextcord.utils.get(user.roles, id=828960184633786399)): # Overseer
                return 1 <= max_level
            elif(nextcord.utils.get(user.roles, id=1100771014234873997)): # Underseer
                return 1 <= max_level
            elif(nextcord.utils.get(user.roles, id=860552432945463346)): # Server manager
                return 2 <= max_level
            elif(nextcord.utils.get(user.roles, id=820094497332396053)): # Staff manager
                return 3 <= max_level
            elif(nextcord.utils.get(user.roles, id=956821842356764753)): # Head Moderator
                return 4 <= max_level
            elif(nextcord.utils.get(user.roles, id=956820877796859917)): # Senior Moderator
                return 5 <= max_level
            elif(nextcord.utils.get(user.roles, id=820290678973792287)): # Moderator
                return 6 <= max_level
            elif(nextcord.utils.get(user.roles, id=956807555122876427)): # Junior Moderator
                return 7 <= max_level
            elif(nextcord.utils.get(user.roles, id=820295435448483851)): # Trial Moderator
                return 8 <= max_level
            elif(nextcord.utils.get(user.roles, id=820249824757678080)): # Staff Team role
                return 8 <= max_level
            else:
                return 9 <= max_level
        return nextcord.ext.application_checks.check(predicate)
    
    async def update_status(self, bot):
        statuses = []
        with open('statuses.txt', 'r') as f:
            for line in f:
                statuses.append(line.strip())
        status = random.choice(statuses)
        if "{staff}" in status:
            # Get all staff members
            staff = self.get_staff(bot, include_trial=True)
            # Get a random staff member
            staff_member = random.choice(staff)
            # Get their name
            staff_name = staff_member.display_name
            status = status.replace("{staff}", staff_name)
        await bot.change_presence(activity=nextcord.Game(name=status), status="dnd")

    async def server_log(self, message, bot):
        guild = bot.get_guild(self.guild_id)
        channel = guild.get_channel(820290198008365057)
        await channel.send(message)

    async def demote(self, user, rankstrip=False, recursive=False):
        if(nextcord.utils.get(user.roles, id=956821842356764753)): # Head Moderator
            await user.remove_roles(nextcord.utils.get(user.guild.roles, id=956821842356764753)) # Head Moderator
            if(not recursive):
                await user.add_roles(nextcord.utils.get(user.guild.roles, id=956820877796859917)) # Senior Moderator
                return "Senior Moderator"
        elif(nextcord.utils.get(user.roles, id=956820877796859917)): # Senior Moderator
            await user.remove_roles(nextcord.utils.get(user.guild.roles, id=956820877796859917)) # Senior Moderator
            if(not recursive):
                await user.add_roles(nextcord.utils.get(user.guild.roles, id=820290678973792287)) # Moderator
                return "Moderator"
        elif(nextcord.utils.get(user.roles, id=820290678973792287)): # Moderator
            await user.remove_roles(nextcord.utils.get(user.guild.roles, id=820290678973792287)) # Moderator
            if(not recursive):
                await user.add_roles(nextcord.utils.get(user.guild.roles, id=956807555122876427)) # Junior Moderator
                return "Junior Moderator"
        elif(nextcord.utils.get(user.roles, id=956807555122876427) and not recursive): # Junior Moderator
            await user.remove_roles(nextcord.utils.get(user.guild.roles, id=956807555122876427)) # Junior Moderator
            await user.remove_roles(nextcord.utils.get(user.guild.roles, id=820249824757678080)) # Staff team role
            await user.add_roles(nextcord.utils.get(user.guild.roles, id=903946067031248917)) # Former staff role
            return "Former staff"
        if(rankstrip):
            await user.remove_roles(nextcord.utils.get(user.guild.roles, id=820249824757678080)) # Staff team role
            await user.add_roles(nextcord.utils.get(user.guild.roles, id=903946067031248917)) # Former staff role
            await self.demote(user, rankstrip=False, recursive=True)
            return "Former staff"
        
    def get_staff(self, bot, include_trial=False):
        staff_role_ids = [956821842356764753, 956820877796859917, 820290678973792287, 956807555122876427]
        if(include_trial):
            staff_role_ids.append(820295435448483851)
        blacklist_role_ids = [860552432945463346, 954315024019623966, 828960184633786399, 820094497332396053, 967803801308393472, 1087522003264733294, 1087522481239232532, 1112068576740905112]
        staff = []
        for staff_role_id in staff_role_ids:
            staff_role = nextcord.utils.get(bot.get_guild(820093197933740062).roles, id=staff_role_id)
            # If staff has a role in the blacklist, don't add them to the list
            for member in staff_role.members:
                if(not any(role.id in blacklist_role_ids for role in member.roles) and member not in staff):
                    staff.append(member)
        return staff

    async def confirm(self, interaction: nextcord.Interaction, message):
        # Create the confirmation message and add discord panel buttons
        view = ConfirmationButtons()
        await interaction.followup.send(message, view=view, ephemeral=True)
        await view.wait()
        if view.value:
            return True
        else:
            return False
    
    async def log_error(self, bot, message):
        await bot.get_user(305246941992976386).send(message[:2000])

    def error_embed(self, message):
        embed = nextcord.Embed(title="Error", description=message, color=nextcord.Color.red())
        return embed

    async def add_ticket(self, interaction, reporter, reported, evidence, reason, punishment, message_id, additional_info=None, completedIn=None):
        # Add ticket usign prisma
        message_id = str(message_id)
        reporter = str(reporter)
        if completedIn != None:
            completedIn = int(completedIn)
        # Check if there is a current multiplier
        multiplier = await db.ticketpurges.find_first(where={"start": {"gte": datetime.datetime.now()}, "end": {"lte": datetime.datetime.now()}})
        if multiplier != None:
            multiplier = multiplier.multiplier
        else:
            multiplier = 1.0
        if(await db.staff.find_first(where={"discord_id": str(interaction.user.id)}) == None):
            await db.staff.create(data={
                    "discord_id": str(interaction.user.id),
                    "tickets": {
                        "create": [
                            {
                                "reporter": reporter,
                                "reported": reported,
                                "evidence": evidence,
                                "reason": reason,
                                "punishment": punishment,
                                "messageId": message_id,
                                "additionalInfo": additional_info,
                                "completedIn": completedIn
                            }
                        ]
                    }
                }
            )
        else:
            # Update the staff object in the database
            await db.staff.update(where={"discord_id": str(interaction.user.id)}, data={
                "tickets": {
                    "create": [
                        {
                            "reporter": reporter,
                            "reported": reported,
                            "evidence": evidence,
                            "reason": reason,
                            "punishment": punishment,
                            "messageId": message_id,
                            "additionalInfo": additional_info,
                            "completedIn": completedIn
                        }
                    ]
                }
            })

class ConfirmationButtons(nextcord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = False
    
    @nextcord.ui.button(label="Yes", style=nextcord.ButtonStyle.green)
    async def confirm(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.value = True
        self.stop()
    
    @nextcord.ui.button(label="No", style=nextcord.ButtonStyle.red)
    async def cancel(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.value = False
        self.stop()




db = Utils().get_db()
