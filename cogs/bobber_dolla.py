"""
/give_dolla (which staff member) (how many (autos to 1 if not filled in)) (reason)
Allows for bobber dolla's to be given to a staff member
Only accessable by Boba/overseers

/remove_dolla (which staff member) (how many (autos to 1 if not filled in)) (reason)
Allows for bobber dolla's to be revoked from a staff member
Only accessable by Boba/overseers

/check_dolla (staff member (autos to yourself if not filled in))
Allows for staff members to check bobber dollas
Accessable by all staff members

/claim_reward (reward type)
Allows for staff members to request a reward
Accessable by all staff members

/bobber_report (staff member) (reason)
Allows for a staff member to be anonymously reported if one feels like they are breaking the rules, fabricating their behavior, then a staff manager+ can look into it to see if it is valid
Accessable by all staff members
if someone gets lots of boba coins, the amount they get on average becomes slightly less
so people who have little compassion starting to become generous and overall a good staff would be rewarded greatly over time, same with every other staff regardless of nice or bad
with that, as time passes, people who have obtained many coins will slowly start to receive less, while people improving more will get a little more
in the end, everyone should be very generous and kind to eachother, while we each get the same amount of boba coins relative to how we act all the time
"""

import nextcord
from nextcord.ext import commands

class bobber_dolla(commands.Cog):
  pass

def setup(bot):
  bot.add_cog(bobber_dolla(bot))
