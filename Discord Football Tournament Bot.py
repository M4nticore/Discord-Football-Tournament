import discord
from discord.ext import commands

class Team:
    def __init__(self, name):
        self.name = name
        self.goals_scored = 0
        self.goals_conceded = 0
        self.goal_difference = 0
        self.points = 0

    def update_stats(self, scored, conceded):
        self.goals_scored += scored
        self.goals_conceded += conceded
        self.goal_difference = self.goals_scored - self.goals_conceded
        if scored > conceded:
            self.points += 3
        elif scored == conceded:
            self.points += 1

    def reverse_stats(self, scored, conceded):
        self.goals_scored -= scored
        self.goals_conceded -= conceded
        self.goal_difference = self.goals_scored - self.goals_conceded
        if scored > conceded:
            self.points -= 3
        elif scored == conceded:
            self.points -= 1

    def __str__(self):
        return f"{self.name}: Points: {self.points}, Scored: {self.goals_scored}, Conceded: {self.goals_conceded}, Difference: {self.goal_difference}"

def get_team_by_name(teams, name):
    for team in teams:
        if team.name == name:
            return team
    return None

def sort_groups(groups):
    for group in groups:
        group['teams'].sort(key=lambda x: (x.points, x.goal_difference), reverse=True)

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

groups = [{'name': chr(ord('A') + i), 'teams': []} for i in range(4)]
match_history = []

# Variable to hold the scoreboard channel ID
scoreboard_channel_id = None

@bot.command(name='setscoreboard')
async def set_scoreboard_channel(ctx, channel_id: int):
    global scoreboard_channel_id
    scoreboard_channel_id = channel_id
    await ctx.send(f"Scoreboard channel set to <#{channel_id}>")

async def update_scoreboard():
    if scoreboard_channel_id is None:
        return

    channel = bot.get_channel(scoreboard_channel_id)
    if channel is None:
        return

    standings_message = ""
    for group in groups:
        standings_message += f"\nGroup {group['name']} Standings:\n"
        for team in group['teams']:
            standings_message += f"{team}\n"

    # Clear previous messages and send new standings
    async for message in channel.history(limit=100):
        await message.delete()

    await channel.send(standings_message)

@bot.command(name='takımekle')
async def add_team(ctx, group_name: str, team_name: str):
    group = next((g for g in groups if g['name'].lower() == group_name.lower()), None)
    if group:
        if len(group['teams']) >= 6:
            await ctx.send(f"Group {group_name} already has 6 teams.")
            return
        if get_team_by_name(group['teams'], team_name):
            await ctx.send(f"Team {team_name} already exists in Group {group_name}.")
            return
        group['teams'].append(Team(team_name))
        await ctx.send(f"Team {team_name} added to Group {group_name}.")
    else:
        await ctx.send(f"Group {group_name} does not exist.")
    await update_scoreboard()

@bot.command(name='maç')
async def match(ctx, team_a: str, team_b: str, goals_a: int, goals_b: int):
    team_a_obj = None
    team_b_obj = None
    for group in groups:
        team_a_obj = get_team_by_name(group['teams'], team_a)
        team_b_obj = get_team_by_name(group['teams'], team_b)
        if team_a_obj and team_b_obj:
            break

    if team_a_obj and team_b_obj:
        team_a_obj.update_stats(goals_a, goals_b)
        team_b_obj.update_stats(goals_b, goals_a)
        match_history.append((team_a, team_b, goals_a, goals_b))
        sort_groups(groups)
        await ctx.send(f"Match recorded: {team_a} {goals_a} - {goals_b} {team_b}")
        await update_scoreboard()
    else:
        await ctx.send("Invalid team names entered. Please try again.")

