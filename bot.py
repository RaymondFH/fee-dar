import discord
import requests
import time
from config import DISCORD_TOKEN, RIOT_API_KEY, MONITORED_GAME

client = discord.Client()

# Dictionary to store Discord to Riot account mappings
user_riot_mapping = {}

# Function to fetch summoner ID
def get_summoner_id(summoner_name):
    summoner_url = f"https://na1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summoner_name}"
    headers = {
        'X-Riot-Token': RIOT_API_KEY
    }
    response = requests.get(summoner_url, headers=headers)
    if response.status_code == 200:
        return response.json()['id']
    return None

# Function to fetch live game stats for League of Legends
def get_live_game_stats(summoner_id):
    live_game_url = f"https://na1.api.riotgames.com/lol/spectator/v4/active-games/by-summoner/{summoner_id}"
    headers = {
        'X-Riot-Token': RIOT_API_KEY
    }
    response = requests.get(live_game_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

# Function to fetch PUUID for Valorant player
def get_valorant_puuid(username, tagline):
    url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{username}/{tagline}"
    headers = {
        'X-Riot-Token': RIOT_API_KEY
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['puuid']
    return None

# Function to fetch live game stats for Valorant
def get_valorant_live_game_stats(puuid):
    url = f"https://na.api.riotgames.com/val/match/v1/matches/by-puuid/{puuid}/recent"
    headers = {
        'X-Riot-Token': RIOT_API_KEY
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Command to register Riot account
    # !register <RiotAccount> <Tagline>
    if message.content.startswith('!register'):
        parts = message.content.split(' ')
        if len(parts) == 3:
            riot_account = parts[1]
            tagline = parts[2]
            user_riot_mapping[message.author.id] = (riot_account, tagline)
            await message.channel.send(f'Registered {riot_account}#{tagline} for {message.author.name}')
        else:
            await message.channel.send('Usage: !register <RiotAccount> <Tagline>')

async def monitor_game_stats():
    channel = discord.utils.get(client.get_all_channels(), name='general')
    
    while True:
        any_active_game = False

        for member in channel.guild.members:
            if member.bot or member.id not in user_riot_mapping:
                continue

            riot_account, tagline = user_riot_mapping[member.id]
            game_stats = None

            if MONITORED_GAME == 'League of Legends':
                summoner_id = get_summoner_id(riot_account)
                if summoner_id:
                    game_stats = get_live_game_stats(summoner_id)
            elif MONITORED_GAME == 'Valorant':
                puuid = get_valorant_puuid(riot_account, tagline)
                if puuid:
                    game_stats = get_valorant_live_game_stats(puuid)

            if game_stats:
                any_active_game = True
                if MONITORED_GAME == 'League of Legends':
                    for participant in game_stats['participants']:
                        if participant['summonerName'] == riot_account:
                            kills = participant['kills']
                            deaths = participant['deaths']
                            username = participant['summonerName']
                            if deaths == 3 and kills == 0:
                                await channel.send(f"@everyone {username} is feeding in {MONITORED_GAME}!")
                            elif deaths == 5 and kills == 0:
                                await channel.send(f"@everyone {username} is inting in {MONITORED_GAME}!")
                            elif kills == 4 and deaths == 0:
                                await channel.send(f"@everyone {username} is fed in {MONITORED_GAME}!")
                
                elif MONITORED_GAME == 'Valorant':
                    for match in game_stats['matches']:
                        for player in match['players']:
                            if player['puuid'] == puuid:
                                kills = player['stats']['kills']
                                deaths = player['stats']['deaths']
                                username = riot_account
                                if deaths == 3 and kills == 0:
                                    await channel.send(f"@everyone {username} is feeding in {MONITORED_GAME}!")
                                elif deaths == 5 and kills == 0:
                                    await channel.send(f"@everyone {username} is inting in {MONITORED_GAME}!")
                                elif kills == 4 and deaths == 0:
                                    await channel.send(f"@everyone {username} is fed in {MONITORED_GAME}!")

        if not any_active_game:
            await channel.send(f"No active {MONITORED_GAME} games detected. Monitoring paused.")
            break

        time.sleep(60)  # Check every 60 seconds

client.loop.create_task(monitor_game_stats())
client.run(DISCORD_TOKEN)
