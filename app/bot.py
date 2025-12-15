import discord
from discord.ext import commands, tasks
import aiohttp
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import asyncio
import random
from bs4 import BeautifulSoup
import re
import urllib.parse

# Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
MATCH_CHANNEL_ID = int(os.getenv('MATCH_CHANNEL_ID', '0'))
NEWS_CHANNEL_ID = int(os.getenv('NEWS_CHANNEL_ID', '0'))

# API Endpoints
ESPORTS_API = "https://esports-api.lolesports.com/persisted/gw"

# Intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Cache pour éviter les doublons
notified_matches = set()
posted_articles = set()

# Mapping des leagues
LEAGUES = {
    'lec': 'LEC',
    'lck': 'LCK', 
    'lpl': 'LPL',
    'lta': 'LTA',
    'lcp': 'LCP'
}

async def fetch_schedule():
    """Récupère le calendrier des matchs depuis l'API LoL Esports"""
    url = f"{ESPORTS_API}/getSchedule"
    params = {'hl': 'en-US'}
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'x-api-key': '0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z'
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    print(f"API Error: {resp.status}")
                    return None
    except Exception as e:
        print(f"Error fetching schedule: {e}")
        return None

def filter_matches_by_leagues(data, target_leagues=None):
    """Filtre les matchs par leagues (LEC, LCK, LPL, LTA, LCP)"""
    if target_leagues is None:
        target_leagues = ['LEC', 'LCK', 'LPL', 'LTA', 'LCP']
    
    filtered = []
    
    if not data or 'data' not in data:
        return filtered
    
    schedule = data.get('data', {}).get('schedule', {})
    events = schedule.get('events', [])
    
    for event in events:
        league_name = event.get('league', {}).get('name', '').upper()
        
        if any(target in league_name for target in target_leagues):
            filtered.append(event)
    
    return filtered

