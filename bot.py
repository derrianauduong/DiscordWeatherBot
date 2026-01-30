import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import pytz
from datetime import datetime
from event_logic import get_weather_recommendations, get_todays_events, get_going_out_events
from weather import get_weather
from google_auth import get_calendar_service
import os

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True  # Required so your bot can read messages

bot = commands.Bot(command_prefix="!", intents=intents)

service = get_calendar_service()

last_run_date = None

@tasks.loop(minutes=1)
async def daily_check():
    global last_run_date
    tz = pytz.timezone("Australia/Sydney")
    now = datetime.now(tz)

    # Print this so you can see it in Railway logs
    if now.minute == 0: 
        print(f"Heartbeat: It is currently {now.strftime('%H:%M')}. Last run: {last_run_date}")

    if now.hour == 7 and last_run_date != now.date():
        print("Attempting to send daily weather update...")
        last_run_date = now.date()

        channel = bot.get_channel(int(os.getenv("DISCORD_CHANNEL_ID")))
        user_id = int(os.getenv("DISCORD_USER_ID"))

        events = get_going_out_events(service)
        if not events:
            return

        recs = get_weather_recommendations(events)

        message = f"<@{user_id}> **Today's Going-Out Weather Summary:**\n\n"
        for r in recs:
            event = r["event"]
            weather = r["weather"]
            umbrella = r["umbrella"]

            start = event["start"].get("dateTime", event["start"].get("date"))
            summary = event["summary"]

            message += f"- **{summary}** at `{start}`\n"
            message += f"Weather: {weather['description']}\n"
            message += "→ Bring an umbrella.\n\n" if umbrella else "→ No umbrella needed.\n\n"

        await channel.send(message)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

    if not daily_check.is_running():
        daily_check.start()

@bot.command()
async def ping(ctx):
    channel = bot.get_channel(int(os.getenv("DISCORD_CHANNEL_ID")))
    user_id = int(os.getenv("DISCORD_USER_ID"))
    await channel.send(f"<@{user_id}>")

@bot.command()
async def weather(ctx):
    lat = -33.8688
    lon = 151.2093
    now = datetime.now(pytz.timezone("Australia/Sydney"))

    report = get_weather(lat, lon, now)
    await ctx.send(report)

@bot.tree.command(name="events", description="Show today's calendar events")
async def events(interaction: discord.Interaction):
    await interaction.response.defer()

    events = get_todays_events(service)

    if not events:
        await interaction.followup.send("No events scheduled for today.")
        return

    message = "**Today's Events:**\n"
    for event in events:
        start_str = event["start"].get("dateTime")

        if start_str:
            dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            sydney = pytz.timezone("Australia/Sydney")
            local_dt = dt.astimezone(sydney)

            # Choose your preferred format:
            time_24h = local_dt.strftime("%H:%M")
            time_ampm = local_dt.strftime("%I:%M %p")

            message += f"- **{event['summary']}** at `{time_24h}` **({time_ampm})**\n"
        else:
            message += f"- **{event['summary']}** (All day)\n"

    await interaction.followup.send(message)

@bot.tree.command(name="goingout", description="Show today's going-out events")
async def going_out(interaction: discord.Interaction):
    await interaction.response.defer()

    events = get_going_out_events(service)

    if not events:
        await interaction.followup.send("No going-out events today.")
        return

    message = "**Today's Going-Out Events:**\n"
    for event in events:
        start_str = event["start"].get("dateTime")

        if start_str:
            dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            sydney = pytz.timezone("Australia/Sydney")
            local_dt = dt.astimezone(sydney)

            # Choose your preferred format:
            time_24h = local_dt.strftime("%H:%M")
            time_ampm = local_dt.strftime("%I:%M %p")

            message += f"- **{event['summary']}** at `{time_24h}` **({time_ampm})**\n"
        else:
            message += f"- **{event['summary']}** (All day)\n"


    await interaction.followup.send(message)

bot.run(os.getenv("DISCORD_TOKEN"))