@bot.command(name='işlemsil')
async def undo_last_match(ctx):
    if not match_history:
        await ctx.send("No match to undo.")
        return

    last_match = match_history.pop()
    team_a, team_b, goals_a, goals_b = last_match

    team_a_obj = None
    team_b_obj = None
    for group in groups:
        team_a_obj = get_team_by_name(group['teams'], team_a)
        team_b_obj = get_team_by_name(group['teams'], team_b)
        if team_a_obj and team_b_obj:
            break

    if team_a_obj and team_b_obj:
        team_a_obj.reverse_stats(goals_a, goals_b)
        team_b_obj.reverse_stats(goals_b, goals_a)
        sort_groups(groups)
        await ctx.send(f"Last match undone: {team_a} {goals_a} - {goals_b} {team_b}")
        await update_scoreboard()
    else:
        await ctx.send("Error undoing match. Teams not found.")

@bot.command(name='standings')
async def standings(ctx):
    standings_message = ""
    for group in groups:
        standings_message += f"\nGroup {group['name']} Standings:\n"
        for team in group['teams']:
            standings_message += f"{team}\n"
    await ctx.send(standings_message)

@bot.command(name='quarterfinal')
async def create_quarterfinal(ctx):
    # Check if there are enough teams to create quarterfinals
    if len(groups) < 4:
        await ctx.send("There are not enough groups to create quarterfinals.")
        return

    # Sort each group by points to get the winners and runners-up
    for group in groups:
        sort_groups([group])

    # Get the winners and runners-up of each group
    winners = [group['teams'][0] for group in groups]
    runners_up = [group['teams'][1] for group in groups]

    # Create quarterfinal groups
    quarterfinal_groups = [
        {'name': 'Quarter 1', 'teams': [winners[0], runners_up[1]]},
        {'name': 'Quarter 2', 'teams': [winners[1], runners_up[0]]},
        {'name': 'Quarter 3', 'teams': [winners[2], runners_up[3]]},
        {'name': 'Quarter 4', 'teams': [winners[3], runners_up[2]]}
    ]

    # Replace the existing groups with the new quarterfinal groups
    groups.clear()
    groups.extend(quarterfinal_groups)

    # Reset team scores
    for group in groups:
        for team in group['teams']:
            team.goals_scored = 0
            team.goals_conceded = 0
            team.goal_difference = 0
            team.points = 0

    # Update the scoreboard with the new standings
    await update_scoreboard()
    await ctx.send("Quarterfinals created. Standings updated. Team scores reset.")


@bot.command(name='semifinal')
async def create_semifinal(ctx):
    # Check if there are enough quarterfinal groups to create semifinals
    if len(groups) < 2:
        await ctx.send("There are not enough quarterfinal groups to create semifinals.")
        return

    # Sort each quarterfinal group by points to get the winners
    for group in groups:
        sort_groups([group])

    # Get the winners of each quarterfinal group
    winners = [group['teams'][0] for group in groups]

    # Create semifinal groups
    semifinal_groups = [
        {'name': 'Semi Final 1', 'teams': [winners[0], winners[3]]},
        {'name': 'Semi Final 2', 'teams': [winners[1], winners[2]]}
    ]

    # Replace the existing groups with the new semifinal groups
    groups.clear()
    groups.extend(semifinal_groups)

    # Reset team scores
    for group in groups:
        for team in group['teams']:
            team.goals_scored = 0
            team.goals_conceded = 0
            team.goal_difference = 0
            team.points = 0

    # Update the scoreboard with the new standings
    await update_scoreboard()
    await ctx.send("Semifinals created. Standings updated. Team scores reset.")

@bot.command(name='backup')
async def send_backup(ctx):
    # Create the current standings message
    standings_message = ""
    for group in groups:
        standings_message += f"\nGroup {group['name']} Standings:\n"
        for team in group['teams']:
            standings_message += f"{team}\n"

    # Send messages to users
    user1_id = #userid

    try:
        user1 = await bot.fetch_user(user1_id)
        await user1.send(standings_message)
    except discord.errors.NotFound:
        print("User 1 not found.")

    try:
        user2 = await bot.fetch_user(user2_id)
        await user2.send(standings_message)
    except discord.errors.NotFound:
        print("User 2 not found.")

    await ctx.send("Current standings sent to users.")


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')

bot.run('Your Discord Token')