def format_match_embed(match):
    """Formate un match en embed Discord"""
    state = match.get('state', 'unstarted')
    match_type = match.get('type', 'match')
    
    team1 = match.get('match', {}).get('teams', [{}])[0]
    team2 = match.get('match', {}).get('teams', [{}])[1] if len(match.get('match', {}).get('teams', [])) > 1 else {}
    
    team1_name = team1.get('name', 'TBD')
    team2_name = team2.get('name', 'TBD')
    
    team1_code = team1.get('code', team1_name[:3].upper())
    team2_code = team2.get('code', team2_name[:3].upper())
    
    team1_result = team1.get('result', {})
    team2_result = team2.get('result', {})
    
    team1_score = team1_result.get('gameWins', 0)
    team2_score = team2_result.get('gameWins', 0)
    
    league_name = match.get('league', {}).get('name', 'Unknown League')
    tournament_name = match.get('blockName', '')
    
    start_time = match.get('startTime')
    if start_time:
        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        time_str = f"<t:{int(dt.timestamp())}:F>"
    else:
        time_str = "TBD"
    
    if state == 'completed':
        color = 0x00FF00
        status = f"✅ **Final** - {team1_code} {team1_score} - {team2_score} {team2_code}"
    elif state == 'inProgress':
        color = 0xFF0000
        status = f"🔴 **LIVE** - {team1_code} {team1_score} - {team2_score} {team2_code}"
    else:
        color = 0x808080
        status = f"🕐 **Upcoming** - {team1_code} vs {team2_code}"
    
    embed = discord.Embed(
        title=f"{league_name}",
        description=status,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    
    if tournament_name:
        embed.add_field(name="Tournament", value=tournament_name, inline=False)
    
    embed.add_field(name="Match Time", value=time_str, inline=False)
    
    return embed

@bot.event
async def on_ready():
    print(f'✅ Bot connecté en tant que {bot.user}')
    print(f'📺 Match Channel: {MATCH_CHANNEL_ID}')
    print(f'📰 News Channel: {NEWS_CHANNEL_ID}')
    print(f'🚀 CI/CD Pipeline Active - v2!')
    
    if not check_matches.is_running():
        check_matches.start()
    
    if not check_sheep_news.is_running():
        check_sheep_news.start()

@bot.command(name='matches')
async def show_matches(ctx):
    """Affiche les 4 derniers matchs terminés et les 4 prochains matchs"""
    await ctx.send("🔍 Récupération des matchs...")
    
    data = await fetch_schedule()
    if not data:
        await ctx.send("❌ Impossible de récupérer les données")
        return
    
    matches = filter_matches_by_leagues(data)
    
    now = datetime.now(timezone.utc)
    completed = []
    upcoming = []
    
    for match in matches:
        start_time = match.get('startTime')
        if not start_time:
            continue
        
        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        state = match.get('state', 'unstarted')
        
        if state == 'completed':
            completed.append(match)
        elif state in ['unstarted', 'inProgress']:
            upcoming.append(match)
    
    completed = sorted(completed, key=lambda x: x.get('startTime', ''), reverse=True)[:4]
    upcoming = sorted(upcoming, key=lambda x: x.get('startTime', ''))[:4]
    
    if completed:
        await ctx.send("**📊 Derniers résultats:**")
        for match in completed:
            embed = format_match_embed(match)
            await ctx.send(embed=embed)
    
    if upcoming:
        await ctx.send("**📅 Prochains matchs:**")
        for match in upcoming:
            embed = format_match_embed(match)
            await ctx.send(embed=embed)
    
    if not completed and not upcoming:
        await ctx.send("Aucun match trouvé")

@bot.command(name='team')
async def team_matches(ctx, *, team_name: str):
    """Affiche les matchs d'une équipe spécifique"""
    await ctx.send(f"🔍 Recherche des matchs de **{team_name}**...")
    
    data = await fetch_schedule()
    if not data:
        await ctx.send("❌ Impossible de récupérer les données")
        return
    
    matches = filter_matches_by_leagues(data)
    team_matches = []
    
    team_name_lower = team_name.lower()
    
    for match in matches:
        teams = match.get('match', {}).get('teams', [])
        for team in teams:
            name = team.get('name', '').lower()
            code = team.get('code', '').lower()
            
            if team_name_lower in name or team_name_lower == code:
                team_matches.append(match)
                break
    
    if not team_matches:
        await ctx.send(f"❌ Aucun match trouvé pour **{team_name}**")
        return
    
    team_matches = sorted(team_matches, key=lambda x: x.get('startTime', ''))
    
    await ctx.send(f"**Matchs de {team_name}:**")
    for match in team_matches[:10]:
        embed = format_match_embed(match)
        await ctx.send(embed=embed)

@bot.command(name='today')
async def today_matches(ctx):
    """Affiche les matchs d'aujourd'hui"""
    await ctx.send("🔍 Matchs d'aujourd'hui...")
    
    data = await fetch_schedule()
    if not data:
        await ctx.send("❌ Impossible de récupérer les données")
        return
    
    matches = filter_matches_by_leagues(data)
    
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    today_matches = []
    
    for match in matches:
        start_time = match.get('startTime')
        if not start_time:
            continue
        
        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        
        if today_start <= dt < today_end:
            today_matches.append(match)
    
    if not today_matches:
        await ctx.send("Aucun match prévu aujourd'hui")
        return
    
    today_matches = sorted(today_matches, key=lambda x: x.get('startTime', ''))
    
    await ctx.send(f"**📅 Matchs d'aujourd'hui ({len(today_matches)}):**")
    for match in today_matches:
        embed = format_match_embed(match)
        await ctx.send(embed=embed)

@bot.command(name='league')
async def league_matches(ctx, league: str):
    """Affiche les matchs d'une league spécifique (LEC, LCK, LPL, LTA, LCP)"""
    league_upper = league.upper()
    
    if league_upper not in ['LEC', 'LCK', 'LPL', 'LTA', 'LCP']:
        await ctx.send("❌ League invalide. Utilisez: LEC, LCK, LPL, LTA ou LCP")
        return
    
    await ctx.send(f"🔍 Matchs de la {league_upper}...")
    
    data = await fetch_schedule()
    if not data:
        await ctx.send("❌ Impossible de récupérer les données")
        return
    
    matches = filter_matches_by_leagues(data, [league_upper])
    
    if not matches:
        await ctx.send(f"Aucun match trouvé pour la {league_upper}")
        return
    
    matches = sorted(matches, key=lambda x: x.get('startTime', ''))
    
    await ctx.send(f"**{league_upper} Matchs ({len(matches)}):**")
    for match in matches[:10]:
        embed = format_match_embed(match)
        await ctx.send(embed=embed)

@tasks.loop(hours=1)
async def check_matches():
    """Vérifie les matchs toutes les heures et notifie"""
    try:
        channel = bot.get_channel(MATCH_CHANNEL_ID)
        if not channel:
            return
        
        data = await fetch_schedule()
        if not data:
            return
        
        matches = filter_matches_by_leagues(data)
        now = datetime.now(timezone.utc)
        
        for match in matches:
            start_time = match.get('startTime')
            if not start_time:
                continue
            
            dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            time_until = (dt - now).total_seconds() / 3600
            
            match_id = match.get('match', {}).get('id', '')
            
            if 0 <= time_until <= 1 and match_id not in notified_matches:
                embed = format_match_embed(match)
                await channel.send("🔔 **Match bientôt !**", embed=embed)
                notified_matches.add(match_id)
                
                if len(notified_matches) > 100:
                    notified_matches.clear()
        
    except Exception as e:
        print(f"Error in check_matches: {e}")

@check_matches.before_loop
async def before_check_matches():
    await bot.wait_until_ready()

@tasks.loop(minutes=20)
async def check_sheep_news():
    """Scrape les news Sheep Esports directement depuis leur site"""
    try:
        channel = bot.get_channel(NEWS_CHANNEL_ID)
        if not channel:
            return
        
        url = 'https://www.sheepesports.com/fr/browse/LEAGUE'
        
        # Ajouter un délai aléatoire de 0-3 minutes
        random_delay = random.randint(0, 180)
        await asyncio.sleep(random_delay)
        
        print(f"🔍 Checking Sheep Esports news...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }) as resp:
                if resp.status != 200:
                    print(f"❌ HTTP Error {resp.status}")
                    return
                
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                articles = soup.find_all('article')[:5]
                
                if not articles:
                    print("⚠️ No articles found")
                    return
                
                for article in articles:
                    try:
                        all_texts = [t.strip() for t in article.find_all(string=True) if t.strip() and len(t.strip()) > 10]
                        
                        if len(all_texts) < 2:
                            continue
                        
                        date_str = all_texts[0] if all_texts else "Unknown date"
                        title = all_texts[1] if len(all_texts) > 1 else "No title"
                        description = all_texts[2] if len(all_texts) > 2 else ""
                        
                        article_id = re.sub(r'\W+', '_', title.lower())[:50]
                        
                        if article_id in posted_articles:
                            continue
                        
                        link_tag = article.find('a')
                        article_link = "https://www.sheepesports.com"
                        if link_tag and link_tag.get('href'):
                            href = link_tag.get('href')
                            if href.startswith('http'):
                                article_link = href
                            else:
                                article_link = f"https://www.sheepesports.com{href}"
                        
                        img_tag = article.find('img')
                        img_url = None
                        if img_tag:
                            img_src = img_tag.get('src') or img_tag.get('data-src')
                            if img_src:
                                if 'cdn.sanity.io' in img_src:
                                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(img_src).query)
                                    if 'url' in parsed:
                                        img_url = parsed['url'][0]
                                elif img_src.startswith('http'):
                                    img_url = img_src
                        
                        embed = discord.Embed(
                            title=title[:256],
                            description=description[:300] + "..." if len(description) > 300 else description,
                            url=article_link,
                            color=0xFF6B35,
                            timestamp=datetime.now(timezone.utc)
                        )
                        
                        if img_url:
                            embed.set_image(url=img_url)
                        
                        embed.set_footer(
                            text=f"Sheep Esports • {date_str}",
                            icon_url="https://www.sheepesports.com/favicon.ico"
                        )
                        
                        await channel.send(embed=embed)
                        posted_articles.add(article_id)
                        
                        await asyncio.sleep(2)
                        
                        print(f"✅ Posted article: {title[:50]}...")
                        
                    except Exception as e:
                        print(f"⚠️ Error processing article: {e}")
                        continue
        
    except Exception as e:
        print(f"❌ Error checking Sheep news: {e}")

@check_sheep_news.before_loop
async def before_check_news():
    await bot.wait_until_ready()
    initial_delay = random.randint(0, 300)
    print(f"⏳ Starting Sheep news checker in {initial_delay}s...")
    await asyncio.sleep(initial_delay)

if __name__ == '__main__':
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN non défini")
        exit(1)
    
    bot.run(DISCORD_TOKEN)
